package com.sdsi.splitter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.splitter.cli.Main;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Runs the CLI in-process and checks exit codes and output. */
class MainTest {

    private ByteArrayOutputStream out;
    private ByteArrayOutputStream err;

    @BeforeEach
    void streams() {
        out = new ByteArrayOutputStream();
        err = new ByteArrayOutputStream();
    }

    private int run(String... args) {
        return Main.run(args, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));
    }

    private String out() {
        return out.toString(StandardCharsets.UTF_8);
    }

    private String err() {
        return err.toString(StandardCharsets.UTF_8);
    }

    @Test
    void summaryOfSample() {
        assertEquals(0, run("summary", "data/expenses.json"));
        String o = out();
        assertTrue(o.contains("BALANCES"));
        assertTrue(o.contains("Esha pays Asha ₹7,504.03"), o);
        assertTrue(o.contains("4 transfer(s), proven minimum"), o);
    }

    @Test
    void asciiCurrency() {
        assertEquals(0, run("summary", "data/expenses.json", "--ascii"));
        assertTrue(out().contains("Rs.7,504.03"));
        assertFalse(out().contains("₹"));
    }

    @Test
    void greedyVsOptimalSample() {
        assertEquals(0, run("summary", "data/greedy-vs-optimal.json"));
        assertTrue(out().contains("3 transfer(s), proven minimum"), out());
    }

    @Test
    void jsonOutputIsValidAndBalanced() throws Exception {
        assertEquals(0, run("summary", "data/expenses.json", "--json"));
        JsonNode root = new ObjectMapper().readTree(out());
        BigDecimal total = BigDecimal.ZERO;
        for (JsonNode b : root.get("balances")) {
            total = total.add(b.get("net").decimalValue());
        }
        assertEquals(0, total.signum());
        assertEquals(4, root.get("settlements").size());
        assertTrue(root.get("settlementsProvenMinimal").asBoolean());
    }

    @Test
    void invalidExpensesStopTheReportByDefault(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("bad.json");
        Files.writeString(f, """
                {"members":["A","B"],"expenses":[
                  {"paidBy":"A","amount":10,"split":"equal"},
                  {"description":"oops","paidBy":"C","amount":10,"split":"equal"}]}""");
        assertEquals(1, run("summary", f.toString()));
        assertTrue(err().contains("#2 (oops)"), err());
        assertTrue(err().contains("payer 'C' is not a member"), err());
        assertEquals("", out());

        streams();
        assertEquals(0, run("summary", f.toString(), "--skip-invalid"));
        assertTrue(out().contains("SKIPPED (invalid)"), out());
        assertTrue(out().contains("1 expense(s)"), out());
    }

    @Test
    void validateCommand() {
        assertEquals(0, run("validate", "data/expenses.json"));
        assertTrue(out().startsWith("OK: 5 expense(s)"));
    }

    @Test
    void addCommandAllSplitTypes(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.json");
        Files.writeString(f, "{\"group\":\"g\",\"members\":[\"Asha\",\"Bhavesh\",\"Chirag\"]}");

        assertEquals(0, run("add", f.toString(), "--paid-by", "Asha", "--amount", "300", "--split", "equal",
                "--desc", "Dinner"));
        assertEquals(0, run("add", f.toString(), "--paid-by", "Bhavesh", "--amount", "100", "--split", "exact",
                "--shares", "Asha=40,Chirag=60"));
        assertEquals(0, run("add", f.toString(), "--paid-by", "Chirag", "--amount", "50", "--split", "percentage",
                "--shares", "Asha=50,Bhavesh=50"));
        assertEquals(0, run("add", f.toString(), "--paid-by", "Asha", "--amount", "20", "--split", "equal",
                "--among", "Bhavesh, Chirag"));

        streams();
        assertEquals(0, run("validate", f.toString()));
        assertTrue(out().startsWith("OK: 4 expense(s)"), out());
    }

    @Test
    void addRejectsInvalidExpenseAndLeavesFileAlone(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.json");
        String original = "{\"members\":[\"Asha\",\"Bhavesh\"],\"expenses\":[]}";
        Files.writeString(f, original);
        assertEquals(1, run("add", f.toString(), "--paid-by", "Asha", "--amount", "100", "--split", "percentage",
                "--shares", "Asha=50,Bhavesh=40"));
        assertTrue(err().contains("add up to 90, not 100"), err());
        assertEquals(original, Files.readString(f));
    }

    @Test
    void badCommandLines() {
        assertEquals(2, run());
        assertEquals(2, run("summary"));
        assertEquals(2, run("frobnicate", "x.json"));
        assertEquals(2, run("summary", "data/expenses.json", "--bogus"));
        assertEquals(2, run("add", "data/expenses.json", "--paid-by"));
        assertEquals(2, run("add", "data/expenses.json", "--paid-by", "Asha", "--amount", "ten", "--split", "equal"));
        assertEquals(2, run("add", "data/expenses.json", "--paid-by", "Asha", "--amount", "10", "--split", "thirds"));
        assertEquals(2, run("add", "data/expenses.json", "--paid-by", "Asha", "--amount", "10", "--split", "exact",
                "--shares", "Asha"));
        assertEquals(1, run("summary", "does-not-exist.json"));
    }
}
