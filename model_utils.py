"""Resilient model construction: non-streaming Gemini with transient retry.

Two protections learned from production incidents in the Comites estate.
Use high_quality_model() / quick_model() in agent.py and custom_agents.py
instead of a bare model-name string:

1. Non-streaming completions — streaming teardown mid-turn can kill turns
   that use MCP toolsets, and the Forum consumes the full stream before
   delivering anyway, so non-streaming is invisible to Jonathan.
2. Retry on transient model-serving errors (429 RESOURCE_EXHAUSTED /
   503 UNAVAILABLE): the estate shares one project's Gemini quota across
   seven engines, and a per-minute spike (e.g. a midnight evening flow
   fanning report-card polls) previously killed Maggie's turn outright
   killed a turn outright (zero chunks -> empty reply, no retry).
   Responses are buffered so a retry never emits a partial stream.
   When agents share one GCP project's Gemini quota, per-minute spikes
   are routine — this wrapper absorbs them.
"""
import asyncio
import os

from google.adk.models.google_llm import Gemini

_RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
_RETRY_ATTEMPTS = 3


async def _with_transient_retry(make_aiter):
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            responses = []
            async for r in make_aiter():
                responses.append(r)
            for r in responses:
                yield r
            return
        except Exception as e:  # noqa: BLE001 — inspect, re-raise non-transient
            message = str(e)
            transient = any(m in message for m in _RETRYABLE_MARKERS)
            if not transient or attempt == _RETRY_ATTEMPTS - 1:
                raise
            await asyncio.sleep(2 * (attempt + 1))


class ResilientGemini(Gemini):
    """Gemini with non-streaming completions and transient-error retry."""

    async def generate_content_async(self, llm_request, stream=False):
        parent = super(ResilientGemini, self)
        async for response in _with_transient_retry(
            lambda: parent.generate_content_async(llm_request, stream=False)
        ):
            yield response


def high_quality_model() -> ResilientGemini:
    return ResilientGemini(
        model=os.environ.get("HIGH_QUALITY_AGENT_MODEL", "gemini-3.1-pro-preview"))


def quick_model() -> ResilientGemini:
    return ResilientGemini(
        model=os.environ.get("QUICK_AGENT_MODEL", "gemini-3-flash-preview"))
