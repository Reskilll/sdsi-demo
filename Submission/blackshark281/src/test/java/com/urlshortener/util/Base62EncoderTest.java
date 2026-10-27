package com.urlshortener.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

class Base62EncoderTest {

    @Test
    void encodeZero() {
        assertEquals("000000", Base62Encoder.encode(0));
    }

    @Test
    void encodeSmallNumbers() {
        assertEquals("000001", Base62Encoder.encode(1));
        assertEquals("000002", Base62Encoder.encode(2));
        assertEquals("00000a", Base62Encoder.encode(10));
        assertEquals("00000Z", Base62Encoder.encode(61));
    }

    @Test
    void roundTrip() {
        for (long id : new long[]{0, 1, 10, 61, 62, 100, 1000, 99999, 123456789L}) {
            String code = Base62Encoder.encode(id);
            long decoded = Base62Encoder.decode(code);
            assertEquals(id, decoded, "Round-trip failed for id=" + id + " code=" + code);
        }
    }

    @Test
    void encodeMinLengthAlways() {
        // Even the smallest IDs produce 6-char codes
        for (long id = 0; id < 100; id++) {
            assertTrue(Base62Encoder.encode(id).length() >= 6,
                "Code for id " + id + " should have at least 6 chars");
        }
    }

    @Test
    void decodeRejectsInvalidCharacters() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.decode("abc!@#"));
    }

    @Test
    void decodeRejectsNullAndEmpty() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.decode(null));
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.decode(""));
    }

    @Test
    void encodeRejectsNegative() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.encode(-1));
    }

    @Test
    void largeIdRoundTrip() {
        long large = 9_876_543_210L;
        String code = Base62Encoder.encode(large);
        assertEquals(large, Base62Encoder.decode(code));
    }
}