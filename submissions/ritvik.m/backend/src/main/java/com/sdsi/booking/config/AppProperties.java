package com.sdsi.booking.config;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.time.LocalTime;
import java.util.List;

/**
 * Typed application configuration. Defaults live in {@code application.yml}.
 */
@Validated
@ConfigurationProperties(prefix = "app")
public record AppProperties(Office office, Security security, Cors cors, Seed seed) {

    public record Office(
            @NotBlank String zone,
            LocalTime opensAt,
            LocalTime closesAt,
            @Min(5) @Max(60) int slotGridMinutes,
            @Min(5) @Max(480) int minDurationMinutes,
            @Min(10) @Max(500) int maxPageSize) {
    }

    public record Security(
            boolean enabled,
            @NotBlank String username,
            @NotBlank String password,
            @NotBlank String roles) {
    }

    public record Cors(@NotEmpty List<String> allowedOrigins) {
    }

    public record Seed(@NotBlank String roomsResource) {
    }
}
