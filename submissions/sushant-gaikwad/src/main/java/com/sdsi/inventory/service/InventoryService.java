package com.sdsi.inventory.service;

import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.model.Reservation;
import com.sdsi.inventory.model.ReservationStatus;
import com.sdsi.inventory.model.StockReport;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.PriorityQueue;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;
import java.util.regex.Pattern;

/**
 * Thread-safe flash-sale inventory with time-limited reservations.
 *
 * <p>Concurrency model: every SKU owns one {@link ReentrantLock}. All stock counters, per-user usage
 * and reservation state transitions for that SKU happen under that lock, so check-then-act
 * ("is there stock? is the user under the limit?") is atomic and overselling is impossible.
 * Different SKUs never contend with each other.
 *
 * <p>Expiry is enforced twice: lazily (every operation on a SKU first expires its overdue holds,
 * so correctness never depends on a timer) and eagerly by an optional background sweeper that
 * returns stock to the pool even when nobody touches the SKU.
 */
public final class InventoryService implements AutoCloseable {

    public static final Duration DEFAULT_TTL = Duration.ofSeconds(120);
    public static final Duration MIN_TTL = Duration.ofSeconds(1);
    public static final Duration MAX_TTL = Duration.ofHours(1);
    /** How long finished reservations stay queryable before being purged from memory. */
    public static final Duration DEFAULT_RETENTION = Duration.ofHours(1);

    private static final System.Logger LOG = System.getLogger(InventoryService.class.getName());
    private static final Pattern USER_ID = Pattern.compile("[A-Za-z0-9_.@-]{1,64}");
    private static final Pattern IDEMPOTENCY_KEY = Pattern.compile("[A-Za-z0-9_.:-]{1,128}");
    private static final Pattern RESERVATION_ID = Pattern.compile("[0-9a-fA-F-]{36}");

    private final Clock clock;
    private final Duration defaultTtl;
    private final Duration retention;
    private final Map<String, SkuState> skus;
    private final ConcurrentHashMap<String, Hold> reservations = new ConcurrentHashMap<>();
    /** (userId + '\u0000' + key) -> reservation id. Lets clients safely retry a reserve call. */
    private final ConcurrentHashMap<String, String> idempotencyKeys = new ConcurrentHashMap<>();
    private volatile ScheduledExecutorService sweeper;

    public InventoryService(Collection<Product> products) {
        this(products, Clock.systemUTC(), DEFAULT_TTL, DEFAULT_RETENTION);
    }

    public InventoryService(Collection<Product> products, Clock clock, Duration defaultTtl, Duration retention) {
        Objects.requireNonNull(products, "products");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.defaultTtl = validateTtl(Objects.requireNonNull(defaultTtl, "defaultTtl"));
        this.retention = Objects.requireNonNull(retention, "retention");
        if (retention.isNegative()) {
            throw new IllegalArgumentException("retention must not be negative");
        }
        Map<String, SkuState> map = new LinkedHashMap<>();
        for (Product p : products) {
            if (map.putIfAbsent(p.sku(), new SkuState(p)) != null) {
                throw new IllegalArgumentException("duplicate SKU: " + p.sku());
            }
        }
        this.skus = Map.copyOf(map);
    }

    // ------------------------------------------------------------------ M2: reserve

    public Reservation reserve(String userId, String sku, int quantity) {
        return reserve(userId, sku, quantity, null, null);
    }

    /**
     * Places a hold of {@code quantity} units for {@code userId}.
     *
     * @param ttl            hold duration; {@code null} means the service default (120 s)
     * @param idempotencyKey optional client key; repeating a call with the same key returns the
     *                       original reservation instead of holding more stock
     */
    public Reservation reserve(String userId, String sku, int quantity, Duration ttl, String idempotencyKey) {
        validateUser(userId);
        SkuState state = requireSku(sku);
        if (quantity <= 0) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "quantity must be a positive integer");
        }
        Duration effectiveTtl = ttl == null ? defaultTtl : validateTtl(ttl);

        if (idempotencyKey == null) {
            return createHold(state, userId, quantity, effectiveTtl, null).snapshot();
        }
        if (!IDEMPOTENCY_KEY.matcher(idempotencyKey).matches()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT,
                    "idempotency key must be 1-128 chars of [A-Za-z0-9_.:-]");
        }
        String scopedKey = userId + '\u0000' + idempotencyKey;
        // computeIfAbsent is atomic per key: concurrent retries with the same key create one hold.
        String id = idempotencyKeys.computeIfAbsent(scopedKey,
                k -> createHold(state, userId, quantity, effectiveTtl, k).id);
        Hold existing = reservations.get(id);
        if (existing == null) {
            // Purged after retention; treat the key as consumed rather than silently re-reserving.
            throw new InventoryException(ErrorCode.IDEMPOTENCY_CONFLICT, "idempotency key already used");
        }
        if (!existing.sku.equals(sku) || existing.quantity != quantity) {
            throw new InventoryException(ErrorCode.IDEMPOTENCY_CONFLICT,
                    "idempotency key was already used with a different SKU or quantity");
        }
        return get(userId, id);
    }

    private Hold createHold(SkuState state, String userId, int quantity, Duration ttl, String scopedKey) {
        Product p = state.product;
        state.lock.lock();
        try {
            Instant now = clock.instant();
            expireDue(state, now);

            UserUsage usage = state.usage.get(userId);
            int alreadyCommitted = usage == null ? 0 : usage.held + usage.purchased;
            if ((long) alreadyCommitted + quantity > p.perUserLimit()) {
                throw new InventoryException(ErrorCode.PER_USER_LIMIT_EXCEEDED, String.format(
                        "limit for %s is %d per user; you already hold or bought %d",
                        p.sku(), p.perUserLimit(), alreadyCommitted));
            }
            if (quantity > state.available) {
                throw new InventoryException(ErrorCode.INSUFFICIENT_STOCK, String.format(
                        "only %d unit(s) of %s available", state.available, p.sku()));
            }

            Hold hold = new Hold(UUID.randomUUID().toString(), p.sku(), userId, quantity,
                    now, now.plus(ttl), scopedKey);
            state.available -= quantity;
            state.reserved += quantity;
            state.usage.computeIfAbsent(userId, u -> new UserUsage()).held += quantity;
            state.expiryQueue.add(hold);
            reservations.put(hold.id, hold);
            LOG.log(System.Logger.Level.INFO, "RESERVED id={0} sku={1} user={2} qty={3} expiresAt={4}",
                    hold.id, p.sku(), userId, quantity, hold.expiresAt);
            return hold;
        } finally {
            state.lock.unlock();
        }
    }

    // ------------------------------------------------------------------ M3: confirm / cancel

    /** Permanently deducts the held stock. Idempotent: confirming twice returns the same result. */
    public Reservation confirm(String userId, String reservationId) {
        Hold hold = requireOwnedHold(userId, reservationId);
        SkuState state = skus.get(hold.sku);
        state.lock.lock();
        try {
            Instant now = clock.instant();
            expireDue(state, now);
            switch (hold.status) {
                case ACTIVE -> {
                    state.reserved -= hold.quantity;
                    state.sold += hold.quantity;
                    UserUsage usage = state.usage.get(hold.userId);
                    usage.held -= hold.quantity;
                    usage.purchased += hold.quantity;
                    finish(state, hold, ReservationStatus.CONFIRMED, now);
                }
                case CONFIRMED -> { /* idempotent replay */ }
                case EXPIRED -> throw new InventoryException(ErrorCode.RESERVATION_EXPIRED,
                        "reservation expired at " + hold.expiresAt + "; stock was released");
                case CANCELLED -> throw new InventoryException(ErrorCode.INVALID_STATE,
                        "reservation was cancelled and cannot be confirmed");
            }
            return hold.snapshot();
        } finally {
            state.lock.unlock();
        }
    }

    /**
     * Releases the held stock. Idempotent for already cancelled or expired holds (stock is already
     * back in the pool); rejects confirmed ones because a completed sale is not refundable here.
     */
    public Reservation cancel(String userId, String reservationId) {
        Hold hold = requireOwnedHold(userId, reservationId);
        SkuState state = skus.get(hold.sku);
        state.lock.lock();
        try {
            Instant now = clock.instant();
            expireDue(state, now);
            switch (hold.status) {
                case ACTIVE -> {
                    release(state, hold);
                    finish(state, hold, ReservationStatus.CANCELLED, now);
                }
                case CANCELLED, EXPIRED -> { /* already released */ }
                case CONFIRMED -> throw new InventoryException(ErrorCode.INVALID_STATE,
                        "reservation is already confirmed and cannot be cancelled");
            }
            return hold.snapshot();
        } finally {
            state.lock.unlock();
        }
    }

    public Reservation get(String userId, String reservationId) {
        Hold hold = requireOwnedHold(userId, reservationId);
        SkuState state = skus.get(hold.sku);
        state.lock.lock();
        try {
            expireDue(state, clock.instant());
            return hold.snapshot();
        } finally {
            state.lock.unlock();
        }
    }

    // ------------------------------------------------------------------ M5: reporting

    /** Counts for every SKU, sorted by SKU. Each row is internally consistent. */
    public List<StockReport> report() {
        List<StockReport> out = new ArrayList<>(skus.size());
        for (SkuState state : orderedStates()) {
            out.add(report(state));
        }
        return out;
    }

    public StockReport report(String sku) {
        return report(requireSku(sku));
    }

    private StockReport report(SkuState state) {
        state.lock.lock();
        try {
            expireDue(state, clock.instant());
            Product p = state.product;
            return new StockReport(p.sku(), p.name(), p.stock(), state.available, state.reserved, state.sold,
                    p.perUserLimit());
        } finally {
            state.lock.unlock();
        }
    }

    // ------------------------------------------------------------------ expiry

    /** Expires every overdue hold across all SKUs and purges old finished reservations. */
    public int expireAll() {
        int expired = 0;
        for (SkuState state : skus.values()) {
            List<Hold> purged;
            state.lock.lock();
            try {
                Instant now = clock.instant();
                expired += expireDue(state, now);
                purged = drainPurgeable(state, now);
            } finally {
                state.lock.unlock();
            }
            // Removed outside the SKU lock: reserve() can hold an idempotency-map bin lock while
            // waiting for the SKU lock, so taking them in the opposite order here could deadlock.
            for (Hold h : purged) {
                reservations.remove(h.id);
                if (h.scopedIdempotencyKey != null) {
                    idempotencyKeys.remove(h.scopedIdempotencyKey, h.id);
                }
            }
        }
        return expired;
    }

    /** Starts a daemon thread that calls {@link #expireAll()} on a fixed interval. */
    public synchronized void startExpirySweeper(Duration interval) {
        if (sweeper != null) {
            return;
        }
        long millis = Math.max(50, interval.toMillis());
        sweeper = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "reservation-expiry-sweeper");
            t.setDaemon(true);
            return t;
        });
        sweeper.scheduleWithFixedDelay(() -> {
            try {
                expireAll();
            } catch (RuntimeException e) {
                LOG.log(System.Logger.Level.ERROR, "expiry sweep failed", e);
            }
        }, millis, millis, TimeUnit.MILLISECONDS);
    }

    @Override
    public synchronized void close() {
        if (sweeper != null) {
            sweeper.shutdownNow();
            sweeper = null;
        }
    }

    /** Must be called with the SKU lock held. O(k log n) for k expired holds. */
    private int expireDue(SkuState state, Instant now) {
        int count = 0;
        Hold head;
        while ((head = state.expiryQueue.peek()) != null && !now.isBefore(head.expiresAt)) {
            state.expiryQueue.poll();
            if (head.status == ReservationStatus.ACTIVE) {
                release(state, head);
                finish(state, head, ReservationStatus.EXPIRED, now);
                count++;
            }
        }
        return count;
    }

    private void release(SkuState state, Hold hold) {
        state.reserved -= hold.quantity;
        state.available += hold.quantity;
        UserUsage usage = state.usage.get(hold.userId);
        usage.held -= hold.quantity;
        if (usage.held == 0 && usage.purchased == 0) {
            state.usage.remove(hold.userId);
        }
    }

    private void finish(SkuState state, Hold hold, ReservationStatus status, Instant now) {
        hold.status = status;
        hold.updatedAt = now;
        // Left in expiryQueue on purpose (lazy deletion): PriorityQueue.remove is O(n), and
        // expireDue skips non-ACTIVE entries. They drop out by their expiry time at the latest.
        state.finished.addLast(hold);
        LOG.log(System.Logger.Level.INFO, "{0} id={1} sku={2} user={3} qty={4}",
                status, hold.id, hold.sku, hold.userId, hold.quantity);
    }

    private List<Hold> drainPurgeable(SkuState state, Instant now) {
        List<Hold> out = new ArrayList<>();
        Instant cutoff = now.minus(retention);
        Hold head;
        while ((head = state.finished.peekFirst()) != null && head.updatedAt.isBefore(cutoff)) {
            out.add(state.finished.pollFirst());
        }
        return out;
    }

    // ------------------------------------------------------------------ validation helpers

    private Hold requireOwnedHold(String userId, String reservationId) {
        validateUser(userId);
        if (reservationId == null || !RESERVATION_ID.matcher(reservationId).matches()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "reservation id must be a UUID");
        }
        Hold hold = reservations.get(reservationId);
        // Someone else's reservation is reported as "not found" so ids cannot be probed.
        if (hold == null || !hold.userId.equals(userId)) {
            throw new InventoryException(ErrorCode.RESERVATION_NOT_FOUND, "reservation not found");
        }
        return hold;
    }

    private SkuState requireSku(String sku) {
        if (sku == null || sku.isBlank()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "sku is required");
        }
        SkuState state = skus.get(sku);
        if (state == null) {
            throw new InventoryException(ErrorCode.SKU_NOT_FOUND, "unknown sku");
        }
        return state;
    }

    private static void validateUser(String userId) {
        if (userId == null || userId.isEmpty()) {
            throw new InventoryException(ErrorCode.UNAUTHORIZED, "user id is required");
        }
        if (!USER_ID.matcher(userId).matches()) {
            throw new InventoryException(ErrorCode.INVALID_INPUT, "user id must be 1-64 chars of [A-Za-z0-9_.@-]");
        }
    }

    private static Duration validateTtl(Duration ttl) {
        if (ttl.compareTo(MIN_TTL) < 0 || ttl.compareTo(MAX_TTL) > 0) {
            throw new InventoryException(ErrorCode.INVALID_INPUT,
                    "ttl must be between " + MIN_TTL.toSeconds() + " and " + MAX_TTL.toSeconds() + " seconds");
        }
        return ttl;
    }

    private List<SkuState> orderedStates() {
        List<SkuState> list = new ArrayList<>(skus.values());
        list.sort(Comparator.comparing(s -> s.product.sku()));
        return list;
    }

    // ------------------------------------------------------------------ internal state

    private static final class SkuState {
        final Product product;
        final ReentrantLock lock = new ReentrantLock();
        final PriorityQueue<Hold> expiryQueue = new PriorityQueue<>(Comparator.comparing(h -> h.expiresAt));
        final ArrayDeque<Hold> finished = new ArrayDeque<>();
        final Map<String, UserUsage> usage = new HashMap<>();
        int available;
        int reserved;
        int sold;

        SkuState(Product product) {
            this.product = product;
            this.available = product.stock();
        }
    }

    private static final class UserUsage {
        int held;
        int purchased;
    }

    /** Mutable reservation; {@code status} and {@code updatedAt} change only under the SKU lock. */
    private static final class Hold {
        final String id;
        final String sku;
        final String userId;
        final int quantity;
        final Instant createdAt;
        final Instant expiresAt;
        final String scopedIdempotencyKey;
        ReservationStatus status = ReservationStatus.ACTIVE;
        Instant updatedAt;

        Hold(String id, String sku, String userId, int quantity, Instant createdAt, Instant expiresAt,
             String scopedIdempotencyKey) {
            this.id = id;
            this.sku = sku;
            this.userId = userId;
            this.quantity = quantity;
            this.createdAt = createdAt;
            this.expiresAt = expiresAt;
            this.scopedIdempotencyKey = scopedIdempotencyKey;
            this.updatedAt = createdAt;
        }

        Reservation snapshot() {
            return new Reservation(id, sku, userId, quantity, createdAt, expiresAt, status, updatedAt);
        }
    }
}
