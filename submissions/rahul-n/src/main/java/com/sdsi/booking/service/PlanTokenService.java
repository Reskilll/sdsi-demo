package com.sdsi.booking.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.booking.web.error.ApiException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;

/**
 * Stateless, tamper-evident carrier for a recurrence dry-run result.
 *
 * <p>The plan is serialised and HMAC-signed rather than stored server-side: the client
 * holds the state, and the server can still trust the roster of vetted slots when the
 * confirmation POST arrives. Tokens expire so a stale plan cannot be committed blindly.
 */
@Service
public class PlanTokenService {

    private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder DECODER = Base64.getUrlDecoder();
    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private final ObjectMapper mapper;
    private final byte[] secret;
    private final Duration ttl;

    public PlanTokenService(ObjectMapper mapper,
                            @Value("${booking.plan-token.secret:}") String configuredSecret,
                            @Value("${booking.plan-token.ttl:PT15M}") Duration ttl) {
        this.mapper = mapper;
        this.ttl = ttl;
        this.secret = configuredSecret == null || configuredSecret.isBlank()
                ? randomSecret()
                : configuredSecret.getBytes(StandardCharsets.UTF_8);
    }

    /** Immutable state a plan token vouches for: the vetted slots and the window length they share. */
    public record PlanPayload(
            Long roomId,
            String organiser,
            List<String> attendees,
            List<OffsetDateTime> slots,
            int durationMinutes,
            OffsetDateTime expiresAt
    ) {
    }

    public String issue(PlanPayload payload) {
        try {
            String body = ENCODER.encodeToString(mapper.writeValueAsBytes(payload));
            return body + "." + ENCODER.encodeToString(sign(body));
        } catch (Exception e) {
            throw new IllegalStateException("unable to issue plan token", e);
        }
    }

    public PlanPayload verify(String token) {
        if (token == null || token.isBlank() || !token.contains(".")) {
            throw new ApiException.BadRequest("planToken is malformed");
        }
        int split = token.lastIndexOf('.');
        String body = token.substring(0, split);
        byte[] presented = decodeSignature(token.substring(split + 1));
        if (!MessageDigest.isEqual(sign(body), presented)) {
            throw new ApiException.BadRequest("planToken signature is invalid");
        }
        PlanPayload payload;
        try {
            payload = mapper.readValue(DECODER.decode(body), PlanPayload.class);
        } catch (Exception e) {
            throw new ApiException.BadRequest("planToken payload is unreadable");
        }
        if (payload.expiresAt() == null || payload.expiresAt().isBefore(OffsetDateTime.now(ZoneOffset.UTC))) {
            throw new ApiException.Conflict("planToken has expired; re-run the dry-run to refresh the plan");
        }
        return payload;
    }

    public OffsetDateTime expiryFromNow() {
        return OffsetDateTime.now(ZoneOffset.UTC).plus(ttl);
    }

    private byte[] sign(String body) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(secret, HMAC_ALGORITHM));
            return mac.doFinal(body.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException("unable to sign plan token", e);
        }
    }

    private byte[] decodeSignature(String encoded) {
        try {
            return DECODER.decode(encoded);
        } catch (IllegalArgumentException e) {
            throw new ApiException.BadRequest("planToken signature is malformed");
        }
    }

    private static byte[] randomSecret() {
        byte[] bytes = new byte[32];
        new SecureRandom().nextBytes(bytes);
        return HexFormat.of().formatHex(bytes).getBytes(StandardCharsets.UTF_8);
    }
}
