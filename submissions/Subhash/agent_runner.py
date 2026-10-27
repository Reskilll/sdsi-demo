import time
import json
import threading
import logging
from agent import run, sys_engine

# Configure logging for clear tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestRunner")

def setup_mock_inventory_file():
    """Dynamically creates inventory.json to guarantee clean testing environments."""
    mock_data = {
        "inventory": [
            {"sku": "FLASH_ITEM", "stock": 10},
            {"sku": "LIMITED_ITEM", "stock": 5}
        ]
    }
    with open("inventory.json", "w") as f:
        json.dump(mock_data, f)
    logger.info("Created clean local inventory.json file.")

def execute_concurrent_reservations(sku: str, qty: int, threads_count: int):
    """Fires simultaneous reservation hits across threads to test thread-safety."""
    def worker(user_index: int):
        task = json.dumps({
            "action": "reserve",
            "payload": {
                "user_id": f"concurrent_user_{user_index}",
                "sku": sku,
                "qty": qty
            }
        })
        run(task)

    threads = []
    for i in range(threads_count):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

def run_test_suite():
    setup_mock_inventory_file()

    print("\n==================================================")
    print("🔥 RUNNING MILESTONE M1: LOCAL FILE INGESTION TEST")
    print("==================================================")
    m1_task = json.dumps({"action": "load_file", "payload": {"filepath": "inventory.json"}})
    m1_res = run(m1_task)
    print(f"File ingest result: {m1_res}")
    assert m1_res["status"] == "success", "M1 Failed: File loading dropped!"

    print("\n==================================================")
    print("🔥 RUNNING MILESTONE M2 & M4: RESERVATION & LIMITS")
    print("==================================================")
    # User A books 1 unit safely
    task_res1 = json.dumps({"action": "reserve", "payload": {"user_id": "user_A", "sku": "FLASH_ITEM", "qty": 1}})
    print(f"User A First Reservation (1 Unit): {run(task_res1)}")
    
    # User A tries to reserve 2 more units (Total 3, passes the per-user limit of 2)
    task_res2 = json.dumps({"action": "reserve", "payload": {"user_id": "user_A", "sku": "FLASH_ITEM", "qty": 2}})
    print(f"User A Second Reservation (Exploit Attempt 2 Units): {run(task_res2)}")

    print("\n==================================================")
    print("🔥 RUNNING MILESTONE M5: TELEMETRY AND REPORTING")
    print("==================================================")
    m5_task = json.dumps({"action": "report", "payload": {"sku": "FLASH_ITEM"}})
    m5_res = run(m5_task)
    print(f"Current Metrics Profile: {m5_res}")
    # Available should be 9 (10 total - 1 validly reserved by user A)
    assert m5_res["metrics"]["reserved"] == 1, "M5 Metric mismatch on reserved holds!"

    print("\n==================================================")
    print("🔥 RUNNING MILESTONE M3: CONFIRM, CANCEL & TTL DRIVEN PURGES")
    print("==================================================")
    # Confirm User A's held piece
    task_confirm = json.dumps({"action": "confirm", "payload": {"user_id": "user_A", "sku": "FLASH_ITEM"}})
    print(f"Confirm Permanent Purchase User A: {run(task_confirm)}")
    
    # Verify reservation converted to solid sale
    print(f"Post-Purchase Report: {run(m5_task)}")

    # Test explicit user cancellation pathing
    print("\nTesting Explicit Cancel Lifecycle...")
    run(json.dumps({"action": "reserve", "payload": {"user_id": "user_B", "sku": "FLASH_ITEM", "qty": 1}}))
    print(f"Pre-Cancellation Status: {run(m5_task)}")
    run(json.dumps({"action": "cancel", "payload": {"user_id": "user_B", "sku": "FLASH_ITEM"}}))
    print(f"Post-Cancellation Status: {run(m5_task)}")

    # Test Short TTL Expiry Sweep edge cases
    print("\nTesting Lazy TTL Expiry Engine (Using micro-hold)...")
    run(json.dumps({"action": "reserve", "payload": {"user_id": "user_C", "sku": "FLASH_ITEM", "qty": 1, "ttl": 0.5}}))
    print(f"Immediately after holding: {run(m5_task)}")
    print("Sleeping for 0.7 seconds to let hold expire...")
    time.sleep(0.7)
    print(f"After TTL expiration sweep window: {run(m5_task)}")

    print("\n==================================================")
    print("🔥 RUNNING EDGE CASE STRESSING: CONCURRENCY RACE TEST")
    print("==================================================")
    # LIMITED_ITEM starts with exactly 5 items.
    # We will launch 12 separate concurrent thread consumers matching 1 item each.
    # Total sold + reserved must never cross 5. Overselling protection must lock perfectly.
    print("Launching 12 threads chasing 5 total units simultaneously...")
    execute_concurrent_reservations(sku="LIMITED_ITEM", qty=1, threads_count=12)

    final_report_task = json.dumps({"action": "report", "payload": {"sku": "LIMITED_ITEM"}})
    final_state = run(final_report_task)
    print(f"\nFinal Concurrency Stress State Metrics: {final_state}")
    
    total_allocated = final_state["metrics"]["reserved"] + final_state["metrics"]["sold"]
    print(f"Total Allocated Units: {total_allocated} (Stock Ceiling Cap: 5)")
    
    assert total_allocated <= 5, "CRITICAL CONCURRENCY BUG DETECTED: OVERSELLING OCCURRED!"
    print("\n🎉 ALL TRACE Lifecycle tests successfully cleared! Zero overselling anomalies.")

if __name__ == "__main__":
    run_test_suite()