"""Tests for ResilientLlm's orphaned-tool-call guard.

Run from the repo root:  python3 tests/test_orphaned_tool_calls.py

Plain execution, like test_comites_standard.py — the repo root is an ADK
package whose `__init__.py` does `from . import agent`, which pytest's
collection cannot resolve for anything under tests/. Written as plain
`test_*` functions with bare asserts, so it also runs under pytest the day
that is sorted out.

Needs google-genai for the `types` shapes and nothing else.

What it guards: a turn cut off after a function_call is persisted but before
the tool replies leaves the session replaying a `tool_use` with no
`tool_result`. Anthropic rejects that history on every later turn — primary
and backup alike, since they share it — so the agent goes silent until the
session is reset. The guard inserts an honest "unconfirmed" result so the
history replays cleanly.
"""
import types as types_module
import sys
from pathlib import Path

try:
    from google.genai import types
except ImportError:  # pragma: no cover - bare checkout
    print("SKIP: google-genai not installed")
    raise SystemExit(0)

ROOT = Path(__file__).resolve().parent.parent


def _stub(name, **attrs):
    module = types_module.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules.setdefault(name, module)
    return module


def _load_healer():
    """Import just the healer out of model_utils.

    model_utils pulls in google.adk and the agent's own secret_utilities at
    module scope. The function under test touches neither — it is a pure
    transform over google.genai types — so those imports are stubbed rather
    than installed. That keeps this test runnable on a bare checkout with
    only google-genai present, the same as the rest of tests/.
    """
    _stub("google.adk")
    _stub("google.adk.models")
    _stub("google.adk.models.base_llm", BaseLlm=object)
    _stub("google.adk.models.llm_request", LlmRequest=object)
    _stub("google.adk.models.llm_response", LlmResponse=object)
    _stub("secret_utilities", get_secret_from_secret_manager=lambda *a, **k: "")

    source = (ROOT / "model_utils.py").read_text(encoding="utf-8")
    # The one relative import; rewritten so the module can load standalone.
    source = source.replace(
        "from .secret_utilities import", "from secret_utilities import"
    )

    module = types_module.ModuleType("model_utils_under_test")
    module.__file__ = str(ROOT / "model_utils.py")
    exec(compile(source, str(ROOT / "model_utils.py"), "exec"), module.__dict__)
    return module.heal_orphaned_tool_calls


heal_orphaned_tool_calls = _load_healer()


def _call(call_id, name="write_sheet"):
    return types.Content(
        role="model",
        parts=[types.Part(function_call=types.FunctionCall(id=call_id, name=name))],
    )


def _calls(*pairs):
    return types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(id=cid, name=name))
            for cid, name in pairs
        ],
    )


def _response(call_id, name="write_sheet"):
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=call_id, name=name, response={"ok": True}
                )
            )
        ],
    )


def _text(text, role="user"):
    return types.Content(role=role, parts=[types.Part(text=text)])


def _responses_in(content):
    return [
        p.function_response
        for p in (content.parts or [])
        if p.function_response is not None
    ]


def test_healthy_history_is_untouched():
    contents = [
        _text("do the thing"),
        _call("toolu_1"),
        _response("toolu_1"),
        _text("done", role="model"),
    ]
    before = len(contents)
    assert heal_orphaned_tool_calls(contents) == 0
    assert len(contents) == before


def test_orphaned_call_gets_a_result_immediately_after_it():
    contents = [_text("do the thing"), _call("toolu_1")]

    assert heal_orphaned_tool_calls(contents) == 1

    assert len(contents) == 3
    inserted = contents[2]
    assert inserted.role == "user"
    responses = _responses_in(inserted)
    assert [r.id for r in responses] == ["toolu_1"]
    assert [r.name for r in responses] == ["write_sheet"]
    assert "unconfirmed" in responses[0].response["error"]


def test_orphan_mid_history_is_healed_in_place():
    """The user gave up and asked again; the orphan is no longer at the tail."""
    contents = [
        _call("toolu_1"),
        _text("are you there?"),
    ]

    assert heal_orphaned_tool_calls(contents) == 1

    assert _responses_in(contents[1])[0].id == "toolu_1"
    assert contents[2].parts[0].text == "are you there?"


def test_every_sibling_of_a_parallel_call_is_answered():
    """Anthropic wants every tool_use of a message answered in the next one."""
    contents = [_calls(("toolu_1", "write_sheet"), ("toolu_2", "notify"))]

    assert heal_orphaned_tool_calls(contents) == 2

    responses = _responses_in(contents[1])
    assert [r.id for r in responses] == ["toolu_1", "toolu_2"]


def test_a_partly_answered_parallel_call_joins_the_existing_response():
    """The surviving id must be answered in the SAME content as its sibling."""
    contents = [
        _calls(("toolu_1", "write_sheet"), ("toolu_2", "notify")),
        _response("toolu_1"),
    ]

    assert heal_orphaned_tool_calls(contents) == 1

    # No new content inserted — the result joined the one already there.
    assert len(contents) == 2
    responses = _responses_in(contents[1])
    assert [r.id for r in responses] == ["toolu_1", "toolu_2"]
    assert responses[0].response == {"ok": True}
    assert "unconfirmed" in responses[1].response["error"]


def test_calls_without_an_id_are_left_alone():
    """Some Gemini histories carry no ids; they cannot be matched."""
    contents = [
        types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name="write_sheet"))],
        )
    ]

    assert heal_orphaned_tool_calls(contents) == 0
    assert len(contents) == 1


def test_healing_is_idempotent():
    """The guard runs before every model call; the second pass must no-op."""
    contents = [_text("do the thing"), _call("toolu_1")]

    assert heal_orphaned_tool_calls(contents) == 1
    healed_len = len(contents)
    assert heal_orphaned_tool_calls(contents) == 0
    assert len(contents) == healed_len


def test_empty_history_is_safe():
    contents = []
    assert heal_orphaned_tool_calls(contents) == 0
    assert contents == []


def test_several_orphans_across_the_history_are_all_healed():
    contents = [
        _call("toolu_1"),
        _text("still there?"),
        _call("toolu_2", "notify"),
    ]

    assert heal_orphaned_tool_calls(contents) == 2

    assert _responses_in(contents[1])[0].id == "toolu_1"
    assert _responses_in(contents[-1])[0].id == "toolu_2"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
        else:
            print(f"ok   {name}")
    raise SystemExit(1 if failures else 0)
