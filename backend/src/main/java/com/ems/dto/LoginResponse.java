package com.ems.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {

    private String token;
    private String tokenType;
    private String username;
    private String fullName;
    private String email;
    private String role;

    public static LoginResponse of(String token, String username, String fullName, String email, String role) {
        return LoginResponse.builder()
                .token(token)
                .tokenType("Bearer")
                .username(username)
                .fullName(fullName)
                .email(email)
                .role(role)
                .build();
    }
}