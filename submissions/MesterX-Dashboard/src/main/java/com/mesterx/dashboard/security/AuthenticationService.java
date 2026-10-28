package com.mesterx.dashboard.security;

import com.mesterx.dashboard.domain.ApiKey;
import com.mesterx.dashboard.domain.Enums;
import com.mesterx.dashboard.domain.User;
import com.mesterx.dashboard.repository.ApiKeyRepository;
import com.mesterx.dashboard.repository.UserRepository;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;

/**
 * Resolves the authenticated user for the current request, either from the
 * session (web UI) or from the X-Api-Key header (plugin).
 */
@Component
public class AuthenticationService {

    private final UserRepository userRepository;
    private final ApiKeyRepository apiKeyRepository;

    public AuthenticationService(UserRepository userRepository, ApiKeyRepository apiKeyRepository) {
        this.userRepository = userRepository;
        this.apiKeyRepository = apiKeyRepository;
    }

    public Optional<CurrentUser> current() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof CurrentUser cu) {
            return Optional.of(cu);
        }
        if (auth != null && auth.getPrincipal() instanceof ApiKeyPrincipal pk) {
            return Optional.of(new CurrentUser(pk.userId(), pk.email(), pk.displayName(), pk.role()));
        }
        return Optional.empty();
    }

    public CurrentUser require() {
        return current().orElseThrow(() -> new org.springframework.security.access.AccessDeniedException("Not authenticated"));
    }

    public static void setSessionAuthentication(User user) {
        CurrentUser cu = new CurrentUser(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole());
        var auth = new UsernamePasswordAuthenticationToken(cu, null,
                List.of(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_" + user.getRole().name())));
        SecurityContextHolder.getContext().setAuthentication(auth);
    }

    public Optional<User> userForApiKey(String apiKey) {
        String hash = sha256(apiKey);
        return apiKeyRepository.findByKeyHash(hash)
                .filter(k -> k.getRevokedAt() == null)
                .flatMap(k -> userRepository.findById(k.getUserId()))
                .filter(u -> u.getStatus() == Enums.UserStatus.ACTIVE);
    }

    public static String sha256(String value) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}