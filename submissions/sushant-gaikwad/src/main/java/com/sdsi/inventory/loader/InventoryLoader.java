package com.sdsi.inventory.loader;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.inventory.model.Product;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Loads and validates the product catalogue (M1).
 *
 * <p>Accepted shapes: {@code {"products": [ ... ]}} or a bare array {@code [ ... ]}. Each product needs
 * {@code sku}, {@code stock}; {@code name} defaults to the SKU and {@code perUserLimit} to
 * {@link #DEFAULT_PER_USER_LIMIT}. All problems are collected and reported together so a broken
 * file can be fixed in one pass.
 */
public final class InventoryLoader {

    public static final int DEFAULT_PER_USER_LIMIT = 1;
    static final long MAX_FILE_BYTES = 10L * 1024 * 1024;
    static final int MAX_STOCK = 10_000_000;
    private static final Pattern SKU = Pattern.compile("[A-Za-z0-9_.-]{1,64}");

    private final ObjectMapper mapper;

    public InventoryLoader() {
        mapper = new ObjectMapper();
        mapper.enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION);
        mapper.getFactory().setStreamReadConstraints(StreamReadConstraints.builder()
                .maxNestingDepth(32).maxStringLength(10_000).build());
    }

    public List<Product> load(Path file) {
        try {
            if (!Files.isRegularFile(file)) {
                throw new InventoryLoadException("inventory file not found: " + file);
            }
            if (Files.size(file) > MAX_FILE_BYTES) {
                throw new InventoryLoadException("inventory file exceeds " + MAX_FILE_BYTES + " bytes");
            }
            return parse(Files.readString(file));
        } catch (IOException e) {
            throw new InventoryLoadException("cannot read inventory file " + file + ": " + e.getMessage(), e);
        }
    }

    public List<Product> parse(String json) {
        JsonNode root;
        try {
            root = mapper.readTree(json);
        } catch (JsonProcessingException e) {
            throw new InventoryLoadException("inventory is not valid JSON: " + e.getOriginalMessage(), e);
        }
        if (root == null || root.isMissingNode()) {
            throw new InventoryLoadException("inventory file is empty");
        }
        JsonNode items = root.isArray() ? root : root.get("products");
        if (items == null || !items.isArray()) {
            throw new InventoryLoadException("expected a JSON array or an object with a \"products\" array");
        }
        if (items.isEmpty()) {
            throw new InventoryLoadException("inventory contains no products");
        }

        List<String> errors = new ArrayList<>();
        List<Product> products = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < items.size(); i++) {
            JsonNode n = items.get(i);
            String where = "products[" + i + "]";
            if (!n.isObject()) {
                errors.add(where + ": must be an object");
                continue;
            }
            int before = errors.size();

            String sku = textField(n, "sku");
            if (sku == null) {
                errors.add(where + ".sku: required string");
            } else if (!SKU.matcher(sku).matches()) {
                errors.add(where + ".sku: must be 1-64 chars of [A-Za-z0-9_.-]");
            } else if (!seen.add(sku)) {
                errors.add(where + ".sku: duplicate SKU '" + sku + "'");
            }

            String name = n.has("name") ? textField(n, "name") : sku;
            if (n.has("name") && (name == null || name.isBlank())) {
                errors.add(where + ".name: must be a non-empty string");
            }

            Integer stock = intField(n, "stock", errors, where, 0, MAX_STOCK, null);
            Integer limit = intField(n, "perUserLimit", errors, where, 1, MAX_STOCK, DEFAULT_PER_USER_LIMIT);

            if (errors.size() == before) {
                products.add(new Product(sku, name.strip(), stock, limit));
            }
        }
        if (!errors.isEmpty()) {
            throw new InventoryLoadException("invalid inventory:\n  - " + String.join("\n  - ", errors));
        }
        return List.copyOf(products);
    }

    private static String textField(JsonNode n, String field) {
        JsonNode v = n.get(field);
        return v != null && v.isTextual() ? v.asText() : null;
    }

    /** Accepts only true JSON integers (no strings, floats or booleans) inside [min, max]. */
    private static Integer intField(JsonNode n, String field, List<String> errors, String where,
                                    int min, int max, Integer fallback) {
        JsonNode v = n.get(field);
        if (v == null || v.isNull()) {
            if (fallback == null) {
                errors.add(where + "." + field + ": required integer");
            }
            return fallback;
        }
        if (!v.isIntegralNumber() || !v.canConvertToInt()) {
            errors.add(where + "." + field + ": must be an integer");
            return null;
        }
        int value = v.intValue();
        if (value < min || value > max) {
            errors.add(where + "." + field + ": must be between " + min + " and " + max);
            return null;
        }
        return value;
    }
}
