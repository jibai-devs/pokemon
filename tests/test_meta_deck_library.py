"""PKM-022: sanity checks on the built meta deck library.

Run scripts/fetch_limitless_decks.py first to (re)generate
data/meta_decks/library.json; these tests only validate the artifact.
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


def test_archetype_lists_count_matches_meta_share(library):
    total_lists = library["total_lists"]
    for archetype in library["archetypes"].values():
        expected_share = len(archetype["lists"]) / total_lists
        assert archetype["meta_share"] == pytest.approx(expected_share)


def test_cores_non_empty_for_common_archetypes(library):
    for name, archetype in library["archetypes"].items():
        if len(archetype["lists"]) >= 3:
            assert archetype["core"], f"{name} has no core despite {len(archetype['lists'])} lists"


def test_top_archetype_is_dragapult(library):
    top = max(library["archetypes"].items(), key=lambda kv: kv[1]["meta_share"])
    assert top[0] == "Dragapult"
    assert top[1]["meta_share"] > 0.3
