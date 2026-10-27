package com.urlshortener;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class UrlShortenerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shortenAndResolveFlow() throws Exception {
        // 1. Shorten a URL
        String requestBody = """
            {"url": "https://example.com/test-page"}
            """;

        String responseJson = mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.shortCode").isNotEmpty())
            .andExpect(jsonPath("$.shortUrl").isNotEmpty())
            .andExpect(jsonPath("$.originalUrl").value("https://example.com/test-page"))
            .andReturn()
            .getResponse()
            .getContentAsString();

        // Extract the short code from the response
        // Simple extraction: find the shortCode value
        String shortCode = extractJsonValue(responseJson, "shortCode");
        System.out.println("Generated short code: " + shortCode);

        // 2. Resolve it — should redirect (302)
        mockMvc.perform(get("/" + shortCode))
            .andExpect(status().isFound())
            .andExpect(header().string("Location", "https://example.com/test-page"));

        // 3. Stats should show at least 1 click
        mockMvc.perform(get("/api/stats/" + shortCode))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.shortCode").value(shortCode))
            .andExpect(jsonPath("$.totalClicks").value(greaterThanOrEqualTo(1)))
            .andExpect(jsonPath("$.clicksPerDay").isMap());
    }

    @Test
    void idempotentShorten() throws Exception {
        String requestBody = """
            {"url": "https://example.com/idempotent-test"}
            """;

        String first = mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();

        String second = mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();

        String firstCode = extractJsonValue(first, "shortCode");
        String secondCode = extractJsonValue(second, "shortCode");
        assertEquals(firstCode, secondCode, "Same URL should return the same short code");
    }

    @Test
    void resolveUnknownCodeReturns404() throws Exception {
        mockMvc.perform(get("/nonexistent123"))
            .andExpect(status().isNotFound());
    }

    @Test
    void shortenWithCustomAlias() throws Exception {
        String requestBody = """
            {"url": "https://example.com/custom", "customAlias": "myCstm"}
            """;

        mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.shortCode").value("myCstm"));

        // Resolve custom alias
        mockMvc.perform(get("/myCstm"))
            .andExpect(status().isFound())
            .andExpect(header().string("Location", "https://example.com/custom"));
    }

    @Test
    void blockJavascriptScheme() throws Exception {
        String requestBody = """
            {"url": "javascript:alert('xss')"}
            """;

        mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isBadRequest());
    }

    @Test
    void validateCustomAliasLength() throws Exception {
        String requestBody = """
            {"url": "https://example.com", "customAlias": "ab"}
            """;

        mockMvc.perform(post("/api/shorten")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
            .andExpect(status().isBadRequest());
    }

    @Test
    void statsForUnknownCode() throws Exception {
        mockMvc.perform(get("/api/stats/nonexistent"))
            .andExpect(status().isNotFound());
    }

    // ===== helpers =====

    private String extractJsonValue(String json, String key) {
        // Simple extraction for test purposes — the short code is alphanumeric
        String search = "\"" + key + "\":\"";
        int start = json.indexOf(search) + search.length();
        int end = json.indexOf('"', start);
        return json.substring(start, end);
    }

    private void assertEquals(String expected, String actual, String message) {
        if (!expected.equals(actual)) {
            throw new AssertionError(message + ": expected " + expected + " but got " + actual);
        }
    }
}