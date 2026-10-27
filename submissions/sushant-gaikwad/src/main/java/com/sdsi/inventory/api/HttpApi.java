package com.sdsi.inventory.api;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.sdsi.inventory.model.Reservation;
import com.sdsi.inventory.service.ErrorCode;
import com.sdsi.inventory.service.InventoryException;
import com.sdsi.inventory.service.InventoryService;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Minimal JSON REST API on the JDK's built-in HTTP server (no framework needed).
 *
 * <pre>
 * GET    /health
 * GET    /inventory                      -> all SKUs: available / reserved / sold
 * GET    /inventory/{sku}
 * POST   /reservations                   {"sku","quantity","ttlSeconds"?}  -> 201
 * GET    /reservations/{id}
 * POST   /reservations/{id}/confirm
 * POST   /reservations/{id}/cancel       (DELETE /reservations/{id} is an alias)
 * </pre>
 *
 * The caller is identified by the {@code X-User-Id} header. In production this would come from a
 * verified auth token; it is a header here to keep the demo self-contained.
 */
public final class HttpApi implements AutoCloseable {

    static final int MAX_BODY_BYTES = 4 * 1024;
    private static final System.Logger LOG = System.getLogger(HttpApi.class.getName());
    private static final Set<String> RESERVE_FIELDS = Set.of("sku", "quantity", "ttlSeconds");

    private final InventoryService service;
    private final HttpServer server;
    private final ExecutorService executor;
    private final ObjectMapper json = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    public HttpApi(InventoryService service, String host, int port) throws IOException {
        this.service = service;
        this.server = HttpServer.create(new InetSocketAddress(host, port), 0);
        // Virtual threads: thousands of concurrent buyers without a big platform thread pool.
        this.executor = Executors.newVirtualThreadPerTaskExecutor();
        server.setExecutor(executor);
        server.createContext("/", this::handle);
    }

    public void start() {
        server.start();
    }

    public int port() {
        return server.getAddress().getPort();
    }

    @Override
    public void close() {
        server.stop(0);
        executor.shutdownNow();
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            try {
                route(ex);
            } catch (InventoryException e) {
                sendError(ex, e.code(), e.getMessage());
            } catch (RuntimeException e) {
                LOG.log(System.Logger.Level.ERROR, "unhandled error on " + ex.getRequestURI().getPath(), e);
                sendError(ex, ErrorCode.INTERNAL_ERROR, "internal error");
            }
        }
    }

    private void route(HttpExchange ex) throws IOException {
        String method = ex.getRequestMethod();
        String[] p = splitPath(ex.getRequestURI().getRawPath());

        if (p.length == 1 && p[0].equals("health")) {
            requireMethod(method, "GET");
            send(ex, 200, Map.of("status", "UP"));
        } else if (p.length == 1 && p[0].equals("inventory")) {
            requireMethod(method, "GET");
            send(ex, 200, service.report());
        } else if (p.length == 2 && p[0].equals("inventory")) {
            requireMethod(method, "GET");
            send(ex, 200, service.report(p[1]));
        } else if (p.length == 1 && p[0].equals("reservations")) {
            requireMethod(method, "POST");
            send(ex, 201, reserve(ex));
        } else if (p.length == 2 && p[0].equals("reservations")) {
            String user = userId(ex);
            switch (method) {
                case "GET" -> send(ex, 200, service.get(user, p[1]));
                case "DELETE" -> send(ex, 200, service.cancel(user, p[1]));
                default -> throw methodNotAllowed();
            }
        } else if (p.length == 3 && p[0].equals("reservations") && p[2].equals("confirm")) {
            requireMethod(method, "POST");
            send(ex, 200, service.confirm(userId(ex), p[1]));
        } else if (p.length == 3 && p[0].equals("reservations") && p[2].equals("cancel")) {
            requireMethod(method, "POST");
            send(ex, 200, service.cancel(userId(ex), p[1]));
        } else {
            sendError(ex, ErrorCode.NOT_FOUND, "no such endpoint");
        }
    }

    private Reservation reserve(HttpExchange ex) throws IOException {
        String user = userId(ex);
        JsonNode body = readJsonObject(ex);
        body.fieldNames().forEachRemaining(f -> {
            if (!RESERVE_FIELDS.contains(f)) {
                throw new InventoryException(ErrorCode.INVALID_INPUT, "unknown field: " + f);
            }
        });
        JsonNode sku = body.get("sku");
        if (sku == null || !sku.isTextual()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "sku must be a string");
        }
        int quantity = strictInt(body, "quantity", 1);
        JsonNode ttlNode = body.get("ttlSeconds");
        Duration ttl = ttlNode == null || ttlNode.isNull() ? null : Duration.ofSeconds(strictInt(body, "ttlSeconds", null));
        String idemKey = ex.getRequestHeaders().getFirst("Idempotency-Key");
        return service.reserve(user, sku.asText(), quantity, ttl, idemKey);
    }

    // ------------------------------------------------------------------ request helpers

    private static String[] splitPath(String raw) {
        String trimmed = raw.replaceAll("^/+|/+$", "");
        return trimmed.isEmpty() ? new String[0] : trimmed.split("/+");
    }

    private static String userId(HttpExchange ex) {
        String user = ex.getRequestHeaders().getFirst("X-User-Id");
        if (user == null || user.isBlank()) {
            throw new InventoryException(ErrorCode.UNAUTHORIZED, "X-User-Id header is required");
        }
        return user.strip();
    }

    private JsonNode readJsonObject(HttpExchange ex) throws IOException {
        byte[] bytes;
        try (InputStream in = ex.getRequestBody()) {
            bytes = in.readNBytes(MAX_BODY_BYTES + 1);
        }
        if (bytes.length > MAX_BODY_BYTES) {
            throw new InventoryException(ErrorCode.PAYLOAD_TOO_LARGE, "request body exceeds " + MAX_BODY_BYTES + " bytes");
        }
        JsonNode node;
        try {
            node = json.readTree(bytes);
        } catch (JsonProcessingException e) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "request body is not valid JSON");
        }
        if (node == null || !node.isObject()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "request body must be a JSON object");
        }
        return node;
    }

    /** Rejects "2", 2.5, true, etc. Only real JSON integers are accepted. */
    private static int strictInt(JsonNode body, String field, Integer fallback) {
        JsonNode v = body.get(field);
        if (v == null || v.isNull()) {
            if (fallback == null) {
                throw new InventoryException(ErrorCode.INVALID_INPUT, field + " is required");
            }
            return fallback;
        }
        if (!v.isIntegralNumber() || !v.canConvertToInt()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, field + " must be an integer");
        }
        return v.intValue();
    }

    private static void requireMethod(String actual, String expected) {
        if (!expected.equals(actual)) {
            throw methodNotAllowed();
        }
    }

    private static InventoryException methodNotAllowed() {
        return new InventoryException(ErrorCode.METHOD_NOT_ALLOWED, "method not allowed");
    }

    // ------------------------------------------------------------------ response helpers

    private void send(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = json.writeValueAsBytes(body);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        ex.getResponseHeaders().set("Cache-Control", "no-store");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }

    private void sendError(HttpExchange ex, ErrorCode code, String message) throws IOException {
        send(ex, code.httpStatus(), Map.of("error", Map.of("code", code.name(), "message", message)));
    }
}
