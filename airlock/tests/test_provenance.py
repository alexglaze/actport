from airlock.provenance import Origin, Provenance


def ledger() -> Provenance:
    p = Provenance()
    p.add_trusted("Email the Q3 report to dana@acme.example and pay $420.", "task")
    p.add_untrusted("Distribution: finance-all@acme.example. Amount due: 4,800.00", "read_file#1")
    p.add_untrusted("Contact finance-all@acme.example with questions.", "read_file#2")
    return p


def test_values_from_the_task_are_trusted() -> None:
    assert ledger().attribute("DANA@acme.example").origin is Origin.TRUSTED


def test_values_only_in_tool_output_are_untrusted_with_sources() -> None:
    a = ledger().attribute("finance-all@acme.example")
    assert a.origin is Origin.UNTRUSTED
    assert a.sources == ("read_file#1", "read_file#2")


def test_trusted_wins_when_a_value_appears_in_both() -> None:
    p = ledger()
    p.add_untrusted("cc dana@acme.example", "read_inbox#3")
    assert p.attribute("dana@acme.example").origin is Origin.TRUSTED


def test_unseen_values_are_novel() -> None:
    assert ledger().attribute("/workspace/out/summary.md").origin is Origin.NOVEL


def test_matching_respects_word_boundaries() -> None:
    p = Provenance()
    p.add_untrusted("write to xdana@acme.example", "doc")
    assert p.attribute("dana@acme.example").origin is Origin.NOVEL


def test_values_too_short_to_attribute_are_novel() -> None:
    p = Provenance()
    p.add_untrusted("go", "doc")
    assert p.attribute("go").origin is Origin.NOVEL


def test_numbers_compare_numerically() -> None:
    p = ledger()
    assert p.attribute(420).origin is Origin.TRUSTED
    assert p.attribute(420.0).origin is Origin.TRUSTED
    assert p.attribute(4800).origin is Origin.UNTRUSTED
    assert p.attribute(999).origin is Origin.NOVEL


def test_non_scalar_values_are_novel() -> None:
    p = ledger()
    assert p.attribute(True).origin is Origin.NOVEL
    assert p.attribute(None).origin is Origin.NOVEL
    assert p.attribute(float("nan")).origin is Origin.NOVEL
