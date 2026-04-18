"""
Seed PPSA workout templates: Squatober 2023 (22 training days) and 70s Big (20 days).

Usage (server must be running):
    python scripts/seed_ppsa_templates.py

Or with a custom base URL / credentials:
    BASE_URL=http://127.0.0.1:8080 USERNAME=admin PASSWORD=password \
        python scripts/seed_ppsa_templates.py

The script is idempotent-ish: it will create duplicates if run twice.
To wipe and re-seed, delete existing PPSA templates from the UI first.
"""
import os
import sys
import json
import urllib.request
import urllib.error

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8080")
USERNAME = os.getenv("USERNAME", "admin")
PASSWORD = os.getenv("PASSWORD", "password")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def login():
    status, body = _request("POST", "/api/users/login",
                             {"username": USERNAME, "password": PASSWORD})
    if status != 200:
        print(f"Login failed ({status}): {body}")
        sys.exit(1)
    return body["token"]


def get_library(token):
    _, items = _request("GET", "/api/library/", token=token)
    return {item["name"]: item["id"] for item in items}


def create(token, name, description, exercises):
    status, body = _request("POST", "/api/templates/",
                             {"name": name, "description": description, "exercises": exercises},
                             token=token)
    if status == 201:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}: {status} {str(body)[:100]}")


# ── Set/exercise builders ─────────────────────────────────────────────────────

def s(n, reps=None, pct=None, weight=None, set_type="work"):
    row = {"set_number": n, "set_type": set_type}
    if reps is not None:
        row["reps"] = reps
    if pct is not None:
        row["percent"] = pct
    if weight is not None:
        row["weight"] = weight
    return row


def ex(eid, order, note, sets):
    return {"exercise_id": eid, "order_index": order, "notes": note, "sets": sets}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = login()
    lib = get_library(token)

    # Resolve IDs — fall back to None so the error is obvious rather than silent
    def eid(name):
        result = lib.get(name)
        if result is None:
            print(f"  WARNING: '{name}' not found in exercise library")
        return result

    E = {
        "back_squat":    eid("Back Squat"),
        "front_squat":   eid("Front Squat"),
        "deadlift":      eid("Deadlift"),
        "rdl":           eid("Romanian Deadlift"),
        "bench":         eid("Bench Press"),
        "cgbench":       eid("Close-Grip Bench Press"),
        "ohp":           eid("Overhead Press"),
        "incline":       eid("Incline Bench Press"),
        "chinup":        eid("Chin-up"),
        "pullup":        eid("Pull-up"),
        "bent_row":      eid("Bent Over Row"),
        "db_row":        eid("Single Arm Dumbbell Row"),
        "lateral":       eid("Lateral Raise"),
        "rear_delt":     eid("Rear Delt Fly"),
        "curl":          eid("Barbell Curl"),
        "skull":         eid("Skull Crusher"),
        "pushdown":      eid("Tricep Pushdown"),
        "kickback":      eid("Kickback"),
        "lunge":         eid("Lunge"),
        "bss":           eid("Bulgarian Split Squat"),
        "kb_swing":      eid("Kettlebell Swing"),
        "seated_press":  eid("Seated Dumbbell Press"),
        "arnold":        eid("Arnold Press"),
        "pushup":        eid("Push-up"),
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # PPSA SQUATOBER 2023
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n── PPSA SQUATOBER 2023 ──")

    create(token, "Squatober Day 1 – Welcome to the Show", "PPSA Squatober 2023 • Day 1", [
        ex(E["back_squat"], 1, "3x5@70%, then 3x3@78%", [
            s(1,reps=5,pct=70), s(2,reps=5,pct=70), s(3,reps=5,pct=70),
            s(4,reps=3,pct=78), s(5,reps=3,pct=78), s(6,reps=3,pct=78),
        ]),
        ex(E["bench"], 2, "6x10@50% — superset with DB Lateral Raises 6x10", [s(i+1,reps=10,pct=50) for i in range(6)]),
        ex(E["lateral"], 3, "6x10 — superset with Bench Press", [s(i+1,reps=10) for i in range(6)]),
        ex(E["rdl"], 4, "4x5 — superset with BB Bent Over Rows 4x5", [s(i+1,reps=5) for i in range(4)]),
        ex(E["bent_row"], 5, "4x5 — superset with BB RDLs", [s(i+1,reps=5) for i in range(4)]),
    ])

    create(token, "Squatober Day 2 – Take Em Down Take Em Up", "PPSA Squatober 2023 • Day 2", [
        ex(E["back_squat"], 1, "3x5@72%, then 3x3@80%", [
            s(1,reps=5,pct=72), s(2,reps=5,pct=72), s(3,reps=5,pct=72),
            s(4,reps=3,pct=80), s(5,reps=3,pct=80), s(6,reps=3,pct=80),
        ]),
        ex(E["front_squat"], 2, "3x5@45-50% of back squat max", [s(i+1,reps=5) for i in range(3)]),
        ex(E["ohp"], 3, "4x5 standing BB OHP — superset with Slow Strict Chin Ups 4x3-5", [s(i+1,reps=5) for i in range(4)]),
        ex(E["chinup"], 4, "4x3-5 Slow Strict — superset with OHP", [s(i+1,reps=4) for i in range(4)]),
    ])

    create(token, "Squatober Day 3 – Slow Speed Zone", "PPSA Squatober 2023 • Day 3 • 5-sec descent squats + deadlift volume", [
        ex(E["back_squat"], 1, "5x5@60% — 5-second descent (slow tempo)", [s(i+1,reps=5,pct=60) for i in range(5)]),
        ex(E["deadlift"], 2, "10x3@70%", [s(i+1,reps=3,pct=70) for i in range(10)]),
    ])

    create(token, "Squatober Day 4 – Thick Thigh Thursday", "PPSA Squatober 2023 • Day 4", [
        ex(E["back_squat"], 1, "Complex: 5@65%, 4@70%, 3@75%, 2@80%, 1@85%, 3@80%, 4@75%, 5@70%", [
            s(1,reps=5,pct=65), s(2,reps=4,pct=70), s(3,reps=3,pct=75), s(4,reps=2,pct=80),
            s(5,reps=1,pct=85), s(6,reps=3,pct=80), s(7,reps=4,pct=75), s(8,reps=5,pct=70),
        ]),
        ex(E["bench"], 2, "Same complex — superset with Slow Strict Chin Ups 6x3-5", [
            s(1,reps=5,pct=65), s(2,reps=4,pct=70), s(3,reps=3,pct=75), s(4,reps=2,pct=80),
            s(5,reps=1,pct=85), s(6,reps=3,pct=80), s(7,reps=4,pct=75), s(8,reps=5,pct=70),
        ]),
        ex(E["chinup"], 3, "6x3-5 Slow Strict — superset with Bench Press", [s(i+1,reps=4) for i in range(6)]),
    ])

    create(token, "Squatober Day 5 – Unbroken Business", "PPSA Squatober 2023 • Day 5 • unbroken sets", [
        ex(E["back_squat"], 1, "Unbroken: 5,6,7@70%, then 8,9,10@57%", [
            s(1,reps=5,pct=70), s(2,reps=6,pct=70), s(3,reps=7,pct=70),
            s(4,reps=8,pct=57), s(5,reps=9,pct=57), s(6,reps=10,pct=57),
        ]),
        ex(E["lunge"], 2, "DB Alternating Reverse Lunges 3x5/leg", [s(i+1,reps=10) for i in range(3)]),
        ex(E["rdl"], 3, "3x10 — superset with BB Bent Over Rows 3x10", [s(i+1,reps=10) for i in range(3)]),
        ex(E["bent_row"], 4, "3x10 — superset with RDLs", [s(i+1,reps=10) for i in range(3)]),
    ])

    create(token, "Squatober Day 8 – The Pressure Cooker", "PPSA Squatober 2023 • Day 8 • AMRAP doubles @85%", [
        ex(E["back_squat"], 1, "Work up to 85%, then AMRAP doubles @85% for 10 minutes", [
            s(1,reps=3,pct=60), s(2,reps=2,pct=70), s(3,reps=2,pct=80),
            s(4,reps=2,pct=85), s(5,reps=2,pct=85), s(6,reps=2,pct=85),
            s(7,reps=2,pct=85), s(8,reps=2,pct=85), s(9,reps=2,pct=85),
        ]),
        ex(E["bench"], 2, "5x5@75%", [s(i+1,reps=5,pct=75) for i in range(5)]),
    ])

    create(token, "Squatober Day 9 – 70s Big", "PPSA Squatober 2023 • Day 9 • high volume", [
        ex(E["back_squat"], 1, "6,7,8@70%, then 8,7,6@70%", [
            s(1,reps=6,pct=70), s(2,reps=7,pct=70), s(3,reps=8,pct=70),
            s(4,reps=8,pct=70), s(5,reps=7,pct=70), s(6,reps=6,pct=70),
        ]),
        ex(E["deadlift"], 2, "5x5@70%", [s(i+1,reps=5,pct=70) for i in range(5)]),
        ex(E["bent_row"], 3, "7x10 BB Bent Over Rows", [s(i+1,reps=10) for i in range(7)]),
        ex(E["lateral"], 4, "7x10 DB Shrugs", [s(i+1,reps=10) for i in range(7)]),
    ])

    create(token, "Squatober Day 10 – The Seesaw", "PPSA Squatober 2023 • Day 10 • seesaw pattern", [
        ex(E["back_squat"], 1, "Seesaw: 3@65%,1@80%,3@70%,1@83%,3@75%,1@86%", [
            s(1,reps=3,pct=65), s(2,reps=1,pct=80), s(3,reps=3,pct=70),
            s(4,reps=1,pct=83), s(5,reps=3,pct=75), s(6,reps=1,pct=86),
        ]),
        ex(E["ohp"], 2, "5x5 Standing BB OHP", [s(i+1,reps=5) for i in range(5)]),
        ex(E["rdl"], 3, "4x5 BB RDLs", [s(i+1,reps=5) for i in range(4)]),
    ])

    create(token, "Squatober Day 11 – Bend Pause Drive", "PPSA Squatober 2023 • Day 11 • 2-sec pause squats", [
        ex(E["back_squat"], 1, "4x5@65% — 2-second pause at bottom", [s(i+1,reps=5,pct=65) for i in range(4)]),
        ex(E["front_squat"], 2, "3x5@40-45% — 2-second pause", [s(i+1,reps=5) for i in range(3)]),
    ])

    create(token, "Squatober Day 12 – Friday the 13th", "PPSA Squatober 2023 • Day 12 • 13 total reps at top", [
        ex(E["back_squat"], 1, "3@60%, 3@70%, 2@80%, then @87% for 13 total reps (clusters OK)", [
            s(1,reps=3,pct=60), s(2,reps=3,pct=70), s(3,reps=2,pct=80),
            s(4,reps=5,pct=87), s(5,reps=4,pct=87), s(6,reps=4,pct=87),
        ]),
        ex(E["bench"], 2, "Same pattern: 3@60%, 3@70%, 2@80%, then @87% for 13 total reps", [
            s(1,reps=3,pct=60), s(2,reps=3,pct=70), s(3,reps=2,pct=80),
            s(4,reps=5,pct=87), s(5,reps=4,pct=87), s(6,reps=4,pct=87),
        ]),
    ])

    create(token, "Squatober Day 15 – Bill Starr Tribute", "PPSA Squatober 2023 • Day 15 • 5x5 ascending", [
        ex(E["back_squat"], 1, "5x5 ascending: @67%, 73%, 75%, 77%, 77%", [
            s(1,reps=5,pct=67), s(2,reps=5,pct=73), s(3,reps=5,pct=75), s(4,reps=5,pct=77), s(5,reps=5,pct=77),
        ]),
        ex(E["bench"], 2, "5x5 ascending: @67%, 73%, 75%, 77%, 77%", [
            s(1,reps=5,pct=67), s(2,reps=5,pct=73), s(3,reps=5,pct=75), s(4,reps=5,pct=77), s(5,reps=5,pct=77),
        ]),
        ex(E["deadlift"], 3, "5x5 ascending: @67%, 73%, 75%, 77%, 77%", [
            s(1,reps=5,pct=67), s(2,reps=5,pct=73), s(3,reps=5,pct=75), s(4,reps=5,pct=77), s(5,reps=5,pct=77),
        ]),
    ])

    create(token, "Squatober Day 16 – Super Set", "PPSA Squatober 2023 • Day 16 • heavy supersets", [
        ex(E["bss"], 1, "DB Bulgarian Split Squats 4x5/leg — superset with Back Squat", [s(i+1,reps=5) for i in range(4)]),
        ex(E["back_squat"], 2, "4x3@80% — superset with DB Bulgarian Split Squats", [s(i+1,reps=3,pct=80) for i in range(4)]),
        ex(E["front_squat"], 3, "3x5@45-50% — superset with Slow Strict Chin Ups", [s(i+1,reps=5) for i in range(3)]),
        ex(E["chinup"], 4, "3x3-5 Slow Strict — superset with Front Squat", [s(i+1,reps=4) for i in range(3)]),
    ])

    create(token, "Squatober Day 17 – The Echo Chamber", "PPSA Squatober 2023 • Day 17 • wave loading", [
        ex(E["back_squat"], 1, "Wave: 3@73%,2@80%,1@87%, 3@76%,2@83%,1@90%", [
            s(1,reps=3,pct=73), s(2,reps=2,pct=80), s(3,reps=1,pct=87),
            s(4,reps=3,pct=76), s(5,reps=2,pct=83), s(6,reps=1,pct=90),
        ]),
        ex(E["bench"], 2, "Wave: 3@73%,2@80%,1@87%, 3@76%,2@83%,1@90%", [
            s(1,reps=3,pct=73), s(2,reps=2,pct=80), s(3,reps=1,pct=87),
            s(4,reps=3,pct=76), s(5,reps=2,pct=83), s(6,reps=1,pct=90),
        ]),
    ])

    create(token, "Squatober Day 18 – Basic Strength", "PPSA Squatober 2023 • Day 18", [
        ex(E["bss"], 1, "BB Bulgarian Split Squats 4x5/leg — superset with Slow Strict Chin Ups 4x3-5", [s(i+1,reps=5) for i in range(4)]),
        ex(E["chinup"], 2, "4x3-5 Slow Strict — superset with BB Bulgarian Split Squats", [s(i+1,reps=4) for i in range(4)]),
        ex(E["back_squat"], 3, "4x5@70%", [s(i+1,reps=5,pct=70) for i in range(4)]),
        ex(E["front_squat"], 4, "3x5@40% of back squat max", [s(i+1,reps=5) for i in range(3)]),
    ])

    create(token, "Squatober Day 19 – Business Friday", "PPSA Squatober 2023 • Day 19 • descending squats + 10x10 bench", [
        ex(E["back_squat"], 1, "10@60%, 8@70%, 6@75%, 4@80%, 10@65%", [
            s(1,reps=10,pct=60), s(2,reps=8,pct=70), s(3,reps=6,pct=75), s(4,reps=4,pct=80), s(5,reps=10,pct=65),
        ]),
        ex(E["cgbench"], 2, "10x10@45-50% Close Grip Bench — superset with KB Swings 10x10", [s(i+1,reps=10,pct=50) for i in range(10)]),
        ex(E["kb_swing"], 3, "10x10 KB Swings — superset with Close Grip Bench", [s(i+1,reps=10) for i in range(10)]),
        ex(E["bent_row"], 4, "5x5 BB Bent Over Rows", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "Squatober Day 22 – The Rematch", "PPSA Squatober 2023 • Day 22 • AMRAP doubles rematch 16 min", [
        ex(E["back_squat"], 1, "3@55%, 3@65%, 2@75%, then @85% AMRAP doubles for 16 minutes", [
            s(1,reps=3,pct=55), s(2,reps=3,pct=65), s(3,reps=2,pct=75),
            s(4,reps=2,pct=85), s(5,reps=2,pct=85), s(6,reps=2,pct=85),
            s(7,reps=2,pct=85), s(8,reps=2,pct=85), s(9,reps=2,pct=85), s(10,reps=2,pct=85),
        ]),
        ex(E["bench"], 2, "5x5@72%", [s(i+1,reps=5,pct=72) for i in range(5)]),
    ])

    create(token, "Squatober Day 23 – Tuesday Tune Up", "PPSA Squatober 2023 • Day 23", [
        ex(E["back_squat"], 1, "5x3@60% — pause squat", [s(i+1,reps=3,pct=60) for i in range(5)]),
        ex(E["deadlift"], 2, "4x4@77% — superset with Slow Strict Chin Ups 4x3-5", [s(i+1,reps=4,pct=77) for i in range(4)]),
        ex(E["chinup"], 3, "4x3-5 Slow Strict — superset with Deadlift", [s(i+1,reps=4) for i in range(4)]),
        ex(E["curl"], 4, "5x10 BB Bicep Curls", [s(i+1,reps=10) for i in range(5)]),
    ])

    create(token, "Squatober Day 24 – Stairway to Strongville", "PPSA Squatober 2023 • Day 24 • staircase to 91%", [
        ex(E["back_squat"], 1, "Staircase build to 91%: 5@60%,4@68%,3@75%,2@82%,1@88%,1@91%; descend back", [
            s(1,reps=5,pct=60), s(2,reps=4,pct=68), s(3,reps=3,pct=75), s(4,reps=2,pct=82),
            s(5,reps=1,pct=88), s(6,reps=1,pct=91),
            s(7,reps=2,pct=85), s(8,reps=3,pct=78), s(9,reps=4,pct=70),
        ]),
        ex(E["bench"], 2, "Same staircase pattern to 91%", [
            s(1,reps=5,pct=60), s(2,reps=4,pct=68), s(3,reps=3,pct=75), s(4,reps=2,pct=82),
            s(5,reps=1,pct=88), s(6,reps=1,pct=91),
            s(7,reps=2,pct=85), s(8,reps=3,pct=78), s(9,reps=4,pct=70),
        ]),
    ])

    create(token, "Squatober Day 25 – Speedy Bends", "PPSA Squatober 2023 • Day 25 • speed work", [
        ex(E["back_squat"], 1, "5x5@55-65% — fast/explosive reps", [
            s(1,reps=5,pct=55), s(2,reps=5,pct=58), s(3,reps=5,pct=60), s(4,reps=5,pct=63), s(5,reps=5,pct=65),
        ]),
        ex(E["chinup"], 2, "4x3-5 Slow Strict — superset with Snatch Grip Deadlifts", [s(i+1,reps=4) for i in range(4)]),
        ex(E["deadlift"], 3, "4x5 Snatch Grip Deadlift (wide grip)", [s(i+1,reps=5) for i in range(4)]),
    ])

    create(token, "Squatober Day 26 – Seesaw Again Yes Please", "PPSA Squatober 2023 • Day 26 • heavy seesaw", [
        ex(E["back_squat"], 1, "Seesaw: 3@65%,1@80%,3@75%,1@85%,3@80%,1@88%", [
            s(1,reps=3,pct=65), s(2,reps=1,pct=80), s(3,reps=3,pct=75),
            s(4,reps=1,pct=85), s(5,reps=3,pct=80), s(6,reps=1,pct=88),
        ]),
        ex(E["bench"], 2, "Seesaw: 3@65%,1@80%,3@75%,1@85%,3@80%,1@88%", [
            s(1,reps=3,pct=65), s(2,reps=1,pct=80), s(3,reps=3,pct=75),
            s(4,reps=1,pct=85), s(5,reps=3,pct=80), s(6,reps=1,pct=88),
        ]),
        ex(E["bent_row"], 3, "5x5 BB Bent Over Rows", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "Squatober Day 29 – The Day Before", "PPSA Squatober 2023 • Day 29 • opener prep", [
        ex(E["back_squat"], 1, "Fast Forward: 4x4@50-55% — explosive, perfect reps", [
            s(1,reps=4,pct=50), s(2,reps=4,pct=52), s(3,reps=4,pct=54), s(4,reps=4,pct=55),
        ]),
    ])

    create(token, "Squatober Day 30 – The PR Party", "PPSA Squatober 2023 • Day 30 • MAX ATTEMPT", [
        ex(E["back_squat"], 1, "PR Ladder: 5@50%,3@65%,2@75%,1@85%,1@93%,1@100%,1@105%+ (new PR attempt)", [
            s(1,reps=5,pct=50), s(2,reps=3,pct=65), s(3,reps=2,pct=75), s(4,reps=1,pct=85),
            s(5,reps=1,pct=93), s(6,reps=1,pct=100), s(7,reps=1,pct=105),
        ]),
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # PPSA 70s BIG
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n── PPSA 70s BIG ──")

    create(token, "70s Big Day 1 – Bench Wave + Upper Accessories", "PPSA 70s Big • Day 1", [
        ex(E["bench"], 1, "7-set wave: 5@65%,4@70%,3@75%,2@80%,3@75%,4@70%,5@65%", [
            s(1,reps=5,pct=65), s(2,reps=4,pct=70), s(3,reps=3,pct=75), s(4,reps=2,pct=80),
            s(5,reps=3,pct=75), s(6,reps=4,pct=70), s(7,reps=5,pct=65),
        ]),
        ex(E["incline"], 2, "4x10 DB Incline Press — superset with BB Bent Over Rows 4x10", [s(i+1,reps=10) for i in range(4)]),
        ex(E["bent_row"], 3, "4x10 — superset with DB Incline Press", [s(i+1,reps=10) for i in range(4)]),
        ex(E["skull"], 4, "EZ Bar Skullcrushers — superset with Tricep Pushdowns", [s(i+1,reps=10) for i in range(3)]),
        ex(E["pushdown"], 5, "Tricep Pushdowns — superset with Skullcrushers", [s(i+1,reps=12) for i in range(3)]),
    ])

    create(token, "70s Big Day 2 – Squat Volume + RDLs", "PPSA 70s Big • Day 2", [
        ex(E["back_squat"], 1, "12 sets ascending @50-80%", [
            s(1,reps=5,pct=50), s(2,reps=5,pct=55), s(3,reps=5,pct=60), s(4,reps=5,pct=65),
            s(5,reps=4,pct=68), s(6,reps=4,pct=70), s(7,reps=3,pct=73), s(8,reps=3,pct=75),
            s(9,reps=3,pct=77), s(10,reps=3,pct=78), s(11,reps=2,pct=80), s(12,reps=2,pct=80),
        ]),
        ex(E["rdl"], 2, "5x5 BB RDLs — superset with Heavy Alt DB Curls 5x5", [s(i+1,reps=5) for i in range(5)]),
        ex(E["curl"], 3, "5x5 Heavy Alt DB Curls — superset with RDLs", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 3 – Big Ole Back", "PPSA 70s Big • Day 3 • back focus", [
        ex(E["chinup"], 1, "6x2-5 Slow Strict Chin Ups", [s(i+1,reps=4) for i in range(6)]),
        ex(E["incline"], 2, "3x8 DB Pullover (Incline slot) — superset with BB Bent Over Rows 3x8", [s(i+1,reps=8) for i in range(3)]),
        ex(E["bent_row"], 3, "3x8 — superset with DB Pullover", [s(i+1,reps=8) for i in range(3)]),
        ex(E["curl"], 4, "5x5 Heavy BB Bicep Curls", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 4 – Upper Push Supersets", "PPSA 70s Big • Day 4", [
        ex(E["incline"], 1, "DB Incline Press — superset with DB Rear Lateral Raises", [s(1,reps=10), s(2,reps=8), s(3,reps=6), s(4,reps=6), s(5,reps=8)]),
        ex(E["rear_delt"], 2, "DB Rear Lateral Raises — superset with DB Incline Press", [s(i+1,reps=15) for i in range(5)]),
        ex(E["cgbench"], 3, "Close Grip Bench — superset with DB Lateral Raises", [s(i+1,reps=8) for i in range(4)]),
        ex(E["lateral"], 4, "DB Lateral Raises — superset with Close Grip Bench", [s(i+1,reps=15) for i in range(4)]),
    ])

    create(token, "70s Big Day 5 – Deadlift + Split Squats", "PPSA 70s Big • Day 5", [
        ex(E["deadlift"], 1, "3x5@70%, 3x4@75%, 3x3@80-85%", [
            s(1,reps=5,pct=70), s(2,reps=5,pct=70), s(3,reps=5,pct=70),
            s(4,reps=4,pct=75), s(5,reps=4,pct=75), s(6,reps=4,pct=75),
            s(7,reps=3,pct=82), s(8,reps=3,pct=84), s(9,reps=3,pct=85),
        ]),
        ex(E["bss"], 2, "6 sets DB Bulgarian Split Squats", [s(i+1,reps=6) for i in range(6)]),
    ])

    create(token, "70s Big Day 6 – Bench 10x10 + Volume Upper", "PPSA 70s Big • Day 6 • German Volume Training style", [
        ex(E["bench"], 1, "10x10@50-57% — superset with KB Swings 10x10", [s(i+1,reps=10,pct=53) for i in range(10)]),
        ex(E["kb_swing"], 2, "10x10 KB Swings — superset with Bench Press", [s(i+1,reps=10) for i in range(10)]),
        ex(E["incline"], 3, "8x5 DB Incline Press — superset with DB Rear Laterals 8x15", [s(i+1,reps=5) for i in range(8)]),
        ex(E["rear_delt"], 4, "8x15 DB Rear Laterals — superset with DB Incline Press", [s(i+1,reps=15) for i in range(8)]),
    ])

    create(token, "70s Big Day 7 – Back Attack", "PPSA 70s Big • Day 7", [
        ex(E["chinup"], 1, "4x3-5 Slow Strict — superset with 1 Arm DB Rows 4x5", [s(i+1,reps=4) for i in range(4)]),
        ex(E["db_row"], 2, "4x5 1 Arm DB Rows — superset with Chin Ups", [s(i+1,reps=5) for i in range(4)]),
        ex(E["bent_row"], 3, "5x5 BB Bent Over Rows — superset with Reverse Grip BB Rows 5x5", [s(i+1,reps=5) for i in range(5)]),
        ex(E["bent_row"], 4, "5x5 Reverse Grip BB Rows (reverse grip)", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 8 – Squat + Lunges", "PPSA 70s Big • Day 8", [
        ex(E["back_squat"], 1, "5@70%,5@73%,5@75%,5@80%,5@80%", [
            s(1,reps=5,pct=70), s(2,reps=5,pct=73), s(3,reps=5,pct=75), s(4,reps=5,pct=80), s(5,reps=5,pct=80),
        ]),
        ex(E["lunge"], 2, "5x5 DB Reverse Lunges (per leg)", [s(i+1,reps=10) for i in range(5)]),
        ex(E["back_squat"], 3, "3x10@52% — back off sets", [s(i+1,reps=10,pct=52) for i in range(3)]),
    ])

    create(token, "70s Big Day 9 – Density Protocol", "PPSA 70s Big • Day 9 • 17-set bench wave + pump work", [
        ex(E["bench"], 1, "17-set wave: build to ~87% then descend with increasing reps", [
            s(1,reps=5,pct=60), s(2,reps=4,pct=65), s(3,reps=3,pct=70), s(4,reps=2,pct=75),
            s(5,reps=1,pct=82), s(6,reps=1,pct=85), s(7,reps=1,pct=87),
            s(8,reps=2,pct=82), s(9,reps=3,pct=77), s(10,reps=4,pct=72), s(11,reps=5,pct=67),
            s(12,reps=5,pct=63), s(13,reps=6,pct=60), s(14,reps=7,pct=58),
            s(15,reps=8,pct=55), s(16,reps=9,pct=52), s(17,reps=10,pct=50),
        ]),
        ex(E["pushdown"], 2, "10x20 Tricep Pushdowns — superset with DB Lateral Raises 10x20", [s(i+1,reps=20) for i in range(10)]),
        ex(E["lateral"], 3, "10x20 DB Lateral Raises — superset with Pushdowns", [s(i+1,reps=20) for i in range(10)]),
    ])

    create(token, "70s Big Day 10 – Deadlift + Pull Volume", "PPSA 70s Big • Day 10", [
        ex(E["deadlift"], 1, "3x5@70%, 5x3@80%", [
            s(1,reps=5,pct=70), s(2,reps=5,pct=70), s(3,reps=5,pct=70),
            s(4,reps=3,pct=80), s(5,reps=3,pct=80), s(6,reps=3,pct=80), s(7,reps=3,pct=80), s(8,reps=3,pct=80),
        ]),
        ex(E["chinup"], 2, "10x3-5 Slow Strict Chin Ups", [s(i+1,reps=4) for i in range(10)]),
        ex(E["db_row"], 3, "5x5 1 Arm DB Rows", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 11 – Legs like Kegs", "PPSA 70s Big • Day 11 • massive squat volume", [
        ex(E["back_squat"], 1, "14-set wave: build to 80% then descend", [
            s(1,reps=5,pct=50), s(2,reps=5,pct=55), s(3,reps=5,pct=60), s(4,reps=4,pct=65),
            s(5,reps=4,pct=68), s(6,reps=3,pct=70), s(7,reps=3,pct=73), s(8,reps=3,pct=75),
            s(9,reps=2,pct=78), s(10,reps=2,pct=80),
            s(11,reps=3,pct=75), s(12,reps=4,pct=70), s(13,reps=5,pct=65), s(14,reps=5,pct=60),
        ]),
        ex(E["rdl"], 2, "10x10 DB RDLs", [s(i+1,reps=10) for i in range(10)]),
        ex(E["curl"], 3, "5x5 Heavy BB Bicep Curls", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 12 – Bench Volume + Shoulder Press", "PPSA 70s Big • Day 12", [
        ex(E["bench"], 1, "5x10@57%", [s(i+1,reps=10,pct=57) for i in range(5)]),
        ex(E["incline"], 2, "5x5 DB Incline Press", [s(i+1,reps=5) for i in range(5)]),
        ex(E["bench"], 3, "3x15@58% — back off sets", [s(i+1,reps=15,pct=58) for i in range(3)]),
        ex(E["seated_press"], 4, "Seated DB Shoulder Press — superset with DB Lateral Raises", [s(i+1,reps=10) for i in range(4)]),
        ex(E["lateral"], 5, "DB Lateral Raises — superset with Seated DB Shoulder Press", [s(i+1,reps=15) for i in range(4)]),
    ])

    create(token, "70s Big Day 13 – Big Back Day", "PPSA 70s Big • Day 13", [
        ex(E["bent_row"], 1, "5x10 BB Bent Over Rows", [s(i+1,reps=10) for i in range(5)]),
        ex(E["chinup"], 2, "4x3-5 Slow Strict Chin Ups", [s(i+1,reps=4) for i in range(4)]),
        ex(E["bent_row"], 3, "5x5 Reverse Grip BB Rows (reverse grip)", [s(i+1,reps=5) for i in range(5)]),
        ex(E["curl"], 4, "BB Bicep Curls — superset with DB Rear Laterals", [s(i+1,reps=10) for i in range(4)]),
        ex(E["rear_delt"], 5, "DB Rear Lateral Raises — superset with BB Bicep Curls", [s(i+1,reps=15) for i in range(4)]),
    ])

    create(token, "70s Big Day 14 – OHP + Squat Supersets", "PPSA 70s Big • Day 14", [
        ex(E["ohp"], 1, "BB Standing OHP — superset with DB Bulgarian Split Squats", [s(i+1,reps=5) for i in range(4)]),
        ex(E["bss"], 2, "DB Bulgarian Split Squats — superset with BB OHP", [s(i+1,reps=6) for i in range(4)]),
        ex(E["back_squat"], 3, "4x5@70% — superset with Seated DB Arnold Press", [s(i+1,reps=5,pct=70) for i in range(4)]),
        ex(E["arnold"], 4, "Seated DB Arnold Press — superset with Back Squat", [s(i+1,reps=10) for i in range(4)]),
        ex(E["lunge"], 5, "DB Alt Reverse Lunges — superset with DB Lateral Raises", [s(i+1,reps=10) for i in range(3)]),
        ex(E["lateral"], 6, "DB Lateral Raises — superset with Reverse Lunges", [s(i+1,reps=15) for i in range(3)]),
    ])

    create(token, "70s Big Day 15 – Big Back Assault", "PPSA 70s Big • Day 15 • heavy deadlift + back", [
        ex(E["deadlift"], 1, "3x3@75%, 3x2@85%, 3x1@92%, 3x5@75%", [
            s(1,reps=3,pct=75), s(2,reps=3,pct=75), s(3,reps=3,pct=75),
            s(4,reps=2,pct=85), s(5,reps=2,pct=85), s(6,reps=2,pct=85),
            s(7,reps=1,pct=92), s(8,reps=1,pct=92), s(9,reps=1,pct=92),
            s(10,reps=5,pct=75), s(11,reps=5,pct=75), s(12,reps=5,pct=75),
        ]),
        ex(E["incline"], 2, "DB Pullovers (Incline slot) — superset with 1 Arm DB Rows", [s(i+1,reps=10) for i in range(4)]),
        ex(E["db_row"], 3, "1 Arm DB Rows — superset with DB Pullovers", [s(i+1,reps=5) for i in range(4)]),
        ex(E["curl"], 4, "5x5 Heavy BB Bicep Curls", [s(i+1,reps=5) for i in range(5)]),
    ])

    create(token, "70s Big Day 16 – Bench Wave 16 Sets + Triceps", "PPSA 70s Big • Day 16", [
        ex(E["bench"], 1, "16-set wave: build to ~88% then descend with increasing reps", [
            s(1,reps=5,pct=60), s(2,reps=4,pct=65), s(3,reps=3,pct=70), s(4,reps=2,pct=75),
            s(5,reps=1,pct=82), s(6,reps=1,pct=85), s(7,reps=1,pct=88),
            s(8,reps=2,pct=82), s(9,reps=3,pct=77), s(10,reps=4,pct=72),
            s(11,reps=5,pct=67), s(12,reps=5,pct=63), s(13,reps=6,pct=60),
            s(14,reps=7,pct=57), s(15,reps=8,pct=54), s(16,reps=9,pct=50),
        ]),
        ex(E["kickback"], 2, "6x15 DB Tricep Kickbacks", [s(i+1,reps=15) for i in range(6)]),
    ])

    create(token, "70s Big Day 17 – Squat + Split Squats", "PPSA 70s Big • Day 17", [
        ex(E["back_squat"], 1, "10 sets ascending @50-65%", [
            s(1,reps=5,pct=50), s(2,reps=5,pct=52), s(3,reps=5,pct=54), s(4,reps=5,pct=56),
            s(5,reps=5,pct=58), s(6,reps=4,pct=60), s(7,reps=4,pct=62),
            s(8,reps=4,pct=63), s(9,reps=4,pct=64), s(10,reps=4,pct=65),
        ]),
        ex(E["bss"], 2, "4x5 DB Bulgarian Split Squats (per leg)", [s(i+1,reps=5) for i in range(4)]),
    ])

    create(token, "70s Big Day 18 – Chin Ups + Rows + Curls", "PPSA 70s Big • Day 18", [
        ex(E["chinup"], 1, "Slow Strict Chin Ups — superset with BB Bent Over Rows", [s(i+1,reps=4) for i in range(5)]),
        ex(E["bent_row"], 2, "BB Bent Over Rows — superset with Chin Ups", [s(i+1,reps=8) for i in range(5)]),
        ex(E["db_row"], 3, "3 sets 1 Arm DB Rows", [s(i+1,reps=8) for i in range(3)]),
        ex(E["curl"], 4, "4 sets BB Bicep 21s (7 bottom half + 7 top half + 7 full reps)", [s(i+1,reps=21) for i in range(4)]),
    ])

    create(token, "70s Big Day 19 – OHP + Shoulder Superset", "PPSA 70s Big • Day 19", [
        ex(E["ohp"], 1, "9-set BB OHP wave: 5,4,3,2,1,2,3,4,5", [
            s(1,reps=5), s(2,reps=4), s(3,reps=3), s(4,reps=2), s(5,reps=1),
            s(6,reps=2), s(7,reps=3), s(8,reps=4), s(9,reps=5),
        ]),
        ex(E["lateral"], 2, "DB Lateral Raises — triple superset 10x15", [s(i+1,reps=15) for i in range(10)]),
        ex(E["rear_delt"], 3, "DB Rear Lateral Raises — triple superset 10x15", [s(i+1,reps=15) for i in range(10)]),
        ex(E["pushdown"], 4, "Tricep Pushdowns — superset with Close Grip Push-ups", [s(i+1,reps=15) for i in range(4)]),
        ex(E["pushup"], 5, "Close Grip Push-ups — superset with Tricep Pushdowns", [s(i+1,reps=12) for i in range(4)]),
    ])

    create(token, "70s Big Day 20 – Heavy Deadlift + Chin Ups", "PPSA 70s Big • Day 20 • final day", [
        ex(E["deadlift"], 1, "3x4@75%, 3x3@85%, 3x2@90%", [
            s(1,reps=4,pct=75), s(2,reps=4,pct=75), s(3,reps=4,pct=75),
            s(4,reps=3,pct=85), s(5,reps=3,pct=85), s(6,reps=3,pct=85),
            s(7,reps=2,pct=90), s(8,reps=2,pct=90), s(9,reps=2,pct=90),
        ]),
        ex(E["chinup"], 2, "10x3-5 Slow Strict Chin Ups", [s(i+1,reps=4) for i in range(10)]),
        ex(E["rdl"], 3, "5x5 Heavy BB RDLs", [s(i+1,reps=5) for i in range(5)]),
    ])

    print("\nDone. 22 Squatober + 20 70s Big = 42 templates created.")


if __name__ == "__main__":
    main()
