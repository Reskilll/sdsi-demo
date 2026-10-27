# PROMPTS.md — AI Collaboration History

This document details the structured engineering conversations and iterative prompt strategy used to co-develop the Flash Sale Inventory Reservation System.

## 🤖 Collaboration Summary
The system design was developed across three focused iterations to progress from a basic structural scaffolding into a thread-safe, production-ready concurrency engine.

---

## 🗺️ Engineering Progression

### Phase 1: Context Setup & Intent Parsing
*   **User Action:** Supplied the initial SDSI Hackathon entry guidelines and generic document triage framework.
*   **AI Action:** Generated an isolated routing architecture template implementing status classification rules and a human-in-the-loop fallback mechanism.

### Phase 2: Problem Alignment & Requirement Ingestion
*   **User Action:** Provided the formal **PS4: Inventory Reservation System (Flash Sale)** brief containing strict milestones (**M1** through **M5**).
*   **AI Action:** Redesigned the agent into an in-memory transactional database engine, utilizing atomic `threading.Lock` primitives to prevent race conditions during high-volume sales.

### Phase 3: Optimizations & Edge Case Proofing
*   **User Action:** Requested comprehensive implementation runtime tracking and verification configurations.
*   **AI Action:** Delivered clean, zero-dependency source layouts (`agent.py`, `run_agent.py`, and `README.md`) featuring a decoupled, lazy TTL-cleansing mechanism to optimize CPU performance under heavy traffic loads.

---

## 🛠️ Key Prompts Used

```text
"I got the below actual problem statement , please design accordingly:
Problem statement — PS4: Inventory Reservation System (Flash Sale)
Prevent overselling during a flash sale.
M1 Load products and stock from some sample input file...
M2 Reserve stock for a user, held for a TTL...
M3 Confirm permanently deducts... Cancel or TTL expiry releases it.
M4 Enforce a per-user purchase limit per SKU.
M5 Report available, reserved and sold counts..."
```

```text
"yes please generate Readme md file"
```
