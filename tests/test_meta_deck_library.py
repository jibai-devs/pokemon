"""PKM-022/PKM-024: sanity checks on the built meta deck library.

Run scripts/fetch_limitless_decks.py first to (re)generate
data/meta_decks/library.json, then scripts/extract_replay_decks.py to merge
the replay-extracted bot archetypes (plan 011 Phase 1); these tests only
validate the artifact, and pass on both the limitless-only and merged forms.
"""

import json
from pathlib import Path

import pytest

LIBRARY_PATH = Path(__file__).resolve().parents[1] / "data" / "meta_decks" / "library.json"

pytestmark = pytest.mark.skipif(
    not LIBRARY_PATH.exists(), reason="library.json not generated — run scripts/fetch_limitless_decks.py"
)


@pytest.fixture(scope="module")
def library():
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def test_library_loads(library):
    assert library["total_lists"] > 0
    assert library["archetypes"]


def test_every_list_sums_to_60(library):
    for name, archetype in library["archetypes"].items():
        for lst in archetype["lists"]:
            total = sum(lst["cards"].values())
            assert total == 60, f"{name} / {lst['player']} sums to {total}"


def test_meta_share_consistent(library):
    sources = library.get("sources")
    if sources is None:
        # Pre-merge (limitless-only) form: meta_share is the plain list share.
        total_lists = library["total_lists"]
        for archetype in library["archetypes"].values():
            expected_share = len(archetype["lists"]) / total_lists
            assert archetype["meta_share"] == pytest.approx(expected_share)
        return
    # Merged form: meta_share = within-source share x that source's weight,
    # and the shares form a proper prior (sum to 1 across the library).
    for name, archetype in library["archetypes"].items():
        weight = sources[archetype["source"]]["weight"]
        assert archetype["meta_share"] == pytest.approx(archetype["source_share"] * weight), name
    total = sum(a["meta_share"] for a in library["archetypes"].values())
    assert total == pytest.approx(1.0, abs=0.01)


def test_cores_non_empty_for_common_archetypes(library):
    for name, archetype in library["archetypes"].items():
        if len(archetype["lists"]) >= 3:
            assert archetype["core"], f"{name} has no core despite {len(archetype['lists'])} lists"


def test_top_archetype_is_dragapult(library):
    """Dragapult is the #1 *human-tournament* archetype (PKM-022's headline
    finding); in the merged library that means top among non-replay sources."""
    human = {
        name: arch
        for name, arch in library["archetypes"].items()
        if arch.get("source", "limitless_550") != "replays"
    }
    top = max(human.items(), key=lambda kv: kv[1]["meta_share"])
    assert top[0] == "Dragapult"
    share = top[1].get("source_share", top[1]["meta_share"])
    assert share > 0.3


def test_replay_archetypes_tagged_and_weighted(library):
    """Merged form only: replay archetypes exist, are tagged, and carry the
    dominant share of the prior (they are today's actual opponents)."""
    sources = library.get("sources")
    if sources is None or "replays" not in sources:
        pytest.skip("library not yet merged with replay-extracted lists")
    replay_archetypes = [a for a in library["archetypes"].values() if a["source"] == "replays"]
    assert replay_archetypes
    replay_mass = sum(a["meta_share"] for a in replay_archetypes)
    assert replay_mass == pytest.approx(sources["replays"]["weight"], abs=0.01)
