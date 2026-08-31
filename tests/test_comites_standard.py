"""Consistency + behavior tests for the Magister capability suite.

Run from the repo root:  python3 -m pytest tests/test_comites_standard.py
(or plain `python3 tests/test_comites_standard.py` — stdlib only, no deps).

Guards the two invariants AGENTS.md rule 13 promises:
  1. The shipped inquiries.json stub matches STANDARD_CONTRACTS verbatim.
  2. With MAGISTER_DISPLAY_NAME unset, the suite is completely inert.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("comites_standard", ROOT / "comites_standard.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


def test_stub_matches_standard_contracts():
    with open(ROOT / "inquiries.json", encoding="utf-8") as f:
        data = json.load(f)
    standard = {i["name"]: i for i in data.get("inquiries", []) if i.get("standard")}
    assert standard, "template stub should ship the standard entries"
    for name, entry in standard.items():
        contract = cs.STANDARD_CONTRACTS[name]
        assert entry["request_format"] == contract["request_format"], name
        assert entry["response_format"] == contract["response_format"], name


def test_gate_off_is_inert():
    os.environ.pop("MAGISTER_DISPLAY_NAME", None)
    assert cs.magister_instruction() == ""


def test_gate_on_teaches_only_published_entries():
    os.environ["MAGISTER_DISPLAY_NAME"] = "Test Magister"
    try:
        frag = cs.magister_instruction()
        assert "Test Magister" in frag
        assert "Conviction scale" in frag
        for name in cs.published_standard_inquiries():
            assert cs.STANDARD_CONTRACTS[name]["request_format"] in frag
    finally:
        os.environ.pop("MAGISTER_DISPLAY_NAME", None)


def test_parsers():
    r = cs.parse_review_idea(
        "IDEA_REVIEW: verdict=against conviction=9 | reason=a whole tub of butter\n"
        "Extra commentary that must not leak into the reason.")
    assert r == {"verdict": "against", "conviction": 9,
                 "reason": "a whole tub of butter"}, r

    r = cs.parse_review_idea("no_data: outside my domain")
    assert r["verdict"] == "abstain" and r["conviction"] is None

    r = cs.parse_review_idea("IDEA_REVIEW: verdict=for conviction=999 | reason=x")
    assert r["conviction"] == 10, "conviction must clamp to 1-10"

    r = cs.parse_goal_progress(
        "GOAL_PROGRESS: item=Goal 4: Run a 4h Marathon score=7 | evidence=5 of 6 runs\n"
        "trailing prose")
    assert r["score"] == 7 and r["evidence"] == "5 of 6 runs", r

    items = cs.parse_focus_items(
        "FOCUS: item=Audit the bins conviction=8 | why=trip Friday\n"
        "FOCUS: item=Order caps conviction=3 | why=stock low")
    assert [i["conviction"] for i in items] == [8, 3], items
    assert cs.parse_focus_items("FOCUS: none") == []
    assert cs.is_no_data("  No_Data: nothing this week")

    m = cs.parse_daily_metric("METRIC: metric=sleep_score date=2026-08-25 value=74")
    assert m == {"metric": "sleep_score", "date": "2026-08-25", "value": "74"}, m
    assert cs.parse_daily_metric("NO_DATA: no reading that day")["no_data"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  [OK] {name}")
            except AssertionError as e:
                failures += 1
                print(f"  [x] {name}: {e}")
    sys.exit(1 if failures else 0)
