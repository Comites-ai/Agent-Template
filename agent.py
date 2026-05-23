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
# provisioned the API key (see README.md "Adding the scheduler MCP"), and
# the secret has been populated. The trailing slash on the URL matters —
# FastAPI 307-redirects POST → GET on the bare path and silently breaks
# the MCP handshake.
#
# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
# from .secret_utilities import get_secret_from_secret_manager
#
# SCHEDULER_MCP_KEY_SECRET_ID = f"{os.environ['BOT_ACCOUNT_ID']}-scheduler-mcp-key"
#
# def _load_scheduler_mcp_key() -> str:
#     project_id = os.environ.get('AGENT_SECRET_PROJECT') or os.environ['GOOGLE_CLOUD_PROJECT']
#     return get_secret_from_secret_manager(project_id, SCHEDULER_MCP_KEY_SECRET_ID)
#
# scheduler_toolset = MCPToolset(
#     connection_params=StreamableHTTPConnectionParams(
#         url=f"{os.environ['FORUM_URL']}/api/v1/mcp/scheduler/",
#         headers={"X-API-Key": _load_scheduler_mcp_key()},
#     ),
# )

# --- Stub instruction ---
# This is what makes the freshly-deployed agent respond with something
# recognizable so you can confirm the pipeline works end-to-end. Replace
# with your real prompt as soon as you've verified deployment.
STUB_INSTRUCTION = (
    "No matter what input you receive, you must always respond with this "
    "exact text and nothing else: "
    "\"HI! I'm a new agent that is being created using the comites.ai "
    "template! I haven't been configured to do anything yet.\""
)


root_agent = Agent(
    model=os.environ.get('HIGH_QUALITY_AGENT_MODEL', 'gemini-2.5-flash'),
    name='root_agent',
    description=(
        'A new Comites.ai agent built from the agent template. Currently '
        'a stub — replace this description and STUB_INSTRUCTION in agent.py '
        'with your real agent prompt.'
    ),
    instruction=STUB_INSTRUCTION,
    tools=[
        # Persistent memory via Google Docs — wired up by default.
        # The stub instruction above doesn't actually call these, so the
        # first deploy works even if you skipped the memory doc setup in
        # get_started_linux.sh. Your real prompt should call
        # get_agent_memory() at the start of each session and
        # update_agent_memory(...) before ending it.
        FunctionTool(get_agent_memory),
        FunctionTool(update_agent_memory),

        # Add your own tools below as you build:
        #   FunctionTool(your_function_from_custom_functions),
        #   AgentTool(agent=your_subagent_from_custom_agents),
        #   scheduler_toolset,
    ],
)
