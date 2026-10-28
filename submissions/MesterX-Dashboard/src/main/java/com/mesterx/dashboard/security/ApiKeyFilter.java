package com.mesterx.dashboard.security;

import com.mesterx.dashboard.domain.Enums;
import com.mesterx.dashboard.domain.User;
import com.mesterx.dashboard.repository.UserRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Authenticates plugin requests using the X-Api-Key header. Applies only to
 * /api/v1/** (the UI uses session auth instead). Validation of model metrics
 * is done in the controller after authentication; this filter only establishes
 * identity.
 */
@Component
public class ApiKeyFilter extends OncePerRequestFilter {

    private final AuthenticationService authenticationService;

    public ApiKeyFilter(AuthenticationService authenticationService) {
        this.authenticationService = authenticationService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String header = request.getHeader("X-Api-Key");
        if (header != null && !header.isBlank()) {
            var user = authenticationService.userForApiKey(header.trim()).orElse(null);
            if (user != null) {
                ApiKeyPrincipal principal = new ApiKeyPrincipal(
                        user.getId(), user.getEmail(), user.getDisplayName(), user.getRole());
                var auth = new UsernamePasswordAuthenticationToken(principal, null,
                        List.of(new SimpleGrantedAuthority("ROLE_" + user.getRole().name())));
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }
        chain.doFilter(request, response);
    }
}