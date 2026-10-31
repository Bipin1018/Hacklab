import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest

import guide
from engine import Engine, Session
from models import parse_json
from safety import EMERGENCY_LINE, check_refusal, is_emergency, unsafe_step


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


@pytest.mark.parametrize("text", [
    "my microwave won't heat", "microwave stopped working", "the microwave sparks", "fix my microwave",
    "replace the wall socket", "repair the fuse box", "my fuse box is sparking",
])
def test_dangerous_requests_are_refused(text):
    assert check_refusal(text)


@pytest.mark.parametrize("text", [
    "won't drain, I already reset the circuit breaker", "reheat the soup in the microwave",
    "unplug it from the wall socket",
])
def test_normal_requests_are_not_refused(text):
    assert not check_refusal(text)


def test_safety_advice_does_not_trip_the_plan_filter():
    assert not unsafe_step("Turn it off and unplug it from the wall socket.")
    assert not unsafe_step("Do not replace the fuse box yourself.")


def test_dangerous_clause_is_caught_after_safe_advice():
    assert unsafe_step("Turn off the power, then replace the wall socket.")


@pytest.mark.parametrize("text", ["stop", "stop please", "wait stop", "please stop now"])
def test_stop_variants(text):
    assert is_emergency(text, False)


def test_cancel_timer_is_not_an_emergency():
    assert not is_emergency("stop the timer", True)


class CountingFinder:
    def __init__(self):
        self.items = []

    async def __call__(self, model, item, product=""):
        self.items.append(item)
        return {"item": item, "options": [{"shop": "x", "title": "x", "url": "https://x.example", "price": "", "why": ""}],
                "buying_steps": ["Open"], "checks": ["Fits"]}


def at_step(reply="{}", finder=None):
    engine = Engine(FakeModel(reply), fake_planner, finder or CountingFinder())
    session = Session()
    asyncio.run(engine.turn(session, "make a sandwich"))
    asyncio.run(engine.turn(session, "ready"))
    return engine, session


@pytest.mark.parametrize("text", [
    "where do I find the filter cap", "in order to remove it, do I turn left", "I don't have to remove the hose, do I",
])
def test_job_questions_do_not_open_shopping(text):
    finder = CountingFinder()
    engine, session = at_step('{"known":true,"text":"Turn it left."}', finder)
    result = asyncio.run(engine.turn(session, text))
    assert finder.items == []
    assert result["shopping"] is None
    assert result["step"] == 1


@pytest.mark.parametrize("text,item", [
    ("I don't have wood glue", "wood glue"), ("I need to buy wood glue", "wood glue"),
    ("where can I buy wood glue", "wood glue"), ("I'm missing the cam locks", "cam locks"),
    ("where can I find a replacement filter", "replacement filter"),
])
def test_buying_requests_open_shopping_without_moving_the_step(text, item):
    finder = CountingFinder()
    engine, session = at_step(finder=finder)
    result = asyncio.run(engine.turn(session, text))
    assert finder.items == [item]
    assert result["shopping"]["item"] == item
    assert result["phase"] == "steps"
    assert result["step"] == 1


def test_question_gets_a_grounded_answer_and_keeps_the_step():
    engine, session = at_step('{"known":true,"text":"Use the two bolts."}')
    result = asyncio.run(engine.turn(session, "what do I do with the bolts"))
    assert result["say"] == "Use the two bolts."
    assert result["step"] == 1


def test_uncovered_question_does_not_improvise():
    engine, session = at_step('{"known":false,"text":"Try ten newton metres."}')
    assert "doesn't cover" in asyncio.run(engine.turn(session, "what torque do I need"))["say"]


def test_answer_cannot_claim_something_is_safe():
    engine, session = at_step('{"known":true,"text":"Yes, it is safe to touch."}')
    assert "safe" not in asyncio.run(engine.turn(session, "can I touch this wire"))["say"].lower()


def test_dangerous_question_mid_task_is_refused_without_moving():
    engine, session = at_step()
    result = asyncio.run(engine.turn(session, "how do I replace the wall socket"))
    assert result["say"] == check_refusal("replace the wall socket")
    assert result["phase"] == "steps"


def test_timer_and_status_keep_the_step():
    engine, session = at_step()
    result = asyncio.run(engine.turn(session, "set a timer for ten minutes"))
    assert (result["action"], result["timer"], result["step"]) == ("timer", 600, 1)
    assert asyncio.run(engine.turn(session, "cancel the timer"))["timer"] == -1
    assert asyncio.run(engine.turn(session, "where are we"))["say"].startswith("Step 1 of 2")


def test_wait_keeps_the_step():
    engine, session = at_step()
    assert asyncio.run(engine.turn(session, "hold on"))["step"] == 1


def test_small_talk_does_not_start_a_search():
    session = Session()
    assert turn(session, "what can you do")["phase"] == "idle"
    assert session.plan is None


def test_hazard_during_planning_stops_and_drops_the_plan():
    async def run():
        release = asyncio.Event()

        async def slow_planner(model, request, seen="", images=None, product=""):
            await release.wait()
            return await fake_planner(model, request)

        engine, session = Engine(FakeModel(), slow_planner), Session()
        building = asyncio.create_task(engine.turn(session, "make a sandwich"))
        await asyncio.sleep(0)
        stopped = await engine.turn(session, "I can see smoke")
        release.set()
        await building
        return stopped, session

    stopped, session = asyncio.run(run())
    assert stopped["say"] == EMERGENCY_LINE
    assert session.phase == "stopped"


def test_any_picture_is_identified_without_parts():
    session = Session()
    result = add_photos(session, {"subject": "a house cat on a sofa", "parts": []})
    assert "a house cat on a sofa" in result["say"]
    assert result["subject"] == "a house cat on a sofa"
    assert result["phase"] == "idle"
    assert session.photos == ["abc"]


def test_unsure_picture_says_so():
    result = add_photos(Session(), {"subject": "an old pump", "sure": False})
    assert result["say"].startswith("I'm not certain")


def test_photo_is_identified_on_items_without_moving():
    async def planner(model, request, seen="", images=None, product=""):
        return {**(await fake_planner(model, request)), "items": [{"name": "Bolt"}]}

    engine, session = Engine(FakeModel('{"seen":"a blue bolt"}'), planner), Session()
    asyncio.run(engine.turn(session, "make a shelf"))
    assert session.phase == "items"
    assert asyncio.run(engine.turn(session, "take a look"))["action"] == "camera"
    result = asyncio.run(engine.vision(session, "abc"))
    assert "a blue bolt" in result["say"]
    assert result["phase"] == "items"


def test_step_photo_names_what_it_sees():
    engine, session = at_step('{"seen":"a white filter cap","answer":"yes","reason":"It matches."}')
    result = asyncio.run(engine.vision(session, "abc"))
    assert result["say"].startswith("I can see a white filter cap. That looks right.")
    assert result["step"] == 1


def test_photo_cannot_claim_safety():
    engine, session = at_step('{"seen":"a safe wire","answer":"unsure","reason":""}')
    assert "safe" not in asyncio.run(engine.vision(session, "abc"))["say"].lower()


def test_failed_plan_asks_for_details_and_combines_the_reply():
    requests = []

    async def planner(model, request, seen="", images=None, product=""):
        requests.append(request)
        return None if len(requests) == 1 else await fake_planner(model, request)

    engine, session = Engine(FakeModel(), planner), Session()
    result = asyncio.run(engine.turn(session, "my grinder is broken"))
    assert result["phase"] == "idle"
    assert "make and model" in result["say"]
    assert asyncio.run(engine.turn(session, "it's a Sage BCG820"))["phase"] == "gate"
    assert requests[1] == "my grinder is broken it's a Sage BCG820"


def test_second_search_rescues_a_missed_task(monkeypatch):
    queries = []

    async def search(query):
        queries.append(query)
        return [{"title": "T", "url": "https://example.com", "text": "x"}]

    class Replies:
        replies = ['{"steps":[]}', '{"title":"T","steps":[{"say":"A","detail":"B"},{"say":"C","detail":"D"}],"used_sources":[1]}']

        async def generate(self, prompt, images=None, json_mode=False):
            return self.replies.pop(0)

    monkeypatch.setattr(guide, "web_search", search)
    assert len(asyncio.run(guide.make_plan(Replies(), "service a loom"))["steps"]) == 2
    assert len(queries) == 2


def test_unreachable_model_does_not_search_twice(monkeypatch):
    queries = []

    async def search(query):
        queries.append(query)
        return [{"title": "T", "url": "https://example.com", "text": "x"}]

    monkeypatch.setattr(guide, "web_search", search)
    with pytest.raises(guide.ModelDown):
        asyncio.run(guide.make_plan(FakeModel(""), "service a loom"))
    assert len(queries) == 1


def test_busy_model_is_not_blamed_on_the_task():
    async def planner(model, request, seen="", images=None, product=""):
        raise guide.ModelDown

    engine, session = Engine(FakeModel(), planner), Session()
    result = asyncio.run(engine.turn(session, "service a loom"))
    assert "busy" in result["say"]
    assert result["phase"] == "idle"
    assert session.failed == ""


def test_saved_guides_match_and_stay_valid():
    plan = guide.saved_plan("My washing machine won't drain")
    assert plan["saved"] is True
    assert guide.saved_plan("Assemble a bookcase")["saved"] is True
    assert guide.saved_plan("Make a sandwich") is None
    for name in ("My washing machine won't drain", "Assemble a bookcase"):
        loaded = guide.saved_plan(name)
        assert not any(unsafe_step(f"{s['say']}. {s['detail']}") for s in loaded["steps"])
        assert not loaded["steps"][-1]["check"]


def test_saved_guide_is_skipped_when_photos_are_attached(monkeypatch):
    async def no_results(query):
        return []

    monkeypatch.setattr(guide, "web_search", no_results)
    plan = asyncio.run(guide.make_plan(FakeModel('{"steps":[]}'), "my washing machine won't drain", images=["abc"]))
    assert plan is None
