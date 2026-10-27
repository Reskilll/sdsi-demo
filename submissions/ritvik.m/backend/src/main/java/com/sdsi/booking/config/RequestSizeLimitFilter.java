package com.sdsi.booking.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Rejects oversized JSON bodies before they are buffered/parsed. Complies with
 * the same problem+json contract as the rest of the API.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class RequestSizeLimitFilter extends OncePerRequestFilter {

    static final long MAX_API_BODY_BYTES = 128 * 1024;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        long length = request.getContentLengthLong();
        if (request.getRequestURI().startsWith("/api/") && length > MAX_API_BODY_BYTES) {
            response.setStatus(HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE);
            response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
            String requestId = MDC.get("requestId");
            String idProperty = requestId == null ? "" : ",\"requestId\":\"" + requestId + "\"";
            response.getWriter().write("""
                    {"type":"about:blank","title":"Payload Too Large","status":413,\
                    "detail":"Request body exceeds the 128 KB limit.","code":"PAYLOAD_TOO_LARGE"%s}"""
                    .formatted(idProperty));
            return;
        }
        filterChain.doFilter(request, response);
    }
}
