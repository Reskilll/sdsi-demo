package com.sdsi.inventory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.inventory.api.HttpApi;
import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.service.InventoryService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** End-to-end tests over real HTTP on a random local port. */
class HttpApiTest {

    private final ObjectMapper json = new ObjectMapper();
    private final HttpClient client = HttpClient.newHttpClient();
    private MutableClock clock;
    private InventoryService service;
    private HttpApi api;
    private String base;

    @BeforeEach
    void start() throws Exception {
        clock = new MutableClock(Instant.parse("2026-10-27T10:00:00Z"));
        service = new InventoryService(List.of(new Product("PHONE", "Phone", 5, 2)),
                clock, InventoryService.DEFAULT_TTL, InventoryService.DEFAULT_RETENTION);
        api = new HttpApi(service, "127.0.0.1", 0);
        api.start();
        base = "http://127.0.0.1:" + api.port();
    }

    @AfterEach
    void stop() {
        api.close();
    }

    private record Resp(int status, JsonNode body) {
        String errorCode() {
            return body.path("error").path("code").asText();
        }
    }

    private Resp call(String method, String path, String user, String body, String idemKey) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + path)).timeout(Duration.ofSeconds(5))
                .method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body))
                .header("Content-Type", "application/json");
        if (user != null) {
            b.header("X-User-Id", user);
        }
        if (idemKey != null) {
            b.header("Idempotency-Key", idemKey);
        }
        HttpResponse<String> r = client.send(b.build(), HttpResponse.BodyHandlers.ofString());
        return new Resp(r.statusCode(), json.readTree(r.body()));
    }

    private Resp call(String method, String path, String user, String body) throws Exception {
        return call(method, path, user, body, null);
    }

    @Test
    void fullHappyPath() throws Exception {
        Resp created = call("POST", "/reservations", "alice", "{\"sku\":\"PHONE\",\"quantity\":2}");
        assertEquals(201, created.status());
        assertEquals("ACTIVE", created.body().get("status").asText());
        String id = created.body().get("id").asText();

        Resp inv = call("GET", "/inventory/PHONE", null, null);
        assertEquals(3, inv.body().get("available").asInt());
        assertEquals(2, inv.body().get("reserved").asInt());

        Resp confirmed = call("POST", "/reservations/" + id + "/confirm", "alice", null);
        assertEquals(200, confirmed.status());
        assertEquals("CONFIRMED", confirmed.body().get("status").asText());

        JsonNode all = call("GET", "/inventory", null, null).body();
        assertEquals(2, all.get(0).get("sold").asInt());
    }

    @Test
    void cancelViaPostAndDelete() throws Exception {
        String id1 = call("POST", "/reservations", "alice", "{\"sku\":\"PHONE\",\"quantity\":1}").body().get("id").asText();
        String id2 = call("POST", "/reservations", "alice", "{\"sku\":\"PHONE\",\"quantity\":1}").body().get("id").asText();
        assertEquals("CANCELLED", call("POST", "/reservations/" + id1 + "/cancel", "alice", null).body().get("status").asText());
        assertEquals("CANCELLED", call("DELETE", "/reservations/" + id2, "alice", null).body().get("status").asText());
        assertEquals(5, service.report("PHONE").available());
    }

    @Test
    void expiredConfirmReturns410() throws Exception {
        String id = call("POST", "/reservations", "alice", "{\"sku\":\"PHONE\",\"quantity\":1,\"ttlSeconds\":5}")
                .body().get("id").asText();
        clock.advance(Duration.ofSeconds(5));
        Resp r = call("POST", "/reservations/" + id + "/confirm", "alice", null);
        assertEquals(410, r.status());
        assertEquals("RESERVATION_EXPIRED", r.errorCode());
    }

    @Test
    void errorMapping() throws Exception {
        assertEquals(401, call("POST", "/reservations", null, "{\"sku\":\"PHONE\",\"quantity\":1}").status());
        assertEquals(404, call("POST", "/reservations", "a", "{\"sku\":\"NOPE\",\"quantity\":1}").status());
        assertEquals(409, call("POST", "/reservations", "a", "{\"sku\":\"PHONE\",\"quantity\":3}").status());
        assertEquals(404, call("GET", "/nope", null, null).status());
        assertEquals(405, call("PUT", "/inventory", null, "{}").status());
    }

    @Test
    void strictBodyValidation() throws Exception {
        String[] bad = {
                "not json",
                "[]",
                "{\"sku\":\"PHONE\",\"quantity\":\"1\"}",
                "{\"sku\":\"PHONE\",\"quantity\":1.5}",
                "{\"sku\":\"PHONE\",\"quantity\":true}",
                "{\"sku\":123,\"quantity\":1}",
                "{\"sku\":\"PHONE\",\"quantity\":1,\"price\":0}",
                "{\"sku\":\"PHONE\",\"quantity\":1,\"ttlSeconds\":999999}",
        };
        for (String body : bad) {
            Resp r = call("POST", "/reservations", "alice", body);
            assertEquals(400, r.status(), body);
            assertEquals("INVALID_INPUT", r.errorCode(), body);
        }
        assertEquals(5, service.report("PHONE").available());
    }

    @Test
    void oversizedBodyIsRejected() throws Exception {
        String big = "{\"sku\":\"" + "A".repeat(10_000) + "\",\"quantity\":1}";
        assertEquals(413, call("POST", "/reservations", "alice", big).status());
    }

    @Test
    void idempotencyHeaderPreventsDoubleHold() throws Exception {
        String body = "{\"sku\":\"PHONE\",\"quantity\":1}";
        String a = call("POST", "/reservations", "alice", body, "order-1").body().get("id").asText();
        String b = call("POST", "/reservations", "alice", body, "order-1").body().get("id").asText();
        assertEquals(a, b);
        assertEquals(1, service.report("PHONE").reserved());
    }

    @Test
    void cannotReadOthersReservation() throws Exception {
        String id = call("POST", "/reservations", "alice", "{\"sku\":\"PHONE\",\"quantity\":1}").body().get("id").asText();
        assertEquals(404, call("GET", "/reservations/" + id, "mallory", null).status());
        assertEquals(200, call("GET", "/reservations/" + id, "alice", null).status());
    }
}
