package com.sdsi.booking.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.time.ZoneId;

@Configuration
public class ClockConfig {

    /**
     * The office clock. All business rules ("today", "past") are evaluated in the
     * configured office zone. Tests can replace this bean with a fixed clock.
     */
    @Bean
    public Clock clock(AppProperties properties) {
        return Clock.system(ZoneId.of(properties.office().zone()));
    }

    @Bean
    public ZoneId officeZone(AppProperties properties) {
        return ZoneId.of(properties.office().zone());
    }
}
