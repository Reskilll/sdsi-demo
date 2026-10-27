import time
from agent import run

# Simulating Sample Input Data Profile (M1)
sample_inventory = """{
    "action": "load",
    "payload": {
        "data": [
            {"sku": "IPHONE15", "stock": 5},
            {"sku": "PLAYSTATION5", "stock": 2}
        ]
    }
}"""

print("--- Step 1: Loading Stock Matrix ---")
print(run(sample_inventory))

print("\n--- Step 2: Reserving Valid Stock (User A) ---")
res_user_a = """{"action": "reserve", "payload": {"user_id": "user_A", "sku": "IPHONE15", "qty": 2}}"""
print(run(res_user_a))

print("\n--- Step 3: Checking Metrics State (M5) ---")
report_sku = """{"action": "report", "payload": {"sku": "IPHONE15"}}"""
print(run(report_sku))

print("\n--- Step 4: Enforcing Purchase Limits (User A requesting 2 more, Limit is 2) (M4) ---")
res_user_a_exploit = """{"action": "reserve", "payload": {"user_id": "user_A", "sku": "IPHONE15", "qty": 2}}"""
print(run(res_user_a_exploit))

print("\n--- Step 5: Confirming Stock Purchase (M3) ---")
confirm_user_a = """{"action": "confirm", "payload": {"user_id": "user_A", "sku": "IPHONE15"}}"""
print(run(confirm_user_a))

print("\n--- Step 6: Verifying Updated Inventory Report Profile ---")
print(run(report_sku))

print("\n--- Step 7: Testing TTL Reservation Hold Expiry Edge Case (Holding for 1 sec) (M2) ---")
res_ttl_expiry = """{"action": "reserve", "payload": {"user_id": "user_B", "sku": "PLAYSTATION5", "qty": 1, "ttl": 1}}"""
print(run(res_ttl_expiry))
print("Stock metrics during hold:")
print(run("""{"action": "report", "payload": {"sku": "PLAYSTATION5"}}"""))

print("Sleeping 1.5 seconds to pass TTL...")
time.sleep(1.5)

print("Stock metrics after TTL expiration:")
print(run("""{"action": "report", "payload": {"sku": "PLAYSTATION5"}}"""))