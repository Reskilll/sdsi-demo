package com.sdsi.inventory;

import com.sdsi.inventory.loader.InventoryLoadException;
import com.sdsi.inventory.loader.InventoryLoader;
import com.sdsi.inventory.model.Product;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InventoryLoaderTest {

    private final InventoryLoader loader = new InventoryLoader();

    @Test
    void loadsBundledSampleFile() {
        List<Product> products = loader.load(Path.of("data/inventory.json"));
        assertEquals(5, products.size());
        assertEquals(new Product("PHONE-X1", "Galaxy X1 Smartphone", 100, 2), products.get(0));
    }

    @Test
    void acceptsBareArrayAndAppliesDefaults() {
        List<Product> p = loader.parse("[{\"sku\":\"A\",\"stock\":3}]");
        assertEquals(new Product("A", "A", 3, InventoryLoader.DEFAULT_PER_USER_LIMIT), p.get(0));
    }

    @Test
    void reportsAllProblemsAtOnce() {
        String json = """
                {"products":[
                  {"sku":"A","stock":-1},
                  {"sku":"A","stock":1},
                  {"stock":1},
                  {"sku":"B","stock":"10"},
                  {"sku":"C","stock":1.5,"perUserLimit":0}
                ]}""";
        InventoryLoadException e = assertThrows(InventoryLoadException.class, () -> loader.parse(json));
        String msg = e.getMessage();
        assertTrue(msg.contains("products[0].stock"), msg);
        assertTrue(msg.contains("duplicate SKU 'A'"), msg);
        assertTrue(msg.contains("products[2].sku"), msg);
        assertTrue(msg.contains("products[3].stock: must be an integer"), msg);
        assertTrue(msg.contains("products[4].perUserLimit"), msg);
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "''                                  | empty",
            "not json                            | not valid JSON",
            "{}                                  | expected a JSON array",
            "{\"products\":{}}                   | expected a JSON array",
            "{\"products\":[]}                   | no products",
            "[1]                                 | must be an object",
            "[{\"sku\":\"A\",\"sku\":\"B\",\"stock\":1}] | not valid JSON",
            "[{\"sku\":\"bad sku\",\"stock\":1}] | 1-64 chars",
            "[{\"sku\":\"A\",\"stock\":99999999999}] | must be an integer",
            "[{\"sku\":\"A\",\"name\":\"  \",\"stock\":1}] | name"
    })
    void rejectsMalformedInput(String json, String expectedFragment) {
        InventoryLoadException e = assertThrows(InventoryLoadException.class, () -> loader.parse(json));
        assertTrue(e.getMessage().contains(expectedFragment), e.getMessage());
    }

    @Test
    void missingFileGivesClearError(@TempDir Path dir) {
        InventoryLoadException e = assertThrows(InventoryLoadException.class,
                () -> loader.load(dir.resolve("nope.json")));
        assertTrue(e.getMessage().contains("not found"));
    }

    @Test
    void zeroStockIsAllowed(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("inv.json");
        Files.writeString(f, "[{\"sku\":\"Z\",\"stock\":0,\"perUserLimit\":1}]");
        assertEquals(0, loader.load(f).get(0).stock());
    }
}
