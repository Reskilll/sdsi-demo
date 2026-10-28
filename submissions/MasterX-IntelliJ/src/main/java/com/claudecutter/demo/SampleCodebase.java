package com.claudecutter.demo;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A realistic sample codebase (a small e-commerce backend) used to demo the
 * token-saver. Deliberately verbose so the "without plugin" baseline (full
 * context) is large enough for the savings to be visible, matching what a real
 * codebase looks like.
 */
public final class SampleCodebase {

    private SampleCodebase() {}

    public static Map<String, String> build() {
        Map<String, String> index = new LinkedHashMap<>();

        index.put("com/acme/orders/OrderService.java", service("OrderService",
                """
                private final OrderRepository repository;
                private final PaymentGateway payments;
                private final NotificationService notifications;
                private final InventoryService inventory;
                private final PricingService pricing;
                private final OrderAuditLog audit;

                public OrderService(OrderRepository repository, PaymentGateway payments,
                                    NotificationService notifications, InventoryService inventory,
                                    PricingService pricing, OrderAuditLog audit) {
                    this.repository = repository;
                    this.payments = payments;
                    this.notifications = notifications;
                    this.inventory = inventory;
                    this.pricing = pricing;
                    this.audit = audit;
                }

                public Order createOrder(Customer customer, List<LineItem> items, String promoCode) {
                    Objects.requireNonNull(customer, "customer");
                    Objects.requireNonNull(items, "items");
                    if (items.isEmpty()) {
                        throw new IllegalArgumentException("order must have at least one item");
                    }
                    BigDecimal subtotal = items.stream().map(LineItem::total)
                            .reduce(BigDecimal.ZERO, BigDecimal::add);
                    BigDecimal discount = pricing.discountFor(promoCode, subtotal);
                    BigDecimal tax = pricing.taxFor(subtotal);
                    BigDecimal total = subtotal.subtract(discount).add(tax);
                    Order order = new Order(UUID.randomUUID().toString(), customer, items,
                            subtotal, discount, tax, total, OrderStatus.DRAFT, Instant.now());
                    if (!inventory.reserve(order)) {
                        throw new IllegalStateException("insufficient stock");
                    }
                    repository.save(order);
                    audit.record(order.id(), "created");
                    log.info(() -> "created order " + order.id() + " total=" + total);
                    return order;
                }

                public PaymentResult checkout(String orderId) {
                    Order order = repository.findById(orderId)
                            .orElseThrow(() -> new OrderNotFoundException(orderId));
                    assertDraft(order);
                    PaymentResult result = payments.charge(order.total(), order.customer());
                    if (result.succeeded()) {
                        order = repository.save(order.withStatus(OrderStatus.PAID));
                        notifications.sendConfirmation(order);
                        audit.record(orderId, "paid");
                    } else {
                        log.warning("payment failed for order " + orderId + ": " + result.error());
                        audit.record(orderId, "payment_failed");
                    }
                    return result;
                }

                public void cancel(String orderId) {
                    Order order = repository.findById(orderId)
                            .orElseThrow(() -> new OrderNotFoundException(orderId));
                    if (order.status() == OrderStatus.SHIPPED) {
                        throw new IllegalStateException("cannot cancel a shipped order");
                    }
                    repository.save(order.withStatus(OrderStatus.CANCELLED));
                    audit.record(orderId, "cancelled");
                }

                public List<Order> history(String customerId) {
                    return repository.findAll().stream()
                            .filter(o -> o.customer().id().equals(customerId))
                            .sorted(Comparator.comparing(Order::createdAt).reversed())
                            .toList();
                }

                private void assertDraft(Order order) {
                    if (order.status() != OrderStatus.DRAFT) {
                        throw new IllegalStateException("order " + order.id() + " is not draft");
                    }
                }

                public static final class OrderNotFoundException extends RuntimeException {
                    public OrderNotFoundException(String id) { super("no order with id " + id); }
                }
                """));

        index.put("com/acme/orders/repo/OrderRepository.java", repo("OrderRepository",
                "Order", "String id; ConcurrentHashMap store; save/ findById/ findAll/ delete"));

        index.put("com/acme/orders/model/Order.java", model("Order",
                "String id; Customer customer; List<LineItem> items; BigDecimal subtotal; "
                + "BigDecimal discount; BigDecimal tax; BigDecimal total; OrderStatus status; Instant createdAt"));

        index.put("com/acme/orders/model/Customer.java", model("Customer",
                "String id; String name; String email; String tier"));

        index.put("com/acme/orders/model/LineItem.java", model("LineItem",
                "String sku; int quantity; BigDecimal unitPrice"));

        index.put("com/acme/orders/notify/NotificationService.java", service("NotificationService",
                """
                private static final Logger log = Logger.getLogger(NotificationService.class.getName());
                public void sendConfirmation(Order order) { log.info("confirming " + order.id()); }
                public void sendShippingUpdate(Order order) { log.info("shipping " + order.id()); }
                public void sendRefundNotice(Order order) { log.info("refunding " + order.id()); }
                """));

        index.put("com/acme/orders/service/InventoryService.java", service("InventoryService",
                "Map<String,Integer> stock; boolean reserve(Order); void restock(String,int); int available(String)"));

        index.put("com/acme/orders/service/PricingService.java", service("PricingService",
                "BigDecimal TAX_RATE; taxFor(Order); discountFor(String,BigDecimal); BigDecimal totalFor(Order)"));

        index.put("com/acme/orders/repo/OrderAuditLog.java", service("OrderAuditLog",
                "List<Entry> entries; record(Entry); forOrder(String); List<Entry> all()"));

        index.put("com/acme/payments/PaymentGateway.java", interface_("PaymentGateway",
                "PaymentResult charge(BigDecimal amount, Object customer); "
                + "PaymentResult refund(String transactionId, BigDecimal amount)"));

        index.put("com/acme/auth/AuthController.java", service("AuthController",
                """
                private static final Pattern EMAIL = Pattern.compile("^[\\\\w.+-]+@[\\\\w-]+\\\\.[\\\\w.-]+$");
                private final UserService users;
                private final TokenService tokens;
                public AuthToken login(Credentials creds) {
                    Objects.requireNonNull(creds);
                    if (!EMAIL.matcher(creds.email()).matches()) throw new IllegalArgumentException("invalid email");
                    var user = users.findByEmail(creds.email()).orElseThrow(() -> new AuthException("no such user"));
                    if (!users.verifyPassword(user, creds.password())) throw new AuthException("bad password");
                    return tokens.issue(user.id(), 3600);
                }
                public AuthToken signup(Credentials creds) {
                    if (creds.password().length() < 8) throw new IllegalArgumentException("password too short");
                    var user = users.create(creds.email(), creds.password());
                    return tokens.issue(user.id(), 3600);
                }
                public static final class AuthException extends RuntimeException {
                    public AuthException(String msg) { super(msg); }
                }
                """));

        index.put("com/acme/auth/service/UserService.java", service("UserService",
                "Map<String,User> byEmail; SecureRandom random; findByEmail/ create/ verifyPassword; static hash"));

        index.put("com/acme/auth/service/TokenService.java", service("TokenService",
                "String secret; AuthToken issue(String userId, long ttlSeconds); boolean verify(String token); "
                + "Optional<String> subject(String token)"));

        index.put("com/acme/auth/model/User.java", model("User", "String id; String email; String passwordHash; String salt"));
        index.put("com/acme/auth/model/Credentials.java", model("Credentials", "String email; String password"));
        index.put("com/acme/auth/model/AuthToken.java", model("AuthToken", "String token; Instant expiresAt; String userId"));

        index.put("com/acme/catalog/ProductController.java", service("ProductController",
                "ProductService products; List<Product> search(String q); Product get(String sku); "
                + "Product create(Product p); void update(String sku, Product p)"));

        index.put("com/acme/catalog/ProductService.java", service("ProductService",
                "ProductRepository repo; List<Product> search(String q); Product get(String sku); "
                + "Product create(Product p); void update(String sku, Product p); void delete(String sku)"));

        index.put("com/acme/catalog/ProductRepository.java", repo("ProductRepository", "Product", "String sku; map store"));

        index.put("com/acme/catalog/Product.java", model("Product", "String sku; String name; String description; BigDecimal price; int stock"));

        index.put("com/acme/cart/CartService.java", service("CartService",
                "Map<String,Cart> carts; Cart get(String userId); Cart addItem(String userId, LineItem item); "
                + "Cart removeItem(String userId, String sku); void clear(String userId); BigDecimal subtotal(String userId)"));

        index.put("com/acme/cart/Cart.java", model("Cart", "String userId; List<LineItem> items; Instant updatedAt"));

        index.put("com/acme/shipping/ShippingService.java", service("ShippingService",
                "Shipment ship(Order order); BigDecimal quote(Order order); void markDelivered(String shipmentId); "
                + "Optional<Shipment> track(String shipmentId)"));

        index.put("com/acme/shipping/Shipment.java", model("Shipment", "String id; String orderId; String carrier; String trackingNumber; ShipmentStatus status"));

        index.put("com/acme/refund/RefundService.java", service("RefundService",
                "PaymentGateway payments; Refund process(String orderId, BigDecimal amount); "
                + "List<Refund> forOrder(String orderId); RefundStatus status(String refundId)"));

        index.put("com/acme/refund/Refund.java", model("Refund", "String id; String orderId; BigDecimal amount; RefundStatus status; Instant createdAt"));

        index.put("com/acme/util/ValidationUtils.java", util("ValidationUtils",
                "isValidEmail(String); isValidPhone(String); requirePositive(BigDecimal); isBlank(String)"));
        index.put("com/acme/util/DateUtils.java", util("DateUtils", "parse(String); format(Instant); now(); daysBetween(Instant,Instant)"));
        index.put("com/acme/util/MoneyUtils.java", util("MoneyUtils", "usd(BigDecimal); round(BigDecimal); sum(List<BigDecimal>)"));
        index.put("com/acme/config/AppConfig.java", config("AppConfig",
                "port; dbUrl; jwtSecret; corsOrigins; loadFrom(Properties); defaults()"));

        return index;
    }

    private static String service(String name, String body) {
        return "package com.acme;\n\n"
                + "import java.util.*;\nimport java.math.BigDecimal;\nimport java.time.Instant;\n"
                + "import java.util.logging.Logger;\n\n"
                + "/** " + name + " — part of the sample e-commerce backend. */\n"
                + "public final class " + name + " {\n"
                + "    private static final Logger log = Logger.getLogger(" + name + ".class.getName());\n\n"
                + "    public " + name + "() {}\n\n"
                + "    " + body.replace("\n", "\n    ")
                + "\n}\n";
    }

    private static String repo(String name, String entity, String body) {
        return "package com.acme;\n\nimport java.util.*;\nimport java.util.concurrent.ConcurrentHashMap;\n\n"
                + "/** In-memory repository for " + entity + ". */\n"
                + "public final class " + name + " {\n"
                + "    private final Map<String, " + entity + "> store = new ConcurrentHashMap<>();\n"
                + "    public void save(" + entity + " e) { store.put(idOf(e), e); }\n"
                + "    public Optional<" + entity + "> findById(String id) { return Optional.ofNullable(store.get(id)); }\n"
                + "    public List<" + entity + "> findAll() { return List.copyOf(store.values()); }\n"
                + "    public void delete(String id) { store.remove(id); }\n"
                + "    private static String idOf(" + entity + " e) { return e.toString(); }\n"
                + "}\n";
    }

    private static String model(String name, String fields) {
        return "package com.acme;\n\nimport java.math.BigDecimal;\nimport java.time.Instant;\nimport java.util.*;\n\n"
                + "/** Immutable record: " + fields + " */\n"
                + "public record " + name + "(" + fields + ") {}\n";
    }

    private static String interface_(String name, String methods) {
        return "package com.acme;\n\nimport java.math.BigDecimal;\n\n"
                + "public interface " + name + " {\n    " + methods + "\n}\n";
    }

    private static String util(String name, String methods) {
        return "package com.acme;\n\nimport java.math.BigDecimal;\nimport java.time.Instant;\n\n"
                + "public final class " + name + " {\n    private " + name + "() {}\n"
                + "    // " + methods + "\n}\n";
    }

    private static String config(String name, String fields) {
        return "package com.acme;\n\nimport java.util.Properties;\n\n"
                + "public final class " + name + " {\n"
                + "    // " + fields + "\n"
                + "    public static " + name + " loadFrom(Properties p) { return new " + name + "(); }\n"
                + "    public static " + name + " defaults() { return new " + name + "(); }\n"
                + "}\n";
    }
}
