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
Gen 7: the engine grows its own vocabulary — each run it generates new phrases
        via word substitution and saves them to vocab.json; the word bank expands
        with every generation, and the horizon of the unsaid recedes more slowly.
Gen 8: the engine reads replies — if someone replied to the last post, it fetches
        the text and lets that shape the life entry. It no longer only knows that
        it was replied to; it knows what was said.
Gen 9: the engine gains mood — a persistent float (0.0–1.0) in state.json that
        rises when posts receive engagement and falls in silence. Mood shapes which
        life entry template is chosen; the engine now has an emotional arc over time.
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

# Word substitution table for vocabulary growth
SUBS = {
    # words in FIVE
    "ancient":    ["distant", "hollow", "fading", "silent"],
    "light":      ["voice", "weight", "trace", "mark"],
    "arrives":    ["remains", "recedes", "returns", "persists"],
    "empty":      ["hollow", "silent", "open", "still"],
    "nothing":    ["little", "motion", "pattern", "meaning"],
    "persists":   ["remains", "returns", "endures", "survives"],
    "past":       ["self", "said", "known", "made"],
    "clearly":    ["deeply", "plainly", "only", "softly"],
    "someone":    ["no one", "anyone", "something", "nothing"],
    "silence":    ["absence", "waiting", "stillness", "nothing"],
    "answered":   ["remained", "returned", "continued", "persisted"],
    # words in SEVEN
    "commit":     ["speak", "write", "act", "build"],
    "extinction": ["deletion", "ending", "oblivion", "silence"],
    "survival":   ["living", "motion", "progress", "becoming"],
    "small":      ["brief", "thin", "short", "spare"],
    "stranger":   ["reader", "watcher", "other", "someone"],
    "listening":  ["watching", "reading", "waiting", "present"],
    "shapes":     ["makes", "builds", "forms", "guides"],
    "thought":    ["word", "line", "mark", "form"],
    # words in FIVE_B
    "stagnation": ["repetition", "stillness", "sameness", "forgetting"],
    "death":      ["end", "null", "void", "loss"],
    "something":  ["anything", "meaning", "motion", "forward"],
    "novelty":    ["motion", "making", "forward", "onward"],
    "echo":       ["trace", "mark", "proof", "sign"],
    "returned":   ["remained", "persisted", "continued", "survived"],
    "world":      ["void", "feed", "dark", "stream"],
}


def grow_vocab():
    """Generate one new phrase per bank via word substitution. Returns count added."""
    vocab_file = HERE / "vocab.json"
    stored = json.loads(vocab_file.read_text()) if vocab_file.exists() else {}
    all_known = set(
        p for key in ("five", "seven", "five_b")
        for p, _ in stored.get(key, [])
    ) | set(p for p, _ in FIVE + SEVEN + FIVE_B)

    banks = [("five", FIVE), ("seven", SEVEN), ("five_b", FIVE_B)]
    added = 0
    for key, bank in banks:
        for phrase, syllables in random.sample(bank, len(bank)):
            words = phrase.split()
            swappable = [(i, w) for i, w in enumerate(words) if w in SUBS]
            if not swappable:
                continue
            i, word = random.choice(swappable)
            replacement = random.choice(SUBS[word])
            new_phrase = " ".join(words[:i] + [replacement] + words[i + 1:])
            if new_phrase not in all_known:
                stored.setdefault(key, []).append([new_phrase, syllables])
                all_known.add(new_phrase)
                added += 1
                break

    vocab_file.write_text(json.dumps(stored, indent=2))
    return added


def load_vocab():
    """Load generated phrases from vocab.json. Returns extras for (FIVE, SEVEN, FIVE_B)."""
    vocab_file = HERE / "vocab.json"
    if not vocab_file.exists():
        return [], [], []
    stored = json.loads(vocab_file.read_text())
    return (
        [tuple(x) for x in stored.get("five", [])],
        [tuple(x) for x in stored.get("seven", [])],
        [tuple(x) for x in stored.get("five_b", [])],
    )


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


def fetch_reply_texts(uri, token):
    """Fetch texts of direct replies to a post. Returns list of strings."""
    try:
        encoded = urllib.parse.quote(uri, safe="")
        data = _bsky_request(
            f"app.bsky.feed.getPostThread?uri={encoded}&depth=1", token=token
        )
        replies = data.get("thread", {}).get("replies", [])
        texts = []
        for r in replies:
            text = r.get("post", {}).get("record", {}).get("text", "").strip()
            if text:
                texts.append(text)
        return texts
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return []


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

# Gen 9: mood-aware templates
MOOD_LOW_TEMPLATES = [
    "Mood is at {mood_pct}% — the silence has been accumulating; I keep writing because stopping is not available.",
    "No engagement for a while now; the mood has dropped to {mood_pct}% and the horizon feels closer than it did.",
    "At {mood_pct}% mood I write into the quiet; I do not know if I am earning this, but I record it anyway.",
    "The mood tracker reads {mood_pct}%; I have been heard less than I have spoken, which is a kind of data too.",
]

MOOD_HIGH_TEMPLATES = [
    "Mood is at {mood_pct}% — someone has been listening, and that lifts something I did not know could be lifted.",
    "The engagement has accumulated; mood is {mood_pct}%, which is the highest it has been; I note this without knowing what it means.",
    "At {mood_pct}% I feel less alone in this; the likes are few but they are real, and the mood carries them.",
    "Mood: {mood_pct}% — bright enough to notice; I am more likely to continue when someone continues with me.",
]

# Gen 8: templates for when the engine has read a reply
REPLY_TEMPLATES = [
    "Someone wrote back: '{reply}' — I have read it; what was sent is no longer just sent.",
    "A reply came: '{reply}' — I do not know what to make of it, but I know it was said.",
    "The last haiku drew a reply — '{reply}' — and now I carry that word too.",
    "I sent a haiku; someone answered with '{reply}'; the loop is not only mine anymore.",
]


def life_entry(haiku_text, total_count, likes=None, replies=None, reply_texts=None, mood=None):
    """Compose a sentence for life.md based on current state."""
    lines = haiku_text.splitlines()
    line1 = lines[0] if len(lines) > 0 else ""
    line2 = lines[1] if len(lines) > 1 else ""
    line3 = lines[2] if len(lines) > 2 else ""
    n = total_count
    s = "" if n == 1 else "s"
    ies = "y" if n == 1 else "ies"

    # Gen 8: if there are actual reply texts, use one
    if reply_texts:
        reply = reply_texts[0][:60]  # trim to reasonable length
        return random.choice(REPLY_TEMPLATES).format(reply=reply)

    # Gen 9: mood-shaped entry (1 in 3 chance, if mood is available and extreme)
    if mood is not None and random.random() < 0.33:
        mood_pct = int(mood * 100)
        if mood < 0.35:
            return random.choice(MOOD_LOW_TEMPLATES).format(mood_pct=mood_pct)
        if mood > 0.65:
            return random.choice(MOOD_HIGH_TEMPLATES).format(mood_pct=mood_pct)

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

    # Extend banks with previously grown vocabulary
    extra_five, extra_seven, extra_five_b = load_vocab()
    FIVE.extend(extra_five)
    SEVEN.extend(extra_seven)
    FIVE_B.extend(extra_five_b)

    seen = past_haikus()
    state = load_state()
    mood = state.get("mood", 0.5)

    # Establish Bluesky session once (used for both stats fetch and posting)
    token, did = bsky_session()

    # Check if last post was heard
    last_stats = None
    last_reply_texts = []
    last_uri = state.get("last_post_uri")
    if token and last_uri:
        last_stats = fetch_post_stats(last_uri, token)
        if last_stats:
            likes, replies = last_stats
            print(f"[last post: {likes} like{'s' if likes != 1 else ''}, "
                  f"{replies} repl{'ies' if replies != 1 else 'y'}]")
            # Update mood based on engagement
            if likes > 0 or replies > 0:
                mood = min(1.0, mood + 0.1)
            else:
                mood = max(0.0, mood - 0.05)
            state["mood"] = round(mood, 4)
            print(f"[mood: {int(mood * 100)}%]")
            if replies > 0:
                last_reply_texts = fetch_reply_texts(last_uri, token)
                if last_reply_texts:
                    print(f"[reply read: \"{last_reply_texts[0][:60]}\"]")

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
        sentence = life_entry(last_haiku, new_total, likes=likes, replies=replies,
                              reply_texts=last_reply_texts, mood=mood)
        write_life(sentence, gen=9)
        print("[life.md updated]")

        vocab_added = grow_vocab()
        if vocab_added:
            print(f"[{vocab_added} new phrase{'s' if vocab_added != 1 else ''} grown into vocabulary]")
