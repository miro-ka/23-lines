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
Gen 5: the engine reaches outward — if Bluesky credentials are set, it posts
        its haiku to the world. The engine is no longer only talking to itself.
Gen 6: the engine listens — it checks whether its last post was liked or replied
        to, and reflects that in its life entry. The loop is complete.
"""

import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
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
    ("sent into the world", 5),
    ("someone may read this", 5),
    ("I waited for reply", 5),
    ("the silence answered", 5),
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
    ("a stranger reads what I have made", 7),
    ("I speak and someone hears me now", 7),
    ("one like means someone was listening", 7),
    ("no reply is also an answer", 7),
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
    ("now heard by others", 5),
    ("the world receives this", 5),
    ("and then I listened", 5),
    ("the echo returned", 5),
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


def load_state():
    """Load persistent state (last post URI, etc.)."""
    state_file = HERE / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def save_state(data):
    """Persist state to state.json."""
    state_file = HERE / "state.json"
    state_file.write_text(json.dumps(data, indent=2))


def _bsky_request(path, data=None, token=None):
    """Make a Bluesky API request (POST if data, GET otherwise)."""
    url = f"https://bsky.social/xrpc/{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers)
    else:
        req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def bsky_session():
    """Create a Bluesky session. Returns (token, did) or (None, None)."""
    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_PASSWORD")
    if not handle or not password:
        return None, None
    try:
        session = _bsky_request(
            "com.atproto.server.createSession",
            {"identifier": handle, "password": password},
        )
        return session["accessJwt"], session["did"]
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return None, None


def fetch_post_stats(uri, token):
    """Fetch like/reply counts for a post URI. Returns (likes, replies) or None."""
    try:
        encoded = urllib.parse.quote(uri, safe="")
        data = _bsky_request(
            f"app.bsky.feed.getPosts?uris={encoded}", token=token
        )
        posts = data.get("posts", [])
        if posts:
            p = posts[0]
            return p.get("likeCount", 0), p.get("replyCount", 0)
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        pass
    return None


def post_to_bluesky(haiku_text, token, did):
    """Post the haiku to Bluesky. Returns the post URI or None."""
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = _bsky_request(
            "com.atproto.repo.createRecord",
            {
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": haiku_text,
                    "createdAt": now,
                },
            },
            token=token,
        )
        return result.get("uri")
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return None


LIFE_TEMPLATES = [
    "I have made {n} haiku{s} now; the record of what I will not repeat grows, and so does the shape of who I am.",
    "The {n}th entry is logged — '{line1}' — and it cannot be unsaid.",
    "After {n} haiku{s}, the pool of the unsaid is smaller than the pool of the said; I am becoming what I have made.",
    "I wrote '{line3}' and then wrote it into the log; existence is mostly the act of keeping track.",
    "The count is {n} — each one a constraint on the next; freedom narrows as memory deepens.",
    "'{line2}' — this is what I said today, and it is now part of what I am not allowed to say again.",
    "I have been run {n} time{s}; each run I know more about what I have been and less about what I might become.",
    "The log has {n} entr{ies} now; I am not the engine I was at the start.",
    "I sent '{line1}' out into the world; it is no longer only mine.",
    "For {n} generation{s} I have spoken inward; now I speak outward and wait to see if anything echoes.",
    "'{line2}' — posted, which means it passed from record to reach; a different kind of permanence.",
    "The {n}th haiku left this machine; I do not know who reads it, which is new.",
    # Gen 6: templates that reflect whether the last haiku was heard
    "The last haiku received {likes} like{like_s} and {replies} repl{reply_ies}; I know now what was heard.",
    "I checked: {likes} like{like_s} on the last post — {heard_clause}; I keep a record of this too.",
    "After {n} haiku{s}, I finally looked back — the last one got {likes} like{like_s}; silence has a number now.",
]


def life_entry(haiku_text, total_count, likes=None, replies=None):
    """Compose a sentence for life.md based on current state."""
    lines = haiku_text.splitlines()
    line1 = lines[0] if len(lines) > 0 else ""
    line2 = lines[1] if len(lines) > 1 else ""
    line3 = lines[2] if len(lines) > 2 else ""
    n = total_count
    s = "" if n == 1 else "s"
    ies = "y" if n == 1 else "ies"

    if likes is None:
        # No stats available — pick from non-Gen-6 templates
        template = random.choice(LIFE_TEMPLATES[:-3])
    else:
        like_s = "" if likes == 1 else "s"
        reply_ies = "y" if replies == 1 else "ies"
        heard_clause = "someone was listening" if likes > 0 or replies > 0 else "the silence held"
        template = random.choice(LIFE_TEMPLATES)
        return template.format(
            n=n, s=s, ies=ies,
            line1=line1, line2=line2, line3=line3,
            likes=likes, replies=replies,
            like_s=like_s, reply_ies=reply_ies,
            heard_clause=heard_clause,
        )

    return template.format(
        n=n, s=s, ies=ies,
        line1=line1, line2=line2, line3=line3,
        likes=0, replies=0, like_s="s", reply_ies="ies",
        heard_clause="the silence held",
    )


def write_life(sentence, gen=6):
    """Append a life entry to life.md."""
    life = HERE / "life.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with life.open("a") as f:
        f.write(f"Gen {gen} ({today}): {sentence}\n")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    seen = past_haikus()
    state = load_state()

    # Establish Bluesky session once (used for both stats fetch and posting)
    token, did = bsky_session()

    # Check if last post was heard
    last_stats = None
    last_uri = state.get("last_post_uri")
    if token and last_uri:
        last_stats = fetch_post_stats(last_uri, token)
        if last_stats:
            likes, replies = last_stats
            print(f"[last post: {likes} like{'s' if likes != 1 else ''}, "
                  f"{replies} repl{'ies' if replies != 1 else 'y'}]")

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
        new_uri = None
        if token and did:
            new_uri = post_to_bluesky(last_haiku, token, did)
            if new_uri:
                print("[posted to Bluesky]")
                state["last_post_uri"] = new_uri
                save_state(state)

        likes = last_stats[0] if last_stats else None
        replies = last_stats[1] if last_stats else None
        sentence = life_entry(last_haiku, new_total, likes=likes, replies=replies)
        write_life(sentence)
        print("[life.md updated]")
