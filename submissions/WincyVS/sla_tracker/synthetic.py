"""Synthetic benchmark generator — realistic edge-case tickets."""

import json
import random
from datetime import datetime, timedelta, timezone


PRIORITIES = ["P1", "P2", "P3", "P4"]
GROUPS = ["Network Ops", "Infrastructure", "Security Team", "App Support", "DB Admin", "Unassigned"]


def _rand_dt(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.uniform(0, delta))


def generate_tickets(
    count: int = 50,
    seed: int = 42,
    edge_case_ratio: float = 0.3,
) -> list[dict]:
    """Generate synthetic tickets with realistic status transitions and edge cases."""

    random.seed(seed)
    base_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    base_end = datetime(2026, 10, 27, tzinfo=timezone.utc)

    tickets = []

    for i in range(count):
        priority = random.choices(PRIORITIES, weights=[0.1, 0.2, 0.3, 0.4])[0]
        group = random.choice(GROUPS)
        ticket_id = f"TKT-{i+1:04d}"

        created = _rand_dt(base_start, base_end - timedelta(days=3))

        is_edge = random.random() < edge_case_ratio
        edge_type = random.randint(0, 4) if is_edge else -1

        transitions = [{"timestamp": created.isoformat(), "status": "CREATED"}]
        current_time = created
        current_status = "CREATED"

        if edge_type == 0:
            # EC1: Created outside business hours (weekend or late night)
            wd = created.weekday()
            if wd < 5:
                created = created.replace(hour=random.choice([21, 22, 23, 2, 3, 5]))
                transitions = [{"timestamp": created.isoformat(), "status": "CREATED"}]
        elif edge_type == 1:
            # EC6: Created directly in ON_HOLD
            transitions.append({
                "timestamp": (created + timedelta(minutes=1)).isoformat(),
                "status": "ON_HOLD",
            })
            current_status = "ON_HOLD"
        elif edge_type == 2:
            # EC4: Rapid repeated ON_HOLD ↔ IN_PROGRESS
            for _ in range(random.randint(3, 8)):
                current_time += timedelta(minutes=random.randint(1, 30))
                new_status = "IN_PROGRESS" if current_status == "ON_HOLD" else "ON_HOLD"
                transitions.append({"timestamp": current_time.isoformat(), "status": new_status})
                current_status = new_status
        elif edge_type == 3:
            # EC3: ON_HOLD over weekend
            if created.weekday() == 4:  # Friday
                fri_eve = created.replace(hour=17, minute=0)
                transitions.append({"timestamp": fri_eve.isoformat(), "status": "ON_HOLD"})
                mon_morn = fri_eve + timedelta(days=3)  # Monday
                transitions.append({"timestamp": mon_morn.isoformat(), "status": "IN_PROGRESS"})
                current_status = "IN_PROGRESS"

        # Normal flow for non-edge or continuation
        if current_status in ("CREATED", "IN_PROGRESS"):
            if current_status == "CREATED":
                current_time += timedelta(minutes=random.randint(5, 120))
                transitions.append({"timestamp": current_time.isoformat(), "status": "IN_PROGRESS"})
                current_status = "IN_PROGRESS"

            # Maybe go ON_HOLD once
            if random.random() < 0.3 and edge_type not in (1, 2, 3):
                current_time += timedelta(minutes=random.randint(30, 480))
                transitions.append({"timestamp": current_time.isoformat(), "status": "ON_HOLD"})
                current_status = "ON_HOLD"
                # Resume
                current_time += timedelta(hours=random.uniform(0.5, 48))
                transitions.append({"timestamp": current_time.isoformat(), "status": "IN_PROGRESS"})
                current_status = "IN_PROGRESS"

            # Resolve
            current_time += timedelta(hours=random.uniform(0.5, 120))
            transitions.append({"timestamp": current_time.isoformat(), "status": "RESOLVED"})

        elif current_status == "ON_HOLD":
            # Was put on hold, now resolve
            current_time += timedelta(hours=random.uniform(0.5, 24))
            transitions.append({"timestamp": current_time.isoformat(), "status": "IN_PROGRESS"})
            current_time += timedelta(minutes=random.randint(10, 60))
            transitions.append({"timestamp": current_time.isoformat(), "status": "RESOLVED"})

        tickets.append({
            "ticket_id": ticket_id,
            "priority": priority,
            "assignee_group": group,
            "transitions": transitions,
        })

    return tickets


def main(output_path: str = "data/tickets.json", count: int = 50, seed: int = 42) -> None:
    tickets = generate_tickets(count=count, seed=seed)
    with open(output_path, "w") as f:
        json.dump(tickets, f, indent=2)
    print(f"Generated {len(tickets)} tickets → {output_path}")


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "data/tickets.json"
    cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    main(output, cnt)