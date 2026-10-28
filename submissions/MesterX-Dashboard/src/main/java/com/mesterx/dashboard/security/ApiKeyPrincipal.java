package com.mesterx.dashboard.security;

import com.mesterx.dashboard.domain.Enums;

/** Principal attached when a request authenticates via X-Api-Key (plugin). */
public record ApiKeyPrincipal(Long userId, String email, String displayName, Enums.Role role) {
}