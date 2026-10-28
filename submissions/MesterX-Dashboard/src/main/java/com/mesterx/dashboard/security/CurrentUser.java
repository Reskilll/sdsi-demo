package com.mesterx.dashboard.security;

import com.mesterx.dashboard.domain.Enums;

import java.util.List;

/** Authenticated principal stored in the SecurityContext. */
public record CurrentUser(
        Long id,
        String email,
        String displayName,
        Enums.Role role) {
}