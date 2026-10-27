package com.sdsi.splitter.io;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sdsi.splitter.core.Group;
import com.sdsi.splitter.core.ValidationException;
import com.sdsi.splitter.model.ExpenseRequest;
import com.sdsi.splitter.model.SplitType;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Reads and writes the expenses file (M4).
 *
 * <pre>
 * {
 *   "group": "Goa Trip",
 *   "members": ["Asha", "Bhavesh", "Chirag"],
 *   "expenses": [                                   // an array (batch) or a single object
 *     {"description": "Hotel", "paidBy": "Asha", "amount": 9000, "split": "equal"},
 *     {"description": "Cab", "paidBy": "Chirag", "amount": 900, "split": "exact",
 *      "shares": {"Asha": 300, "Chirag": 600}},
 *     {"description": "Scuba", "paidBy": "Bhavesh", "amount": 5000, "split": "percentage",
 *      "shares": {"Asha": 50, "Bhavesh": 25, "Chirag": 25}}
 *   ]
 * }
 * </pre>
 */
public final class ExpenseFile {

    static final long MAX_FILE_BYTES = 20L * 1024 * 1024;
    private static final Set<String> TOP_FIELDS = Set.of("group", "members", "expenses");
    private static final Set<String> EXPENSE_FIELDS =
            Set.of("id", "description", "paidBy", "amount", "split", "participants", "shares");
    private static final int MAX_NUMBER_TEXT = 30;

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
            .enable(SerializationFeature.INDENT_OUTPUT);

    static {
        MAPPER.getFactory().setStreamReadConstraints(StreamReadConstraints.builder()
                .maxNestingDepth(16).maxStringLength(10_000).maxNumberLength(MAX_NUMBER_TEXT).build());
    }

    /** One expense that failed validation. {@code index} is its 0-based position in the file. */
    public record Rejected(int index, String description, List<String> errors) {
    }

    /** The group built from every valid expense, plus every rejected one with its reasons. */
    public record BatchResult(Group group, List<Rejected> rejected) {
        public boolean hasErrors() {
            return !rejected.isEmpty();
        }
    }

    private ExpenseFile() {
    }

    public static BatchResult load(Path file) {
        return process(read(file));
    }

    public static BatchResult parse(String json) {
        return process(readTree(json));
    }

    /**
     * Validates one more expense against the file and, only if it is valid and the rest of the file is
     * too, appends it. The write goes to a temporary file first and is then moved into place, so a
     * crash can never leave a half-written file.
     */
    public static void append(Path file, ObjectNode expense) {
        ObjectNode root = read(file);
        ArrayNode list;
        JsonNode existing = root.get("expenses");
        if (existing == null || existing.isNull()) {
            list = root.putArray("expenses");
        } else if (existing.isArray()) {
            list = (ArrayNode) existing;
        } else {
            list = MAPPER.createArrayNode().add(existing);
            root.set("expenses", list);
        }
        list.add(expense);

        BatchResult check = process(root);
        if (check.hasErrors()) {
            List<String> errors = new ArrayList<>();
            check.rejected().forEach(r -> r.errors().forEach(e -> errors.add("expense #" + (r.index() + 1) + ": " + e)));
            throw new ValidationException(errors);
        }
        try {
            Path tmp = Files.createTempFile(file.toAbsolutePath().getParent(), ".expenses-", ".tmp");
            try {
                Files.writeString(tmp, MAPPER.writeValueAsString(root) + System.lineSeparator(), StandardCharsets.UTF_8);
                try {
                    Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
                } catch (AtomicMoveNotSupportedException e) {
                    Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
                }
            } finally {
                Files.deleteIfExists(tmp);
            }
        } catch (IOException e) {
            throw new ValidationException("could not write " + file + ": " + e.getMessage());
        }
    }

    public static ObjectMapper mapper() {
        return MAPPER;
    }

    // ------------------------------------------------------------------ parsing

    private static ObjectNode read(Path file) {
        try {
            if (!Files.isRegularFile(file)) {
                throw new ValidationException("file not found: " + file);
            }
            if (Files.size(file) > MAX_FILE_BYTES) {
                throw new ValidationException("file is larger than " + MAX_FILE_BYTES / (1024 * 1024) + " MB");
            }
            return readTree(Files.readString(file, StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ValidationException("could not read " + file + ": " + e.getMessage());
        }
    }

    private static ObjectNode readTree(String json) {
        JsonNode root;
        try {
            root = MAPPER.readTree(json);
        } catch (JsonProcessingException e) {
            throw new ValidationException("not valid JSON: " + e.getOriginalMessage());
        }
        if (root == null || root.isMissingNode()) {
            throw new ValidationException("the file is empty");
        }
        if (!root.isObject()) {
            throw new ValidationException("the file must contain a JSON object with \"members\" and \"expenses\"");
        }
        return (ObjectNode) root;
    }

    private static BatchResult process(ObjectNode root) {
        List<String> topErrors = new ArrayList<>();
        unknownFields(root, TOP_FIELDS, topErrors, "");
        JsonNode groupName = root.get("group");
        if (groupName != null && !groupName.isTextual()) {
            topErrors.add("\"group\" must be a string");
        }
        List<String> members = stringList(root.get("members"), "\"members\"", topErrors, true);
        if (!topErrors.isEmpty()) {
            throw new ValidationException(topErrors);
        }
        Group group = new Group(groupName == null ? null : groupName.asText(), members);

        JsonNode expenses = root.get("expenses");
        List<JsonNode> items = new ArrayList<>();
        if (expenses == null || expenses.isNull()) {
            // A group with no expenses yet is valid: everyone is settled.
        } else if (expenses.isArray()) {
            expenses.forEach(items::add);
        } else if (expenses.isObject()) {
            items.add(expenses); // a single expense
        } else {
            throw new ValidationException("\"expenses\" must be an array of expenses or a single expense object");
        }

        List<Rejected> rejected = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            JsonNode node = items.get(i);
            String description = node.path("description").isTextual() ? node.get("description").asText() : null;
            try {
                group.add(toRequest(node));
            } catch (ValidationException e) {
                rejected.add(new Rejected(i, description, e.errors()));
            }
        }
        return new BatchResult(group, rejected);
    }

    static ExpenseRequest toRequest(JsonNode node) {
        if (!node.isObject()) {
            throw new ValidationException("each expense must be a JSON object");
        }
        List<String> errors = new ArrayList<>();
        unknownFields(node, EXPENSE_FIELDS, errors, "");

        String id = optionalText(node, "id", errors);
        String description = optionalText(node, "description", errors);
        String paidBy = optionalText(node, "paidBy", errors);
        BigDecimal amount = decimal(node.get("amount"), "amount", errors);

        SplitType split = null;
        JsonNode s = node.get("split");
        if (s == null || s.isNull()) {
            errors.add("split is required (equal, exact or percentage)");
        } else if (!s.isTextual() || (split = SplitType.parse(s.asText())) == null) {
            errors.add("split must be one of: equal, exact, percentage");
        }

        List<String> participants = node.has("participants")
                ? stringList(node.get("participants"), "participants", errors, false) : null;

        Map<String, BigDecimal> shares = null;
        JsonNode sh = node.get("shares");
        if (sh != null && !sh.isNull()) {
            if (!sh.isObject()) {
                errors.add("shares must be an object like {\"Asha\": 300, \"Bhavesh\": 200}");
            } else {
                shares = new LinkedHashMap<>();
                for (Iterator<Map.Entry<String, JsonNode>> it = sh.fields(); it.hasNext(); ) {
                    Map.Entry<String, JsonNode> e = it.next();
                    shares.put(e.getKey(), decimal(e.getValue(), "share for '" + e.getKey() + "'", errors));
                }
            }
        }
        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        return new ExpenseRequest(id, description, paidBy, amount, split, participants, shares);
    }

    /** Accepts a JSON number or a numeric string ("250.50"). Rejects booleans, objects, NaN and the like. */
    private static BigDecimal decimal(JsonNode v, String label, List<String> errors) {
        if (v == null || v.isNull()) {
            errors.add(label + " is required");
            return null;
        }
        if (v.isNumber()) {
            return v.decimalValue();
        }
        if (v.isTextual() && v.asText().strip().length() <= MAX_NUMBER_TEXT) {
            try {
                return new BigDecimal(v.asText().strip());
            } catch (NumberFormatException ignored) {
                // fall through to the error below
            }
        }
        errors.add(label + " must be a number");
        return null;
    }

    private static String optionalText(JsonNode node, String field, List<String> errors) {
        JsonNode v = node.get(field);
        if (v == null || v.isNull()) {
            return null;
        }
        if (!v.isTextual()) {
            errors.add(field + " must be a string");
            return null;
        }
        return v.asText();
    }

    private static List<String> stringList(JsonNode v, String label, List<String> errors, boolean required) {
        if (v == null || v.isNull()) {
            if (required) {
                errors.add(label + " is required");
            }
            return required ? List.of() : null;
        }
        if (!v.isArray()) {
            errors.add(label + " must be an array of names");
            return List.of();
        }
        List<String> out = new ArrayList<>();
        for (JsonNode n : v) {
            if (!n.isTextual()) {
                errors.add(label + " must contain only strings");
                return List.of();
            }
            out.add(n.asText());
        }
        return out;
    }

    private static void unknownFields(JsonNode node, Set<String> allowed, List<String> errors, String where) {
        node.fieldNames().forEachRemaining(f -> {
            if (!allowed.contains(f)) {
                errors.add(where + "unknown field '" + f + "' (allowed: " + String.join(", ", allowed.stream().sorted().toList()) + ")");
            }
        });
    }
}
