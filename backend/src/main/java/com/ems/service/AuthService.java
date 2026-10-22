package com.ems.service;

import com.ems.dto.LoginRequest;
import com.ems.dto.LoginResponse;
import com.ems.dto.RegisterRequest;
import com.ems.entity.User;
import com.ems.repository.UserRepository;
import com.ems.security.JwtUtils;
import com.ems.security.UserDetailsImpl;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private static final Logger logger = LoggerFactory.getLogger(AuthService.class);
    private final AuthenticationManager authenticationManager;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtils jwtUtils;

    public LoginResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword()));

        SecurityContextHolder.getContext().setAuthentication(authentication);
        UserDetailsImpl userDetails = (UserDetailsImpl) authentication.getPrincipal();

        String token = jwtUtils.generateToken(userDetails.getUsername());
        logger.info("User logged in: {}", userDetails.getUsername());

        return LoginResponse.of(
                token,
                userDetails.getUsername(),
                userDetails.getFullName(),
                userDetails.getEmail(),
                userDetails.getAuthorities().iterator().next().getAuthority());
    }

    @Transactional
    public LoginResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("Username already taken: " + request.getUsername());
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already registered: " + request.getEmail());
        }

        User user = User.builder()
                .username(request.getUsername())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .fullName(request.getFullName())
                .email(request.getEmail())
                .role(User.Role.USER)
                .isActive(true)
                .build();

        userRepository.save(user);
        logger.info("New user registered: {}", user.getUsername());

        String token = jwtUtils.generateToken(user.getUsername());
        return LoginResponse.of(
                token,
                user.getUsername(),
                user.getFullName(),
                user.getEmail(),
                "ROLE_" + user.getRole().name());
    }
}