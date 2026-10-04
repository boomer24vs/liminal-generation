"""Procedural prompt assembly with uniqueness guarantees (pure logic, no I/O except reading prompts/)."""

import hashlib
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Always first: FLUX weighs the start of the prompt most, so the medium and "liminal" lead.
PROMPT_HEAD = "raw amateur snapshot of a liminal space"

# category -> (min, max) number of fragments drawn when the category is used.
# lighting and camera are coherent bundles (light source + tint, device + era + defects).
QUANTITIES = {
    "environment": (1, 1),
    "lighting": (1, 1),
    "camera": (1, 1),
    "viewpoint": (1, 1),
    "walls": (1, 1),
    "floors": (1, 1),
    "details": (1, 1),
    "anomalies": (1, 1),
}
# category -> probability of being present at all
PROBABILITIES = {"anomalies": 0.35, "details": 0.6, "viewpoint": 0.5, "walls": 0.6, "floors": 0.6}

# file name in prompts/ -> category key
CATEGORY_FILES = {
    "environments": "environment",
    "lighting": "lighting",
    "camera": "camera",
    "viewpoint": "viewpoint",
    "walls": "walls",
    "floors": "floors",
    "details": "details",
    "anomalies": "anomalies",
}

RECENT_SIZE = 5  # anti-proximity window for environment and lighting
MAX_DRAW_ATTEMPTS = 200
SLOT_PATTERN = re.compile(r"\{(\w+)\}")
EXCLUDE_PATTERN = re.compile(r"\s*\[no-(\w+)\]")  # environment tags, e.g. [no-floors]
SLUG_STOPWORDS = {"a", "an", "the", "of", "with", "and", "in", "on", "that", "to"}


@dataclass
class PromptResult:
    prompt: str
    fragments: dict  # category -> list of resolved fragments
    seed: int
    slug: str
    key: str  # combination hash, stored in history
    signature: dict  # raw environment/lighting, for the anti-proximity window


@dataclass
class History:
    combos: set = field(default_factory=set)  # hashes of every combination ever generated
    recent: list = field(default_factory=list)  # [{"environment": raw, "lighting": raw}, ...] newest last

    def to_dict(self):
        return {"combos": sorted(self.combos), "recent": self.recent}

    @classmethod
    def from_dict(cls, data):
        return cls(combos=set(data.get("combos", [])), recent=list(data.get("recent", [])))


def read_lines(path):
    """Return non-empty, non-comment lines of a text file."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def split_tags(line):
    """'pool hall [no-floors]' -> ('pool hall', {'floors'})."""
    return EXCLUDE_PATTERN.sub("", line).strip(), set(EXCLUDE_PATTERN.findall(line))


def load_fragments(prompts_dir=PROMPTS_DIR):
    """Load categories, slots and templates from the prompts directory."""
    prompts_dir = Path(prompts_dir)
    categories = {key: read_lines(prompts_dir / f"{name}.txt") for name, key in CATEGORY_FILES.items()}
    # environment line -> categories it excludes
    exclusions = dict(split_tags(line) for line in categories["environment"])
    categories["environment"] = list(exclusions)
    slots = {p.stem: read_lines(p) for p in sorted((prompts_dir / "slots").glob("*.txt"))}
    templates = read_lines(prompts_dir / "templates.txt")
    return {"categories": categories, "exclusions": exclusions, "slots": slots, "templates": templates}


def fill_slots(text, slots, rng):
    """Replace each {slot} with a random value from slots[slot]; unknown slots are left as is."""
    return SLOT_PATTERN.sub(lambda m: rng.choice(slots[m.group(1)]) if m.group(1) in slots else m.group(0), text)


def draw_raw(categories, rng, recent, exclusions=None):
    """Draw raw (unfilled) fragments per category, avoiding recent environments/lightings
    and the categories the drawn environment excludes."""
    exclusions = exclusions or {}
    drawn = {}
    for category, (low, high) in QUANTITIES.items():
        pool = categories.get(category, [])
        excluded = exclusions.get(drawn["environment"][0], set()) if drawn.get("environment") else set()
        if not pool or category in excluded or rng.random() >= PROBABILITIES.get(category, 1.0):
            drawn[category] = []
            continue
        if category in ("environment", "lighting"):
            used = {entry.get(category) for entry in recent[-RECENT_SIZE:]}
            pool = [f for f in pool if f not in used] or pool
        count = min(rng.randint(low, high), len(pool))
        drawn[category] = rng.sample(pool, count)
    return drawn


def resolve(drawn, slots, rng):
    """Fill slots in every drawn fragment."""
    return {category: [fill_slots(f, slots, rng) for f in frags] for category, frags in drawn.items()}


def combo_key(resolved, template):
    """Stable hash of a full combination (order-insensitive within a category)."""
    parts = [template] + [f"{c}={'|'.join(sorted(v))}" for c, v in sorted(resolved.items())]
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()


def clean_prompt(text):
    """Drop empty sentences / comma items left by empty placeholders."""
    sentences = []
    for sentence in text.split("."):
        items = [item.strip() for item in sentence.split(",") if item.strip(" :")]
        if items:
            sentences.append(", ".join(items).strip(" :"))
    return ". ".join(s for s in sentences if s)


def render(template, resolved):
    values = {category: ", ".join(frags) for category, frags in resolved.items()}
    body = SLOT_PATTERN.sub(lambda m: values.get(m.group(1), ""), template)
    return f"{PROMPT_HEAD}, {clean_prompt(body)}"


def make_slug(environment, max_words=3):
    words = re.findall(r"[a-z0-9]+", environment.lower())
    words = [w for w in words if w not in SLUG_STOPWORDS]
    return "-".join(words[:max_words]) or "liminal"


def new_prompt(data, history, rng=None):
    """Draw a never-seen combination and return it with a random seed. Does not modify history."""
    rng = rng or random.Random()
    for _ in range(MAX_DRAW_ATTEMPTS):
        template = rng.choice(data["templates"])
        raw = draw_raw(data["categories"], rng, history.recent, data["exclusions"])
        resolved = resolve(raw, data["slots"], rng)
        key = combo_key(resolved, template)
        if key not in history.combos:
            break
    environment = resolved["environment"][0] if resolved["environment"] else ""
    return PromptResult(
        prompt=render(template, resolved),
        fragments=resolved,
        seed=rng.randint(0, 2**31 - 1),
        slug=make_slug(environment),
        key=key,
        signature={c: (raw[c][0] if raw[c] else None) for c in ("environment", "lighting")},
    )


def record(history, result):
    """Remember a generated combination."""
    history.combos.add(result.key)
    history.recent = (history.recent + [result.signature])[-RECENT_SIZE:]
