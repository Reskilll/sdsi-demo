package com.sdsi.inventory;

import com.sdsi.inventory.api.HttpApi;
import com.sdsi.inventory.loader.InventoryLoadException;
import com.sdsi.inventory.loader.InventoryLoader;
import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.service.InventoryService;
import com.sdsi.inventory.sim.FlashSaleSimulation;

import java.io.IOException;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;

/**
 * Entry point.
 *
 * <pre>
 * java -jar flash-sale-inventory.jar serve    [--inventory data/inventory.json] [--host 127.0.0.1] [--port 8080] [--ttl 120]
 * java -jar flash-sale-inventory.jar simulate [--inventory data/inventory.json] [--sku PHONE-X1] [--buyers 5000]
 * </pre>
 */
public final class App {

    private static final String USAGE = """
            Usage:
              serve    [--inventory FILE] [--host HOST] [--port PORT] [--ttl SECONDS]
              simulate [--inventory FILE] [--sku SKU] [--buyers N]
            Defaults: --inventory data/inventory.json --host 127.0.0.1 --port 8080 --ttl 120
            """;

    private App() {
    }

    public static void main(String[] args) throws Exception {
        boolean hasCommand = args.length > 0 && !args[0].startsWith("--");
        String command = hasCommand ? args[0] : "serve";
        Map<String, String> opts;
        try {
            opts = parseOptions(args, hasCommand ? 1 : 0);
        } catch (IllegalArgumentException e) {
            fail(e.getMessage());
            return;
        }

        List<Product> products;
        try {
            products = new InventoryLoader().load(Path.of(opts.getOrDefault("inventory", "data/inventory.json")));
        } catch (InventoryLoadException e) {
            fail(e.getMessage());
            return;
        }

        switch (command) {
            case "serve" -> serve(products, opts);
            case "simulate" -> FlashSaleSimulation.run(products,
                    opts.getOrDefault("sku", products.get(0).sku()),
                    intOpt(opts, "buyers", 5000));
            default -> fail("unknown command: " + command);
        }
    }

    private static void serve(List<Product> products, Map<String, String> opts) throws IOException, InterruptedException {
        Duration ttl = Duration.ofSeconds(intOpt(opts, "ttl", 120));
        InventoryService service = new InventoryService(products, Clock.systemUTC(), ttl, InventoryService.DEFAULT_RETENTION);
        service.startExpirySweeper(Duration.ofSeconds(1));
        HttpApi api = new HttpApi(service, opts.getOrDefault("host", "127.0.0.1"), intOpt(opts, "port", 8080));
        api.start();
        System.out.printf("Loaded %d products. Listening on http://%s:%d (default TTL %ds)%n",
                products.size(), opts.getOrDefault("host", "127.0.0.1"), api.port(), ttl.toSeconds());

        CountDownLatch stopped = new CountDownLatch(1);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            api.close();
            service.close();
            stopped.countDown();
        }));
        stopped.await();
    }

    static Map<String, String> parseOptions(String[] args, int start) {
        Map<String, String> opts = new HashMap<>();
        for (int i = start; i < args.length; i++) {
            String a = args[i];
            if (!a.startsWith("--") || i + 1 >= args.length) {
                throw new IllegalArgumentException("bad argument: " + a);
            }
            opts.put(a.substring(2), args[++i]);
        }
        return opts;
    }

    private static int intOpt(Map<String, String> opts, String key, int fallback) {
        String v = opts.get(key);
        if (v == null) {
            return fallback;
        }
        try {
            return Integer.parseInt(v);
        } catch (NumberFormatException e) {
            fail("--" + key + " must be an integer");
            return fallback;
        }
    }

    private static void fail(String message) {
        System.err.println("error: " + message);
        System.err.print(USAGE);
        System.exit(2);
    }
}
