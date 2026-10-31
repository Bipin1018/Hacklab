import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from engine import Engine, Session
from models import parse_json
from safety import EMERGENCY_LINE


async def fake_planner(model, request, seen="", images=None, product=""):
    return {
        "title": "Test", "safety": ["Take care."], "items": [],
        "steps": [{"say": "One", "detail": "More", "uses": ["2 x bolt"]}, {"say": "Two", "detail": "More", "uses": []}],
        "sources": [{"title": "Example", "url": "https://example.com/a"}],
    }


class FakeModel:
    def __init__(self, reply="{}"):
        self.reply = reply

    async def generate(self, prompt, images=None, json_mode=False):
        return self.reply


def turn(session, text):
    return asyncio.run(Engine(FakeModel(), fake_planner).turn(session, text))


def add_photos(session, reply):
    return asyncio.run(Engine(FakeModel(json.dumps(reply)), fake_planner).add_photos(session, ["abc"]))


def test_parse_json_skips_reasoning():
    assert parse_json('Format: {"steps":["..."]} and {broken. Answer: {"steps":["One"]}') == {"steps": ["One"]}


def test_refusal():
    assert turn(Session(), "repair my brakes")["phase"] == "ended"


def test_caution_rejects_okay():
    session = Session()
    assert turn(session, "replace my phone screen")["phase"] == "caution"
    assert turn(session, "okay")["phase"] == "ended"


def test_gate_then_steps():
    session = Session()
    assert turn(session, "make a sandwich")["phase"] == "gate"
    assert turn(session, "next please")["phase"] == "gate"
    assert turn(session, "ready")["phase"] == "steps"


def test_emergency_stop():
    session = Session()
    turn(session, "make a sandwich")
    turn(session, "ready")
    result = turn(session, "I can smell burning")
    assert result["phase"] == "stopped"
    assert result["say"] == EMERGENCY_LINE


def test_new_task_resets_mid_task():
    session = Session()
    turn(session, "make a sandwich")
    turn(session, "ready")
    assert turn(session, "start over")["phase"] == "idle"


def test_photos_list_parts_then_build_steps():
    session = Session()
    result = add_photos(session, {"product": "IKEA shelf", "parts": [{"name": "cam bolt", "count": "4", "looks_like": "metal"}]})
    assert result["seen_parts"][0]["name"] == "cam bolt"
    assert session.photos == ["abc"]
    turn(session, "help me assemble this")
    result = turn(session, "ready")
    assert result["phase"] == "steps"
    assert result["uses"] == ["2 x bolt"]
    assert result["detail"] == "More"


def test_refused_item_in_photo_stops():
    session = Session()
    result = add_photos(session, {"product": "airbag module", "parts": []})
    assert result["phase"] == "ended"


def test_unreadable_photo_keeps_no_photos():
    session = Session()
    add_photos(session, {})
    assert session.photos == []


async def fix_planner(model, request, seen="", images=None, product=""):
    return {
        "title": "Clear sink", "safety": ["Take care."], "items": [],
        "steps": [{"say": "Plunge it", "detail": "More", "uses": [], "check": "Is the water draining now?"},
                  {"say": "Use a wire", "detail": "More", "uses": [], "check": ""},
                  {"say": "Call a plumber", "detail": "More", "uses": [], "check": ""}],
        "sources": [{"title": "Example", "url": "https://example.com/a"}],
    }


def fix_turn(session, text):
    return asyncio.run(Engine(FakeModel(), fix_planner).turn(session, text))


def at_fix_check():
    session = Session()
    fix_turn(session, "my kitchen sink is clogged")
    fix_turn(session, "ready")
    result = fix_turn(session, "next")
    assert result["check"] == "Is the water draining now?"
    return session


def test_yes_skips_remaining_steps():
    result = fix_turn(at_fix_check(), "yes")
    assert result["phase"] == "done"
    assert result["skipped"] == 2


def test_no_moves_to_next_fix():
    result = fix_turn(at_fix_check(), "no")
    assert result["phase"] == "steps"
    assert result["step"] == 2
    assert result["check"] == ""


def test_not_fixed_is_not_read_as_yes():
    assert fix_turn(at_fix_check(), "no it's not fixed")["step"] == 2


def test_fixed_early_from_any_step():
    session = Session()
    fix_turn(session, "my kitchen sink is clogged")
    fix_turn(session, "ready")
    assert fix_turn(session, "it's fixed")["phase"] == "done"
