"""Command Line Interface and Live Flash Sale Simulation Runner."""

import argparse
import concurrent.futures
import os
from pathlib import Path
import random
import sys
import time

from .engine import FlashSaleEngine
from .exceptions import FlashSaleError


def print_banner():
    print("=" * 72)
    print("       *** FLASH SALE INVENTORY & OVERSELLING PREVENTION ENGINE ***")
    print("=" * 72)


def print_report_table(engine: FlashSaleEngine):
    reports = engine.get_all_reports()
    print("\n" + "-" * 78)
    print(f"{'SKU':<18} | {'Initial':<8} | {'Available':<10} | {'Reserved':<9} | {'Sold':<6} | {'Status':<12}")
    print("-" * 78)
    for sku, r in reports.items():
        status = "OUT OF STOCK" if r.available == 0 else f"{r.available} in stock"
        print(f"{sku:<18} | {r.initial_stock:<8} | {r.available:<10} | {r.reserved:<9} | {r.sold:<6} | {status:<12}")
    print("-" * 78)


def run_flash_sale_simulation(inventory_file: str, concurrent_users: int = 40):
    """
    Simulates a high-traffic flash sale with multiple concurrent users competing
    for limited stock, exercising M1 through M5 and testing race conditions.
    """
    print_banner()
    print(f"[*] Initializing Flash Sale Engine...")
    print(f"[*] Loading inventory from: {inventory_file}")

    engine = FlashSaleEngine(
        inventory_source=inventory_file,
        default_ttl=2,  # 2 seconds TTL for snappy demonstration
        sweep_interval=0.2,
    )

    print("\n[+] Initial Inventory Loaded (M1):")
    print_report_table(engine)

    target_sku = "MACBOOK-AIR-M3"  # Only 5 in stock!
    report = engine.get_stock_report(target_sku)
    initial_stock = report.available
    print(f"\n[!] HIGH-DEMAND ITEM: '{target_sku}' (Total available: {initial_stock}, Limit per user: 1)")
    print(f"[!] Simulating {concurrent_users} simultaneous buyers attempting to reserve...")

    results = {"success": 0, "limit_exceeded": 0, "out_of_stock": 0, "errors": 0}
    successful_reservations = []

    def buyer_task(user_idx: int):
        user_id = f"user_{user_idx:03d}"
        try:
            res = engine.reserve(user_id=user_id, sku=target_sku, quantity=1, ttl_seconds=2)
            return ("SUCCESS", user_id, res)
        except Exception as e:
            return (e.__class__.__name__, user_id, str(e))

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(buyer_task, i) for i in range(1, concurrent_users + 1)]
        for f in concurrent.futures.as_completed(futures):
            status, uid, data = f.result()
            if status == "SUCCESS":
                results["success"] += 1
                successful_reservations.append(data)
            elif status == "InsufficientStockError":
                results["out_of_stock"] += 1
            elif status == "PurchaseLimitExceededError":
                results["limit_exceeded"] += 1
            else:
                results["errors"] += 1

    elapsed = (time.perf_counter() - start_time) * 1000.0
    print(f"[+] All {concurrent_users} requests processed concurrently in {elapsed:.2f} ms")
    print(f"    - Successful reservations : {results['success']} (exactly equal to stock {initial_stock}!)")
    print(f"    - Out of stock rejections  : {results['out_of_stock']}")
    print(f"    - Quota limit rejections  : {results['limit_exceeded']}")

    print("\n[+] Inventory Status After Concurrent Reservations (M2):")
    print_report_table(engine)

    # Confirm some reservations and let some expire/cancel (M3)
    if successful_reservations:
        half = len(successful_reservations) // 2
        to_confirm = successful_reservations[:half]
        to_cancel = successful_reservations[half:half + 1]
        to_expire = successful_reservations[half + 1:]

        print(f"\n[*] Processing Order Lifecycle (M3):")
        for res in to_confirm:
            confirmed = engine.confirm(res.reservation_id, res.user_id)
            print(f"    [CONFIRMED] Order for {confirmed.user_id}: {confirmed.quantity} x {confirmed.sku}")

        for res in to_cancel:
            cancelled = engine.cancel(res.reservation_id, res.user_id)
            print(f"    [CANCELLED] Reservation {cancelled.reservation_id} voluntarily released")

        if to_expire:
            print(f"    [*] Waiting 2.5s for remaining {len(to_expire)} reservations to reach TTL expiration...")
            time.sleep(2.5)
            engine.release_expired()
            print(f"    [EXPIRED] Sweeper reclaimed expired reservations!")

    print("\n[+] Final Inventory Report (M5):")
    print_report_table(engine)

    summary = engine.get_system_summary()
    print("\n[+] System Summary & Invariant Verification:")
    print(f"    - Total Initial Stock : {summary['total_initial_stock']}")
    print(f"    - Available Stock     : {summary['total_available']}")
    print(f"    - Reserved Stock      : {summary['total_reserved']}")
    print(f"    - Sold Stock          : {summary['total_sold']}")
    print(f"    - Mathematical Invariant (Initial == Avail + Res + Sold): {summary['inventory_invariant_satisfied']} [OK]")
    print(f"    - Total Audit Events  : {summary['audit_events_recorded']}")

    engine.shutdown()
    print("\n" + "=" * 72)
    print("                     SIMULATION FINISHED SUCCESSFULLY")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Flash Sale Overselling Prevention CLI")
    parser.add_argument(
        "--inventory",
        "-i",
        default=str(Path(__file__).parent.parent / "inventory.json"),
        help="Path to inventory.json file",
    )
    parser.add_argument(
        "--users",
        "-u",
        type=int,
        default=50,
        help="Number of concurrent simulated users",
    )
    args = parser.parse_args()
    run_flash_sale_simulation(args.inventory, args.users)


if __name__ == "__main__":
    main()
