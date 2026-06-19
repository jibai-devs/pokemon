from pokemon import catalog


def test_card_record_has_stats_for_known_card():
    rec = catalog.card_record(21)  # Scrafty
    assert rec is not None
    assert rec["hp"] == 120
    assert rec["cardType"] == 0


def test_card_record_none_for_unknown():
    assert catalog.card_record(-1) is None


def test_attack_record_has_damage():
    rec = catalog.attack_record(1)
    assert rec is not None
    assert "damage" in rec and "energies" in rec
