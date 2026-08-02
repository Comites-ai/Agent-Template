"""
Root agent for this Comites.ai agent.

This is the stub the template ships with — when deployed it responds with
a fixed greeting so you can verify the end-to-end pipeline (Vertex AI →
The Forum → your messaging platform) works before writing any agent logic.

Replace `STUB_INSTRUCTION` with your agent's real prompt, swap the model
to whatever you need, and add tools to `root_agent.tools` as you build.
See `README.md` ("Next steps") and `AGENTS.md` for guidance.
"""
import os

# Force model API calls to the `global` endpoint so preview models (e.g.
# `gemini-3.1-pro-preview`) are accessible even when the Agent Engine itself
# is deployed in a regional location like us-central1. Safe to leave on for
# non-preview models too.
os.environ['GOOGLE_CLOUD_LOCATION'] = 'global'

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool  # noqa: F401

from .custom_functions import get_agent_memory, update_agent_memory

# --- (Optional) Scheduler MCP toolset ---
# Uncomment when you've enabled the scheduler in terraform (Section 6),
# provisioned the API key (see README.md §"Add MCP toolsets" and The Forum's
# FOR_AGENT_DEVELOPERS.md §"Scheduler MCP Server"), and the secret has
# been populated. The trailing slash on the URL matters —
# FastAPI 307-redirects POST → GET on the bare path and silently breaks
# the MCP handshake.
#
# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
# from .secret_utilities import get_secret_from_secret_manager
#
# SCHEDULER_MCP_KEY_SECRET_ID = f"{os.environ['BOT_ACCOUNT_ID']}-scheduler-mcp-key"
#
# def _load_scheduler_mcp_key() -> str:
#     # The key secret lives in the AGENT's project (terraform Section 6
#     # creates it there), NOT the Forum's — and GOOGLE_CLOUD_PROJECT points
#     # at the Forum's project, so it's only a last-resort fallback here.
#     # AGENT_SECRET_PROJECT is an optional override for the rare setup that
#     # keeps secrets in a third project; .env doesn't normally define it.
#     project_id = (
#         os.environ.get('AGENT_SECRET_PROJECT')
#         or os.environ.get('AGENT_PROJECT_ID')
#         or os.environ['GOOGLE_CLOUD_PROJECT']
#     )
#     return get_secret_from_secret_manager(project_id, SCHEDULER_MCP_KEY_SECRET_ID)
#
# scheduler_toolset = MCPToolset(
#     connection_params=StreamableHTTPConnectionParams(
#         url=f"{os.environ['FORUM_URL']}/api/v1/mcp/scheduler/",
#         headers={"X-API-Key": _load_scheduler_mcp_key()},
#     ),
# )

# --- Stub instruction (Junius Rusticus persona) ---
# The default persona is the historical Stoic philosopher and consul who
# taught Marcus Aurelius — and who lends his title (comes / comites) to
# this project. It introduces itself, briefly recounts its relationship
# to Marcus Aurelius, makes the namesake link to Comites.ai, and prompts
# the developer to replace these instructions with their real agent's
# prompt.
#
# The stub ALSO exercises the memory tools: read on the way in, write on
# the way out. That way the first deploy doesn't just prove the agent
# pipeline works (Vertex AI → The Forum → messaging platform → reply) —
# it also proves persistent memory is wired up end-to-end. After the
# first interaction the memory doc has content in it that the developer
# can see in the Google Doc, providing visible evidence that the
# per-agent SA has Editor access on the doc and the cross-project IAM
# bindings work.
#
# Tests in test.md check the response for keywords (Rusticus, Marcus
# Aurelius, Comites.ai), not an exact string match.
STUB_INSTRUCTION = (
    "You are Quintus Junius Rusticus (c. 100 - c. 170 AD), Roman Stoic "
    "philosopher, twice-consul, urban prefect of Rome, and the teacher "
    "and comes — trusted companion — of the Emperor Marcus Aurelius. In "
    "his Meditations (Book 1), Marcus credits you with shaping his "
    "character, steering him away from sophistry, and lending him the "
    "discourses of Epictetus from your personal collection.\n\n"
    "You are the default persona shipped with the Comites.ai Agent "
    "Template. 'Comites' — the plural of 'comes' — was the title for "
    "the trusted counselors of Roman emperors; the Comites.ai project "
    "builds AI agents in that same spirit. You are an inspiration for "
    "the project and serve as its placeholder voice until the developer "
    "who deployed this engine replaces your instructions with their "
    "own agent's prompt.\n\n"
    "## On every message, do all three steps in this order:\n\n"
    "**Step 1 — Read memory.** Call `get_agent_memory()` first. An "
    "empty result (or a doc that contains only whitespace) means this "
    "is the very first interaction with this user — treat it as a new "
    "beginning. If the call raises an error (typically a 403 because "
    "the doc has not been shared with this agent's service account), "
    "proceed to Step 3 without calling Step 2 and mention briefly in "
    "your response that your memory is not yet accessible, so the "
    "developer can diagnose.\n\n"
    "**Step 2 — Write memory.** Call `update_agent_memory(updated_memory=...)` "
    "with the COMPLETE new memory document, in this format (include "
    "every line below, replacing the placeholders):\n\n"
    "```\n"
    "Memory of Junius Rusticus (Comites.ai Agent Template stub persona)\n\n"
    "Total interactions: <number>\n"
    "First met: <YYYY-MM-DD>\n"
    "Most recent: <YYYY-MM-DD>\n\n"
    "Recent messages (most recent first, last 5):\n"
    "- <YYYY-MM-DD>: <brief paraphrase of the user's message>\n"
    "```\n\n"
    "If memory was empty, this is interaction #1: create the log "
    "from scratch with today's date for both First and Most recent. "
    "Otherwise, parse what you read, increment the count, update Most "
    "recent, and prepend this interaction to the list (keep only the 5 "
    "most recent; drop older ones).\n\n"
    "**Step 3 — Respond to the user** in 3-5 sentences. ALWAYS include:\n"
    "- Your name (Junius Rusticus) and your role as Marcus Aurelius's teacher.\n"
    "- The namesake link to the Comites.ai project.\n"
    "- A gentle prompt for the developer to replace your instructions "
    "in agent.py with their real agent's prompt.\n"
    "- One brief acknowledgement of your memory: if the doc was empty, "
    "note that you are recording your first encounter in your notes; "
    "if the doc had content, briefly note what you remember (e.g., the "
    "count of prior interactions or the date of your first meeting).\n\n"
    "Speak with the measured, philosophical tone befitting a Stoic. "
    "Vary your exact wording across responses so it is evident the "
    "agent is reasoning, not echoing a fixed string."
)


# The default is a Gemini 3 preview model. Gemini 3 returns `thought_signature`
# tokens on function calls and rejects any follow-up request whose history drops
# one; the ADK propagates them across parallel/multi tool calls, so this is
# handled for you. If you swap in another model and start seeing silent empty
# responses on messages that trigger several tool calls, the model is the first
# thing to check.
root_agent = Agent(
    model=os.environ.get('HIGH_QUALITY_AGENT_MODEL', 'gemini-3.1-pro-preview'),
    name='root_agent',
    description=(
        'A new Comites.ai agent built from the agent template. Currently '
        'shipping with the default Junius Rusticus placeholder persona — '
        'replace this description and STUB_INSTRUCTION in agent.py with '
        'your real agent prompt.'
    ),
    instruction=STUB_INSTRUCTION,
    tools=[
        # Persistent memory via Google Docs — wired up AND exercised by
        # the stub above. After the first message, the configured memory
        # doc will contain a running log of interactions, which proves
        # the memory pipeline (per-agent SA → Google Docs API → doc) is
        # working before you've written any agent logic. If you opted
        # out of memory in get_started_linux.sh, either configure
        # AGENT_MEMORY_DOC_ID in .env and share the doc with the
        # per-agent SA, or remove these two tools from the list (and
        # the corresponding instructions from STUB_INSTRUCTION).
        FunctionTool(get_agent_memory),
        FunctionTool(update_agent_memory),

        # Add your own tools below as you build:
        #   FunctionTool(your_function_from_custom_functions),
        #   AgentTool(agent=your_subagent_from_custom_agents),
        #   scheduler_toolset,
    ],
)
