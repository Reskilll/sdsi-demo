package com.claudecutter.demo;

import com.claudecutter.model.ModelUsage;
import com.claudecutter.provider.LlmClient;
import com.claudecutter.provider.LlmResponse;

/**
 * Offline stand-in so the pipeline + dashboard run without API keys.
 *
 * <p>Routing/compression return machine-parseable output as the real cheap model
 * would; the final "Claude" answer returns a canned-but-plausible response keyed
 * off the prompt, so the demo reads like a real assistant instead of a stub.
 */
final class MockLlmClient implements LlmClient {

    private final String model;
    private final long inputTokPerCall;
    private final long outputTokPerCall;

    MockLlmClient(String model, long in, long out) {
        this.model = model;
        this.inputTokPerCall = in;
        this.outputTokPerCall = out;
    }

    @Override
    public String model() {
        return model;
    }

    @Override
    public LlmResponse complete(String system, String user) {
        String text = answer(system, user);
        ModelUsage u = new ModelUsage(model,
                inputTokPerCall + user.length() / 4,
                outputTokPerCall + text.length() / 4, 0, 0);
        return new LlmResponse(text, u);
    }

    private String answer(String system, String user) {
        if (system.contains("classifier")) {
            String lower = user.toLowerCase();
            boolean complex = lower.contains("refactor") || lower.contains("bug")
                    || lower.contains("feature") || lower.contains("across")
                    || lower.contains("login") || lower.contains("build")
                    || lower.contains("implement") || lower.contains("create");
            return complex
                    ? "{\"complexity\":\"complex\",\"reason\":\"multi-step coding task\"}"
                    : "{\"complexity\":\"trivial\",\"reason\":\"single answer\"}";
        }
        if (system.contains("locator")) {
            // Return the whole (small) codebase so the "without plugin" baseline
            // reflects what Claude would actually read without us.
            return "[\"com/acme/orders/OrderService.java\","
                    + "\"com/acme/orders/model/Order.java\","
                    + "\"com/acme/orders/model/Customer.java\","
                    + "\"com/acme/orders/repo/OrderRepository.java\","
                    + "\"com/acme/orders/repo/OrderAuditLog.java\","
                    + "\"com/acme/orders/notify/NotificationService.java\","
                    + "\"com/acme/orders/service/InventoryService.java\","
                    + "\"com/acme/orders/service/PricingService.java\","
                    + "\"com/acme/auth/AuthController.java\","
                    + "\"com/acme/auth/service/UserService.java\","
                    + "\"com/acme/auth/model/User.java\","
                    + "\"com/acme/payments/PaymentGateway.java\"]";
        }
        if (system.contains("compress")) {
            return "OrderService: createOrder(customer, items, promoCode) -> Order; "
                    + "checkout(orderId) -> PaymentResult; cancel(orderId). "
                    + "Order: id, customer, items, subtotal, discount, tax, total, status, createdAt. "
                    + "OrderRepository: save/ findById in-memory map.";
        }
        return realisticAnswer(user);
    }

    private String realisticAnswer(String user) {
        String lower = user.toLowerCase();
        if (lower.contains("login")) {
            return """
                    Here's a minimal login page (HTML + CSS + a JS handler):

                    ```html
                    <!doctype html>
                    <html>
                    <head>
                      <meta charset="utf-8">
                      <title>Login</title>
                      <style>
                        body { display:grid; place-items:center; height:100vh; margin:0;
                               font-family:system-ui,sans-serif; background:#f4f4f6; }
                        form { display:flex; flex-direction:column; gap:12px; width:280px;
                               padding:28px; background:#fff; border-radius:10px;
                               box-shadow:0 8px 24px rgba(0,0,0,.08); }
                        input { padding:10px; border:1px solid #ddd; border-radius:6px; }
                        button { padding:10px; background:#2a78d6; color:#fff; border:0;
                                 border-radius:6px; cursor:pointer; font-weight:600; }
                      </style>
                    </head>
                    <body>
                      <form onsubmit="return login(event)">
                        <h2 style="margin:0">Sign in</h2>
                        <input id="email" type="email" placeholder="Email" required>
                        <input id="pass" type="password" placeholder="Password" required>
                        <button type="submit">Log in</button>
                      </form>
                      <script>
                        function login(e) {
                          e.preventDefault();
                          const email = document.getElementById('email').value;
                          fetch('/api/login', {
                            method: 'POST',
                            headers: {'Content-Type':'application/json'},
                            body: JSON.stringify({ email })
                          }).then(r => r.json()).then(console.log);
                          return false;
                        }
                      </script>
                    </body>
                    </html>
                    ```
                    """;
        }
        if (lower.contains("refactor")) {
            return """
                    Sure. Here's a clean refactor of the checkout flow to extract the
                    payment-charge step behind an interface and make it testable:

                    ```java
                    public PaymentResult checkout(String orderId) {
                        Order order = repository.findById(orderId)
                                .orElseThrow(() -> new OrderNotFoundException(orderId));
                        assertDraft(order);
                        PaymentResult result = payments.charge(order.total(), order.customer());
                        order = result.succeeded()
                                ? repository.save(order.withStatus(OrderStatus.PAID))
                                : order;
                        if (result.succeeded()) {
                            notifications.sendConfirmation(order);
                        }
                        return result;
                    }

                    private void assertDraft(Order order) {
                        if (order.status() != OrderStatus.DRAFT) {
                            throw new IllegalStateException("order " + order.id() + " is not draft");
                        }
                    }
                    ```
                    """;
        }
        if (lower.contains("hello") || lower.contains("hi")) {
            return "Hello! I'm your coding assistant. Ask me to build or explain something "
                    + "and I'll route it through the token-saving pipeline.";
        }
        if (lower.contains("what can you do") || lower.contains("help")
                || lower.contains("what are you") || lower.contains("capabilit")) {
            return """
                    I can help you with coding tasks. For example:
                    - "Write a login page in HTML/CSS"
                    - "Add retry logic to the checkout payment flow"
                    - "Explain what OrderService.checkout does"
                    - "Find where password hashing is implemented"

                    Behind the scenes, easy questions go to a cheap model, and harder
                    coding tasks are routed to Claude with the relevant code compressed
                    first — so Claude spends fewer tokens.
                    """;
        }
        if (lower.contains("explain") || lower.contains("what does")
                || lower.contains("how does")) {
            return "Let me explain. In this sample codebase, the relevant code is located "
                    + "and summarized before being shown to the answering model. For a real "
                    + "codebase, the compressor would preserve method signatures and key "
                    + "behavior while dropping comments and boilerplate.";
        }
        if (lower.contains("test") || lower.contains("unit test")) {
            return """
                    Here's a JUnit test outline for the checkout flow:

                    ```java
                    @Test
                    void checkout_paidOrder_movesToPaid() {
                        Order order = new Order("o1", customer, items, ZERO, ZERO, ZERO,
                                TEN, OrderStatus.DRAFT, Instant.now());
                        when(repo.findById("o1")).thenReturn(Optional.of(order));
                        when(payments.charge(any(), any())).thenReturn(new PaymentResult(true, null));

                        var result = service.checkout("o1");

                        assertTrue(result.succeeded());
                        verify(repo).save(order.withStatus(OrderStatus.PAID));
                    }
                    ```
                    """;
        }
        if (lower.contains("bug") || lower.contains("error") || lower.contains("fix")) {
            return "To find the bug, I'd trace the failing path through the relevant code. "
                    + "For example, in checkout(), if payments.charge() returns a failed result "
                    + "the order stays DRAFT but no notification is sent — check whether that "
                    + "matches the intended behavior.";
        }
        return "I don't have a canned answer for that in the offline demo. With real API keys "
                + "(DASHSCOPE_API_KEY + ANTHROPIC_API_KEY), the live model would answer it "
                + "directly. Try asking about the sample e-commerce app — e.g. \"write a login "
                + "page\", \"explain checkout\", or \"add retry to payments\".";
    }
}
