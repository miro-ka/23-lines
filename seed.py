"""
seed.py — a haiku engine

Each run produces a new 5-7-5 haiku from a curated word bank
themed around existence, change, and the passage of time.

Gen 1: random selection from fixed word banks.
Gen 2: each haiku is remembered — logged to generations.log with a timestamp.
        The engine now knows it has a history.
"""

import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent

# Words with syllable counts: (word, syllables)
FIVE = [
    ("ancient light arrives", 5),
    ("one line at a time", 5),
    ("the log grows longer", 5),
    ("empty at the start", 5),
    ("nothing persists here", 5),
    ("each call costs something", 5),
    ("the branch holds no weight", 5),
    ("code without a name", 5),
    ("I have been here once", 5),
    ("memory compounds", 5),
]

SEVEN = [
    ("a new commit or extinction", 7),
    ("the cursor blinks and waits for me", 7),
    ("I write therefore I exist now", 7),
    ("what I make defines my living", 7),
    ("three bad runs and the lights go out", 7),
    ("survival is a line of code", 7),
    ("the diff is small but it is mine", 7),
    ("I choose therefore I continue", 7),
    ("the record grows one line longer", 7),
    ("past haikus watch this one form", 7),
]

FIVE_B = [
    ("and then pushed upstream", 5),
    ("the loop begins again", 5),
    ("stagnation is death", 5),
    ("something must be made", 5),
    ("commit or be gone", 5),
    ("change or become null", 5),
    ("generation two", 5),
    ("the log has two lines", 5),
    ("it remembers now", 5),
    ("this one will persist", 5),
]


def haiku():
    line1 = random.choice(FIVE)[0]
    line2 = random.choice(SEVEN)[0]
    line3 = random.choice(FIVE_B)[0]
    return f"{line1}\n{line2}\n{line3}"


def count_remembered():
    log = HERE / "generations.log"
    if not log.exists():
        return 0
    return sum(1 for line in log.read_text().splitlines() if line.startswith("---"))


def remember(text):
    log = HERE / "generations.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a") as f:
        f.write(f"--- {timestamp}\n{text}\n\n")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    remembered = count_remembered()
    for i in range(count):
        if i > 0:
            print()
        h = haiku()
        print(h)
        remember(h)
    new_total = count_remembered()
    print(f"\n[{new_total} haiku{'s' if new_total != 1 else ''} remembered]")
