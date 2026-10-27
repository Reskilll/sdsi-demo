package com.sdsi.inventory;

import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.model.Reservation;
import com.sdsi.inventory.model.ReservationStatus;
import com.sdsi.inventory.model.StockReport;
import com.sdsi.inventory.service.ErrorCode;
import com.sdsi.inventory.service.InventoryException;
import com.sdsi.inventory.service.InventoryService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InventoryServiceTest {

    private MutableClock clock;
    private InventoryService service;

    @BeforeEach
    void setUp() {
        clock = new MutableClock(Instant.parse("2026-10-27T10:00:00Z"));
        service = new InventoryService(List.of(
                new Product("PHONE", "Phone", 10, 2),
                new Product("TV", "TV", 1, 1),
                new Product("EMPTY", "Sold out", 0, 5)),
                clock, InventoryService.DEFAULT_TTL, Duration.ofHours(1));
    }

    private static void assertError(ErrorCode expected, Runnable action) {
        InventoryException e = assertThrows(InventoryException.class, action::run);
        assertEquals(expected, e.code(), e.getMessage());
    }

    private void assertCounts(String sku, int available, int reserved, int sold) {
        StockReport r = service.report(sku);
        assertEquals(available, r.available(), "available");
        assertEquals(reserved, r.reserved(), "reserved");
        assertEquals(sold, r.sold(), "sold");
        assertEquals(r.total(), r.available() + r.reserved() + r.sold(), "invariant");
    }

    @Nested
    class Reserve {

        @Test
        void holdsStockWithDefaultTtl() {
            Reservation r = service.reserve("alice", "PHONE", 2);

            assertEquals(ReservationStatus.ACTIVE, r.status());
            assertEquals(Duration.ofSeconds(120), Duration.between(r.createdAt(), r.expiresAt()));
            assertCounts("PHONE", 8, 2, 0);
        }

        @Test
        void customTtlIsRespected() {
            Reservation r = service.reserve("alice", "PHONE", 1, Duration.ofSeconds(5), null);
            assertEquals(clock.instant().plusSeconds(5), r.expiresAt());
        }

        @Test
        void rejectsWhenNotEnoughStock() {
            service.reserve("alice", "TV", 1);
            assertError(ErrorCode.INSUFFICIENT_STOCK, () -> service.reserve("bob", "TV", 1));
            assertError(ErrorCode.INSUFFICIENT_STOCK, () -> service.reserve("bob", "EMPTY", 1));
            assertCounts("TV", 0, 1, 0);
        }

        @Test
        void failedReserveLeavesNoTrace() {
            assertError(ErrorCode.PER_USER_LIMIT_EXCEEDED, () -> service.reserve("alice", "PHONE", 3));
            assertCounts("PHONE", 10, 0, 0);
            // The failed attempt did not consume any of the user's allowance.
            service.reserve("alice", "PHONE", 2);
        }

        @ParameterizedTest
        @ValueSource(ints = {0, -1, Integer.MIN_VALUE})
        void rejectsNonPositiveQuantity(int qty) {
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("alice", "PHONE", qty));
        }

        @Test
        void hugeQuantityDoesNotOverflow() {
            assertError(ErrorCode.PER_USER_LIMIT_EXCEEDED, () -> service.reserve("alice", "PHONE", Integer.MAX_VALUE));
            assertCounts("PHONE", 10, 0, 0);
        }

        @Test
        void rejectsUnknownOrBlankSku() {
            assertError(ErrorCode.SKU_NOT_FOUND, () -> service.reserve("alice", "NOPE", 1));
            assertError(ErrorCode.SKU_NOT_FOUND, () -> service.reserve("alice", "phone", 1)); // case-sensitive
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("alice", " ", 1));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("alice", null, 1));
        }

        @Test
        void rejectsMissingOrMalformedUser() {
            assertError(ErrorCode.UNAUTHORIZED, () -> service.reserve(null, "PHONE", 1));
            assertError(ErrorCode.UNAUTHORIZED, () -> service.reserve("", "PHONE", 1));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("a b", "PHONE", 1));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("x".repeat(65), "PHONE", 1));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("<script>", "PHONE", 1));
        }

        @Test
        void rejectsOutOfRangeTtl() {
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("a", "PHONE", 1, Duration.ZERO, null));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("a", "PHONE", 1, Duration.ofSeconds(-5), null));
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("a", "PHONE", 1, Duration.ofHours(2), null));
        }
    }

    @Nested
    class ConfirmAndCancel {

        @Test
        void confirmMovesReservedToSold() {
            Reservation r = service.reserve("alice", "PHONE", 2);
            Reservation c = service.confirm("alice", r.id());

            assertEquals(ReservationStatus.CONFIRMED, c.status());
            assertCounts("PHONE", 8, 0, 2);
        }

        @Test
        void confirmIsIdempotent() {
            Reservation r = service.reserve("alice", "PHONE", 1);
            service.confirm("alice", r.id());
            service.confirm("alice", r.id());
            assertCounts("PHONE", 9, 0, 1);
        }

        @Test
        void cancelReleasesStockAndIsIdempotent() {
            Reservation r = service.reserve("alice", "PHONE", 2);
            assertEquals(ReservationStatus.CANCELLED, service.cancel("alice", r.id()).status());
            service.cancel("alice", r.id());
            assertCounts("PHONE", 10, 0, 0);
        }

        @Test
        void cannotCancelConfirmed() {
            Reservation r = service.reserve("alice", "PHONE", 1);
            service.confirm("alice", r.id());
            assertError(ErrorCode.INVALID_STATE, () -> service.cancel("alice", r.id()));
            assertCounts("PHONE", 9, 0, 1);
        }

        @Test
        void cannotConfirmCancelled() {
            Reservation r = service.reserve("alice", "PHONE", 1);
            service.cancel("alice", r.id());
            assertError(ErrorCode.INVALID_STATE, () -> service.confirm("alice", r.id()));
            assertCounts("PHONE", 10, 0, 0);
        }

        @Test
        void otherUsersCannotTouchMyReservation() {
            Reservation r = service.reserve("alice", "PHONE", 1);
            assertError(ErrorCode.RESERVATION_NOT_FOUND, () -> service.confirm("mallory", r.id()));
            assertError(ErrorCode.RESERVATION_NOT_FOUND, () -> service.cancel("mallory", r.id()));
            assertError(ErrorCode.RESERVATION_NOT_FOUND, () -> service.get("mallory", r.id()));
            assertCounts("PHONE", 9, 1, 0);
        }

        @Test
        void unknownOrMalformedIds() {
            assertError(ErrorCode.RESERVATION_NOT_FOUND, () -> service.confirm("alice", UUID.randomUUID().toString()));
            assertError(ErrorCode.INVALID_INPUT, () -> service.confirm("alice", "../../etc"));
            assertError(ErrorCode.INVALID_INPUT, () -> service.cancel("alice", null));
        }
    }

    @Nested
    class Expiry {

        @Test
        void expiresExactlyAtTtlAndReleasesStock() {
            Reservation r = service.reserve("alice", "TV", 1);
            clock.advance(Duration.ofSeconds(119));
            assertEquals(ReservationStatus.ACTIVE, service.get("alice", r.id()).status());

            clock.advance(Duration.ofSeconds(1)); // now == expiresAt -> expired
            assertEquals(ReservationStatus.EXPIRED, service.get("alice", r.id()).status());
            assertCounts("TV", 1, 0, 0);
        }

        @Test
        void confirmAfterExpiryFailsAndStockGoesToNextBuyer() {
            Reservation r = service.reserve("alice", "TV", 1);
            clock.advance(Duration.ofSeconds(121));

            assertError(ErrorCode.RESERVATION_EXPIRED, () -> service.confirm("alice", r.id()));
            Reservation bob = service.reserve("bob", "TV", 1);
            service.confirm("bob", bob.id());
            assertCounts("TV", 0, 0, 1);
        }

        @Test
        void cancelAfterExpiryIsHarmless() {
            Reservation r = service.reserve("alice", "PHONE", 2);
            clock.advance(Duration.ofMinutes(5));
            assertEquals(ReservationStatus.EXPIRED, service.cancel("alice", r.id()).status());
            assertCounts("PHONE", 10, 0, 0);
        }

        @Test
        void expireAllSweepsWithoutAnyRequest() {
            service.reserve("alice", "PHONE", 1);
            service.reserve("bob", "PHONE", 1, Duration.ofSeconds(10), null);
            clock.advance(Duration.ofSeconds(10));
            assertEquals(1, service.expireAll());
            clock.advance(Duration.ofSeconds(110));
            assertEquals(1, service.expireAll());
            assertEquals(0, service.expireAll());
        }

        @Test
        void expiredHoldDoesNotCountTowardLimit() {
            service.reserve("alice", "PHONE", 2);
            clock.advance(Duration.ofSeconds(120));
            Reservation again = service.reserve("alice", "PHONE", 2);
            assertEquals(ReservationStatus.ACTIVE, again.status());
        }

        @Test
        void finishedReservationsArePurgedAfterRetention() {
            Reservation r = service.reserve("alice", "PHONE", 1);
            service.confirm("alice", r.id());
            clock.advance(Duration.ofHours(1).plusSeconds(1));
            service.expireAll();
            assertError(ErrorCode.RESERVATION_NOT_FOUND, () -> service.get("alice", r.id()));
            // ...but the purchase still counts towards the limit and the sold total.
            assertError(ErrorCode.PER_USER_LIMIT_EXCEEDED, () -> service.reserve("alice", "PHONE", 2));
            assertCounts("PHONE", 9, 0, 1);
        }
    }

    @Nested
    class PerUserLimit {

        @Test
        void activeHoldsAndPurchasesBothCount() {
            Reservation first = service.reserve("alice", "PHONE", 1);
            service.confirm("alice", first.id());
            service.reserve("alice", "PHONE", 1);
            assertError(ErrorCode.PER_USER_LIMIT_EXCEEDED, () -> service.reserve("alice", "PHONE", 1));
        }

        @Test
        void cancellingFreesAllowance() {
            Reservation r = service.reserve("alice", "PHONE", 2);
            service.cancel("alice", r.id());
            service.reserve("alice", "PHONE", 2);
        }

        @Test
        void limitIsPerSkuAndPerUser() {
            service.reserve("alice", "PHONE", 2);
            service.reserve("alice", "TV", 1);  // different SKU
            service.reserve("bob", "PHONE", 2); // different user
            assertCounts("PHONE", 6, 4, 0);
        }
    }

    @Nested
    class Idempotency {

        @Test
        void sameKeyReturnsSameReservation() {
            Reservation a = service.reserve("alice", "PHONE", 1, null, "order-42");
            Reservation b = service.reserve("alice", "PHONE", 1, null, "order-42");
            assertEquals(a.id(), b.id());
            assertCounts("PHONE", 9, 1, 0);
        }

        @Test
        void keyIsScopedPerUser() {
            Reservation a = service.reserve("alice", "PHONE", 1, null, "k1");
            Reservation b = service.reserve("bob", "PHONE", 1, null, "k1");
            assertTrue(!a.id().equals(b.id()));
        }

        @Test
        void reusingKeyWithDifferentRequestIsRejected() {
            service.reserve("alice", "PHONE", 1, null, "k1");
            assertError(ErrorCode.IDEMPOTENCY_CONFLICT, () -> service.reserve("alice", "PHONE", 2, null, "k1"));
            assertError(ErrorCode.IDEMPOTENCY_CONFLICT, () -> service.reserve("alice", "TV", 1, null, "k1"));
        }

        @Test
        void failedAttemptDoesNotBurnKey() {
            assertError(ErrorCode.INSUFFICIENT_STOCK, () -> service.reserve("alice", "EMPTY", 1, null, "k1"));
            service.reserve("alice", "PHONE", 1, null, "k1");
        }

        @Test
        void rejectsMalformedKey() {
            assertError(ErrorCode.INVALID_INPUT, () -> service.reserve("alice", "PHONE", 1, null, "bad key!"));
        }
    }

    @Test
    void reportListsEverySkuSorted() {
        List<StockReport> report = service.report();
        assertEquals(List.of("EMPTY", "PHONE", "TV"), report.stream().map(StockReport::sku).toList());
    }

    @Test
    void constructorRejectsDuplicateSkus() {
        assertThrows(IllegalArgumentException.class, () -> new InventoryService(List.of(
                new Product("A", "a", 1, 1), new Product("A", "b", 1, 1))));
    }
}
