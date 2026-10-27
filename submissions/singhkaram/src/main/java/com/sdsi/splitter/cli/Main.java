package com.sdsi.splitter.cli;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sdsi.splitter.core.ValidationException;
import com.sdsi.splitter.io.ExpenseFile;
import com.sdsi.splitter.io.ReportWriter;
import com.sdsi.splitter.model.SplitType;

import java.io.PrintStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Command-line entry point. Exit codes: 0 success, 1 invalid data, 2 bad command line.
 */
public final class Main {

    static final String USAGE = """
            Usage:
              summary  FILE [--skip-invalid] [--json] [--ascii]
                       Process every expense in FILE and print expenses, balances and settlements.
                       By default any invalid expense stops the run; --skip-invalid reports and skips them.
              validate FILE
                       Check FILE and list every problem without printing a report.
              add      FILE --paid-by NAME --amount N --split equal|exact|percentage
                       [--among A,B,C]          equal split between these members (default: everyone)
                       [--shares A=300,B=200]   exact rupees or percentages per member
                       [--desc TEXT] [--id ID]
                       Validate one expense and append it to FILE.
            """;

    private static final Set<String> FLAGS = Set.of("skip-invalid", "json", "ascii");

    private Main() {
    }

    public static void main(String[] args) {
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        PrintStream err = new PrintStream(System.err, true, StandardCharsets.UTF_8);
        System.exit(run(args, out, err));
    }

    /** Testable entry point: returns the exit code instead of exiting. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        if (args.length == 0 || args[0].equals("help") || args[0].equals("--help")) {
            out.print(USAGE);
            return args.length == 0 ? 2 : 0;
        }
        if (args.length < 2) {
            err.println("error: missing FILE");
            err.print(USAGE);
            return 2;
        }
        Map<String, String> opts;
        try {
            opts = parseOptions(args);
        } catch (IllegalArgumentException e) {
            err.println("error: " + e.getMessage());
            err.print(USAGE);
            return 2;
        }
        Path file = Path.of(args[1]);
        try {
            return switch (args[0]) {
                case "summary" -> summary(file, opts, out, err);
                case "validate" -> validate(file, out, err);
                case "add" -> add(file, opts, out);
                default -> {
                    err.println("error: unknown command '" + args[0] + "'");
                    err.print(USAGE);
                    yield 2;
                }
            };
        } catch (ValidationException e) {
            err.println("error:");
            e.errors().forEach(m -> err.println("  - " + m));
            return 1;
        } catch (IllegalArgumentException e) {
            err.println("error: " + e.getMessage());
            return 2;
        }
    }

    private static int summary(Path file, Map<String, String> opts, PrintStream out, PrintStream err) {
        ExpenseFile.BatchResult result = ExpenseFile.load(file);
        if (result.hasErrors() && !opts.containsKey("skip-invalid")) {
            printRejected(result, err);
            err.println("No report printed. Fix the expenses above, or rerun with --skip-invalid.");
            return 1;
        }
        ReportWriter writer = new ReportWriter(opts.containsKey("ascii"));
        out.print(opts.containsKey("json")
                ? writer.json(result.group(), result.rejected()) + System.lineSeparator()
                : writer.text(result.group(), result.rejected()));
        return 0;
    }

    private static int validate(Path file, PrintStream out, PrintStream err) {
        ExpenseFile.BatchResult result = ExpenseFile.load(file);
        if (result.hasErrors()) {
            printRejected(result, err);
            return 1;
        }
        out.println("OK: " + result.group().expenses().size() + " expense(s), "
                + result.group().members().size() + " members, no problems found.");
        return 0;
    }

    private static int add(Path file, Map<String, String> opts, PrintStream out) {
        ObjectNode e = ExpenseFile.mapper().createObjectNode();
        if (opts.containsKey("id")) {
            e.put("id", opts.get("id"));
        }
        if (opts.containsKey("desc")) {
            e.put("description", opts.get("desc"));
        }
        e.put("paidBy", require(opts, "paid-by"));
        e.put("amount", number(require(opts, "amount"), "--amount"));
        String splitRaw = require(opts, "split");
        SplitType split = SplitType.parse(splitRaw);
        if (split == null) {
            throw new IllegalArgumentException("--split must be equal, exact or percentage");
        }
        e.put("split", split.name().toLowerCase());
        if (opts.containsKey("among")) {
            ArrayNode among = e.putArray("participants");
            for (String name : opts.get("among").split(",")) {
                among.add(name.strip());
            }
        }
        if (opts.containsKey("shares")) {
            ObjectNode shares = e.putObject("shares");
            for (String pair : opts.get("shares").split(",")) {
                String[] kv = pair.split("=", 2);
                if (kv.length != 2 || kv[0].isBlank()) {
                    throw new IllegalArgumentException("--shares must look like Asha=300,Bhavesh=200");
                }
                if (shares.has(kv[0].strip())) {
                    throw new IllegalArgumentException("--shares lists '" + kv[0].strip() + "' twice");
                }
                shares.put(kv[0].strip(), number(kv[1], "--shares value for " + kv[0].strip()));
            }
        }
        ExpenseFile.append(file, e);
        out.println("Added. Run 'summary " + file + "' to see updated balances.");
        return 0;
    }

    private static BigDecimal number(String raw, String label) {
        try {
            return new BigDecimal(raw.strip());
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException(label + " must be a number, got '" + raw + "'");
        }
    }

    private static String require(Map<String, String> opts, String key) {
        String v = opts.get(key);
        if (v == null || v.isBlank()) {
            throw new IllegalArgumentException("--" + key + " is required");
        }
        return v;
    }

    private static void printRejected(ExpenseFile.BatchResult result, PrintStream err) {
        err.println(result.rejected().size() + " invalid expense(s):");
        for (ExpenseFile.Rejected r : result.rejected()) {
            err.println("  #" + (r.index() + 1) + (r.description() == null ? "" : " (" + r.description() + ")") + ":");
            r.errors().forEach(m -> err.println("      - " + m));
        }
    }

    static Map<String, String> parseOptions(String[] args) {
        Map<String, String> opts = new HashMap<>();
        for (int i = 2; i < args.length; i++) {
            String a = args[i];
            if (!a.startsWith("--")) {
                throw new IllegalArgumentException("unexpected argument '" + a + "'");
            }
            String key = a.substring(2);
            if (FLAGS.contains(key)) {
                opts.put(key, "true");
            } else if (List.of("paid-by", "amount", "split", "among", "shares", "desc", "id").contains(key)) {
                if (i + 1 >= args.length) {
                    throw new IllegalArgumentException(a + " needs a value");
                }
                opts.put(key, args[++i]);
            } else {
                throw new IllegalArgumentException("unknown option " + a);
            }
        }
        return opts;
    }
}
