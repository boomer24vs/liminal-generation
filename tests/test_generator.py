import random

import generator


def test_read_lines_skips_comments_and_blanks(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("# comment\n\n  one  \ntwo\n")
    assert generator.read_lines(f) == ["one", "two"]


def test_all_categories_and_slots_load():
    data = generator.load_fragments()
    for category in generator.QUANTITIES:
        assert data["categories"][category], category
    assert data["templates"]
    assert {"year90", "year00"} <= set(data["slots"])


def test_every_slot_used_in_fragments_exists():
    data = generator.load_fragments()
    lines = [f for frags in data["categories"].values() for f in frags]
    for line in lines:
        for slot in generator.SLOT_PATTERN.findall(line):
            assert slot in data["slots"], f"missing slot {slot!r} in: {line}"


def test_fill_slots():
    rng = random.Random(0)
    assert generator.fill_slots("{color} wall", {"color": ["teal"]}, rng) == "teal wall"
    assert generator.fill_slots("{unknown}", {}, rng) == "{unknown}"


def test_clean_prompt_drops_empty_placeholders():
    assert generator.clean_prompt("a, , b. . c, :. ") == "a, b. c"


def test_prompt_always_starts_with_head_and_has_no_leftover_braces():
    data = generator.load_fragments()
    history = generator.History()
    for seed in range(200):
        result = generator.new_prompt(data, history, random.Random(seed))
        assert result.prompt.startswith(generator.PROMPT_HEAD + ", ")
        assert "no people" in result.prompt
        assert "{" not in result.prompt and ", ," not in result.prompt


def test_quantities_are_bounded():
    data = generator.load_fragments()
    for seed in range(300):
        drawn = generator.draw_raw(data["categories"], random.Random(seed), [])
        for category, (low, high) in generator.QUANTITIES.items():
            count = len(drawn[category])
            assert count == 0 or low <= count <= high
            if category not in generator.PROBABILITIES:
                assert count >= low


def test_anomaly_probability_roughly_respected():
    data = generator.load_fragments()
    rng = random.Random(1)
    hits = sum(bool(generator.draw_raw(data["categories"], rng, [])["anomalies"]) for _ in range(2000))
    assert 0.28 < hits / 2000 < 0.42


def test_anti_proximity_avoids_recent_environment_and_lighting():
    data = generator.load_fragments()
    history = generator.History()
    rng = random.Random(3)
    for _ in range(100):
        result = generator.new_prompt(data, history, rng)
        recent = history.recent[-generator.RECENT_SIZE:]
        assert result.signature["environment"] not in [r["environment"] for r in recent]
        assert result.signature["lighting"] not in [r["lighting"] for r in recent]
        generator.record(history, result)
    assert len(history.recent) == generator.RECENT_SIZE


def test_never_repeats_a_recorded_combination():
    data = generator.load_fragments()
    history = generator.History()
    rng = random.Random(5)
    keys = set()
    for _ in range(300):
        result = generator.new_prompt(data, history, rng)
        assert result.key not in keys
        keys.add(result.key)
        generator.record(history, result)


def test_history_roundtrip():
    history = generator.History(combos={"a", "b"}, recent=[{"environment": "x", "lighting": "y"}])
    restored = generator.History.from_dict(history.to_dict())
    assert restored.combos == {"a", "b"} and restored.recent == history.recent


def test_make_slug():
    assert generator.make_slug("tiled poolroom with shallow still water") == "tiled-poolroom-shallow"
    assert generator.make_slug("") == "liminal"


def test_split_tags():
    assert generator.split_tags("pool hall [no-walls] [no-floors]") == ("pool hall", {"walls", "floors"})
    assert generator.split_tags("plain room") == ("plain room", set())


def test_environment_tags_are_stripped_and_respected():
    data = generator.load_fragments()
    assert not any("[" in env for env in data["categories"]["environment"])
    rng = random.Random(2)
    for _ in range(500):
        drawn = generator.draw_raw(data["categories"], rng, [], data["exclusions"])
        for category in data["exclusions"][drawn["environment"][0]]:
            assert drawn[category] == []
