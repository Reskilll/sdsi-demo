package com.sdsi.splitter;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sdsi.splitter.core.ValidationException;
import com.sdsi.splitter.io.ExpenseFile;
import com.sdsi.splitter.model.MemberBalance;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ExpenseFileTest {

    private static final String MEMBERS = "\"members\":[\"Asha\",\"Bhavesh\",\"Chirag\"]";

    @Test
    void loadsBundledSample() {
        ExpenseFile.BatchResult r = ExpenseFile.load(Path.of("data/expenses.json"));
        assertFalse(r.hasErrors(), r.rejected().toString());
        assertEquals(5, r.group().expenses().size());
        assertEquals(0, r.group().balances().stream().mapToLong(MemberBalance::net).sum());
        assertEquals(4, r.group().settleUp().settlements().size());
    }

    @Test
    void acceptsASingleExpenseObject() {
        ExpenseFile.BatchResult r = ExpenseFile.parse("{" + MEMBERS
                + ",\"expenses\":{\"paidBy\":\"Asha\",\"amount\":90,\"split\":\"equal\"}}");
        assertEquals(1, r.group().expenses().size());
    }

    @Test
    void acceptsNoExpensesAndNumericStrings() {
        assertEquals(0, ExpenseFile.parse("{" + MEMBERS + "}").group().expenses().size());
        ExpenseFile.BatchResult r = ExpenseFile.parse("{" + MEMBERS
                + ",\"expenses\":[{\"paidBy\":\"Asha\",\"amount\":\"250.50\",\"split\":\"EXACT\",\"shares\":{\"Bhavesh\":\"250.5\"}}]}");
        assertEquals(25050, r.group().expenses().get(0).amountPaise());
    }

    @Test
    void collectsEveryInvalidExpenseWithItsPosition() {
        String json = "{" + MEMBERS + ",\"expenses\":["
                + "{\"paidBy\":\"Asha\",\"amount\":90,\"split\":\"equal\"},"
                + "{\"description\":\"bad pct\",\"paidBy\":\"Asha\",\"amount\":90,\"split\":\"percentage\",\"shares\":{\"Asha\":50,\"Bhavesh\":40}},"
                + "{\"paidBy\":\"Zed\",\"amount\":90,\"split\":\"equal\"},"
                + "{\"paidBy\":\"Asha\",\"amount\":true,\"split\":\"weird\",\"typo\":1}"
                + "]}";
        ExpenseFile.BatchResult r = ExpenseFile.parse(json);
        assertEquals(1, r.group().expenses().size());
        assertEquals(3, r.rejected().size());
        assertEquals(1, r.rejected().get(0).index());
        assertEquals("bad pct", r.rejected().get(0).description());
        assertTrue(r.rejected().get(1).errors().get(0).contains("payer 'Zed'"));
        assertEquals(3, r.rejected().get(2).errors().size(), r.rejected().get(2).errors().toString());
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "''                                       | empty",
            "not json                                 | not valid JSON",
            "[]                                       | must contain a JSON object",
            "{}                                       | members\" is required",
            "{\"members\":\"Asha\"}                   | must be an array",
            "{\"members\":[1,2]}                      | only strings",
            "{\"members\":[\"A\"],\"oops\":1}         | unknown field 'oops'",
            "{\"members\":[\"A\"],\"expenses\":5}     | must be an array of expenses",
            "{\"members\":[\"A\"],\"members\":[\"B\"]} | not valid JSON",
            "{\"members\":[\"A\",\"a\"]}              | more than once",
    })
    void rejectsBrokenFiles(String json, String fragment) {
        ValidationException e = assertThrows(ValidationException.class, () -> ExpenseFile.parse(json));
        assertTrue(e.getMessage().contains(fragment), e.getMessage());
    }

    @Test
    void rejectsHugeNumbers() {
        String json = "{" + MEMBERS + ",\"expenses\":[{\"paidBy\":\"Asha\",\"amount\":" + "9".repeat(40) + ",\"split\":\"equal\"}]}";
        assertThrows(ValidationException.class, () -> ExpenseFile.parse(json));
    }

    @Test
    void appendAddsValidExpenseAndKeepsFileOtherwise(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.json");
        Files.writeString(f, "{" + MEMBERS + ",\"expenses\":[]}");

        ObjectNode ok = ExpenseFile.mapper().createObjectNode()
                .put("paidBy", "Asha").put("amount", 300).put("split", "equal");
        ExpenseFile.append(f, ok);
        assertEquals(1, ExpenseFile.load(f).group().expenses().size());

        String before = Files.readString(f);
        ObjectNode bad = ExpenseFile.mapper().createObjectNode()
                .put("paidBy", "Zed").put("amount", 300).put("split", "equal");
        assertThrows(ValidationException.class, () -> ExpenseFile.append(f, bad));
        assertEquals(before, Files.readString(f));
        try (var files = Files.list(dir)) {
            assertEquals(1, files.count(), "no temp files left behind");
        }
    }

    @Test
    void appendToSingleObjectFileTurnsItIntoAnArray(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.json");
        Files.writeString(f, "{" + MEMBERS + ",\"expenses\":{\"paidBy\":\"Asha\",\"amount\":90,\"split\":\"equal\"}}");
        ExpenseFile.append(f, ExpenseFile.mapper().createObjectNode()
                .put("paidBy", "Bhavesh").put("amount", 30).put("split", "equal"));
        assertEquals(2, ExpenseFile.load(f).group().expenses().size());
    }

    @Test
    void missingFile(@TempDir Path dir) {
        ValidationException e = assertThrows(ValidationException.class, () -> ExpenseFile.load(dir.resolve("nope.json")));
        assertTrue(e.getMessage().contains("file not found"));
    }
}
