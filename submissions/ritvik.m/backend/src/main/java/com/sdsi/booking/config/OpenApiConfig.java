package com.sdsi.booking.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI bookingOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("Meeting Room Booking API")
                        .version("1.0.0")
                        .description("""
                                Room booking engine: CRUD, overlap and capacity guards, \
                                earliest free slot search and weekly recurring series.
                                Times are office-local wall-clock times (ISO-8601, no offset)."""))
                .components(new Components().addSecuritySchemes("basicAuth",
                        new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("basic")))
                .addSecurityItem(new SecurityRequirement().addList("basicAuth"));
    }
}
