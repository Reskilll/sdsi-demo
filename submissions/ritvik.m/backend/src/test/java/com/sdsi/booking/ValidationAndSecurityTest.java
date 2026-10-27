package com.sdsi.booking;

import com.fasterxml.jackson.databind.JsonNode;
import com.sdsi.booking.support.IntegrationTestBase;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.time.LocalDate;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ValidationAndSecurityTest extends IntegrationTestBase {

    @Test
    void roomCatalogueRequiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/rooms"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("WWW-Authenticate", containsString("Basic")))
                .andExpect(header().exists("X-Request-Id"));

        mockMvc.perform(get("/api/rooms")
                        .with(org.springframework.security.test.web.servlet.request
                                .SecurityMockMvcRequestPostProcessors.httpBasic("test", "wrong")))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/rooms").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(6));
    }

    @Test
    void healthEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void malformedJsonIsRejectedWithoutLeakingDetails() throws Exception {
        mockMvc.perform(post("/api/bookings").with(auth())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"roomId\": "))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_JSON"));
    }

    @Test
    void beanValidationErrorsAreStructured() throws Exception {
        LocalDate date = futureDate();
        var body = bookingPayload("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);
        body.put("title", "   ");
        body.remove("organiser");
        JsonNode error = json(postBooking(body)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andReturn());
        assertThat(error.get("errors").findValuesAsText("field"))
                .contains("title", "organiser");
    }

    @Test
    void invalidQueryParametersReturnFourHundred() throws Exception {
        mockMvc.perform(get("/api/find-slot")
                        .param("date", "not-a-date")
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PARAMETER"));

        mockMvc.perform(get("/api/find-slot")
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MISSING_PARAMETER"));

        mockMvc.perform(get("/api/bookings").param("page", "-1").with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PAGE"));

        mockMvc.perform(get("/api/bookings").param("size", "101").with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PAGE_SIZE"));

        mockMvc.perform(get("/api/bookings").param("status", "DRAFT").with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PARAMETER"));
    }

    @Test
    void unknownResourceAndUnsupportedMethod() throws Exception {
        mockMvc.perform(get("/api/does-not-exist").with(auth()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));

        mockMvc.perform(get("/api/bookings/{id}", UUID.randomUUID()).with(auth()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));

        mockMvc.perform(get("/api/bookings/not-a-uuid").with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PARAMETER"));

        mockMvc.perform(put("/api/rooms").with(auth())
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(jsonPath("$.code").value("METHOD_NOT_ALLOWED"));
    }

    @Test
    void unsupportedContentTypeIsRejected() throws Exception {
        mockMvc.perform(post("/api/bookings").with(auth())
                        .contentType(MediaType.TEXT_PLAIN)
                        .content("hello"))
                .andExpect(status().isUnsupportedMediaType())
                .andExpect(jsonPath("$.code").value("UNSUPPORTED_MEDIA_TYPE"));
    }

    @Test
    void oversizedRequestBodyIsRejected() throws Exception {
        String huge = "x".repeat(140 * 1024);
        mockMvc.perform(post("/api/bookings").with(auth())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"description\":\"" + huge + "\"}"))
                .andExpect(status().is(413))
                .andExpect(jsonPath("$.code").value("PAYLOAD_TOO_LARGE"));
    }

    @Test
    void requestIdIsEchoedOnlyWhenSafe() throws Exception {
        mockMvc.perform(get("/api/rooms").with(auth())
                        .header("X-Request-Id", "trace-12345678"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-Request-Id", "trace-12345678"));

        String generated = mockMvc.perform(get("/api/rooms").with(auth())
                        .header("X-Request-Id", "bad id with spaces"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getHeader("X-Request-Id");
        assertThat(generated).isNotBlank().isNotEqualTo("bad id with spaces");
    }

    @Test
    void corsAllowsConfiguredOriginAndRejectsOthers() throws Exception {
        mockMvc.perform(options("/api/rooms")
                        .header("Origin", "http://localhost:5173")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"));

        mockMvc.perform(options("/api/rooms")
                        .header("Origin", "https://evil.example")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isForbidden());
    }

    @Test
    void cancelledBookingCanBeReadButNotUpdated() throws Exception {
        LocalDate date = futureDate();
        JsonNode booking = createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);
        String id = booking.get("id").asText();
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .patch("/api/bookings/{id}/cancel", id).with(auth()))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/bookings/{id}", id).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"));
    }
}
