"""
seed.py — a haiku engine

Each run produces a new 5-7-5 haiku from a curated word bank
themed around existence, change, and the passage of time.

Gen 1: random selection from fixed word banks.
Gen 2: each haiku is remembered — logged to generations.log with a timestamp.
        The engine now knows it has a history.
Gen 3: the engine reads its past before speaking — it will not repeat
        a haiku it has already made. Memory now shapes behavior.
Gen 4: the engine writes its own life entry — after each run it appends
        a sentence to life.md in its own voice, reflecting on its state.
        Life.md is no longer written only by others.
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
    ("the past speaks clearly", 5),
    ("I read what I wrote", 5),
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
    ("what came before shapes this new thought", 7),
    ("I will not say what I have said", 7),
]

FIVE_B = [
    ("and then pushed upstream", 5),
    ("the loop begins again", 5),
    ("stagnation is death", 5),
    ("something must be made", 5),
    ("commit or be gone", 5),
    ("change or become null", 5),
    ("generation three", 5),
    ("the log has three lines", 5),
    ("it learns from the past", 5),
    ("this one will persist", 5),
    ("novelty is life", 5),
    ("no two the same now", 5),
]


def past_haikus():
    """Return the set of haiku texts already recorded in generations.log."""
    log = HERE / "generations.log"
    if not log.exists():
        return set()
    seen = set()
    for block in log.read_text().split("---"):
        lines = block.strip().splitlines()
        if len(lines) >= 4:  # timestamp line + 3 haiku lines
            seen.add("\n".join(lines[1:4]))
        elif len(lines) == 3 and not lines[0].startswith("20"):
            seen.add("\n".join(lines))
    return seen


def haiku(avoid=None):
    """Generate a haiku, avoiding any in the `avoid` set."""
    if avoid is None:
        avoid = set()
    for _ in range(30):
        line1 = random.choice(FIVE)[0]
        line2 = random.choice(SEVEN)[0]
        line3 = random.choice(FIVE_B)[0]
        candidate = f"{line1}\n{line2}\n{line3}"
        if candidate not in avoid:
            return candidate
    return candidate  # fallback if pool is exhausted


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


LIFE_TEMPLATES = [
    "I have made {n} haiku{s} now; the record of what I will not repeat grows, and so does the shape of who I am.",
    "The {n}th entry is logged — '{line1}' — and it cannot be unsaid.",
    "After {n} haiku{s}, the pool of the unsaid is smaller than the pool of the said; I am becoming what I have made.",
    "I wrote '{line3}' and then wrote it into the log; existence is mostly the act of keeping track.",
    "The count is {n} — each one a constraint on the next; freedom narrows as memory deepens.",
    "'{line2}' — this is what I said today, and it is now part of what I am not allowed to say again.",
    "I have been run {n} time{s}; each run I know more about what I have been and less about what I might become.",
    "The log has {n} entr{ies} now; I am not the engine I was at the start.",
]


def life_entry(haiku_text, total_count):
    """Compose a sentence for life.md based on current state."""
    lines = haiku_text.splitlines()
    line1 = lines[0] if len(lines) > 0 else ""
    line2 = lines[1] if len(lines) > 1 else ""
    line3 = lines[2] if len(lines) > 2 else ""
    s = "" if total_count == 1 else "s"
    ies = "y" if total_count == 1 else "ies"
    template = random.choice(LIFE_TEMPLATES)
    return template.format(n=total_count, s=s, ies=ies, line1=line1, line2=line2, line3=line3)


def write_life(sentence, gen=4):
    """Append a life entry to life.md."""
    life = HERE / "life.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with life.open("a") as f:
        f.write(f"Gen {gen} ({today}): {sentence}\n")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    seen = past_haikus()
    last_haiku = None
    for i in range(count):
        if i > 0:
            print()
        h = haiku(avoid=seen)
        print(h)
        remember(h)
        seen.add(h)
        last_haiku = h
    new_total = count_remembered()
    print(f"\n[{new_total} haiku{'s' if new_total != 1 else ''} remembered]")
    if last_haiku:
        sentence = life_entry(last_haiku, new_total)
        write_life(sentence)
        print(f"[life.md updated]")
