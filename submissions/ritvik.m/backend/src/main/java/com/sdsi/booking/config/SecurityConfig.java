package com.sdsi.booking.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.io.IOException;
import java.net.URI;
import java.util.Arrays;
import java.util.List;

@Configuration
public class SecurityConfig {

    private static final Logger log = LoggerFactory.getLogger(SecurityConfig.class);

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public InMemoryUserDetailsManager userDetailsService(AppProperties properties, PasswordEncoder encoder) {
        AppProperties.Security security = properties.security();
        String[] roles = Arrays.stream(security.roles().split(","))
                .map(String::trim)
                .filter(role -> !role.isEmpty())
                .toArray(String[]::new);
        UserDetails user = User.withUsername(security.username())
                .password(encoder.encode(security.password()))
                .roles(roles)
                .build();
        return new InMemoryUserDetailsManager(user);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                   AppProperties properties,
                                                   ObjectMapper objectMapper) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(Customizer.withDefaults())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .httpBasic(Customizer.withDefaults())
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .headers(headers -> headers
                        .contentTypeOptions(Customizer.withDefaults())
                        .frameOptions(frame -> frame.deny())
                        .referrerPolicy(referrer -> referrer.policy(
                                org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy.NO_REFERRER)))
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, authException) ->
                                writeProblem(response, objectMapper, HttpStatus.UNAUTHORIZED,
                                        "Authentication required",
                                        "Provide a valid HTTP Basic credential.", "UNAUTHORIZED"))
                        .accessDeniedHandler((request, response, accessDeniedException) ->
                                writeProblem(response, objectMapper, HttpStatus.FORBIDDEN,
                                        "Access denied", "You are not allowed to perform this action.", "FORBIDDEN")));

        if (properties.security().enabled()) {
            http.authorizeHttpRequests(auth -> auth
                    .requestMatchers("/", "/index.html", "/assets/**", "/favicon.ico").permitAll()
                    .requestMatchers("/actuator/health/**", "/actuator/info").permitAll()
                    .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                    .requestMatchers("/api/**").authenticated()
                    .anyRequest().permitAll());
            if ("admin123".equals(properties.security().password())) {
                log.warn("Using the default demo password. Set APP_ADMIN_PASSWORD before exposing this service.");
            }
        } else {
            log.warn("API authentication is DISABLED (app.security.enabled=false). Do not use this in production.");
            http.authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        }
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource(AppProperties properties) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(properties.cors().allowedOrigins());
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type", "X-Request-Id"));
        config.setExposedHeaders(List.of("X-Request-Id", "Location", "Content-Disposition"));
        config.setMaxAge(3600L);
        config.setAllowCredentials(false);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }

    private static void writeProblem(HttpServletResponse response, ObjectMapper mapper,
                                     HttpStatus status, String title, String detail, String code)
            throws IOException {
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
        if (status == HttpStatus.UNAUTHORIZED) {
            response.setHeader(org.springframework.http.HttpHeaders.WWW_AUTHENTICATE,
                    "Basic realm=\"room-booking\", charset=\"UTF-8\"");
        }
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setTitle(title);
        problem.setType(URI.create("about:blank"));
        problem.setProperty("code", code);
        mapper.writeValue(response.getOutputStream(), problem);
    }
}
