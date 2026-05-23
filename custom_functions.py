"""
Custom function tools for your agent.

Each function in this file is wrappable in `google.adk.tools.FunctionTool`
and added to `root_agent.tools` in `agent.py`. The function's docstring
is shown to the LLM as the tool description, so write clear docstrings
that explain what the tool does, what arguments it takes, and what it
returns.

Pattern:

    def my_tool(some_arg: str) -> dict:
        \"\"\"
        Short one-liner that explains what this does.

        Args:
            some_arg: Description.

        Returns:
            Description of the return structure.
        \"\"\"
        return {"result": some_arg}

Then in agent.py:

    from .custom_functions import my_tool
    ...
    tools=[FunctionTool(my_tool)],
"""

# ============================================================================
# (Optional) Persistent memory via Google Docs
#
# get_started_linux.sh offers to wire up a memory doc when you set up the
# agent. If you opted in, AGENT_MEMORY_DOC_ID is set in .env and the doc
# is shared with the agent service account. Uncomment the functions below
# and add them to root_agent.tools to give the agent persistent memory.
#
# These require `google-api-python-client` and `google-auth*` (already in
# requirements.txt) plus a `docs_utilities.py` module providing
# get_docs_connector(). Copy that module from
# https://github.com/Comites-ai/the-forum/tree/main/docs/examples
# (or look at how agents/growth_coach implements it).
# ============================================================================

# import os
# from .docs_utilities import get_docs_connector
#
# def get_agent_memory() -> str:
#     \"\"\"
#     Retrieve the agent's persistent memory from the configured Google Doc.
#
#     The doc ID comes from AGENT_MEMORY_DOC_ID in .env. The doc must be
#     shared (Editor access) with the agent's service account.
#
#     Returns:
#         The full text content of the memory document.
#     \"\"\"
#     doc_id = os.environ['AGENT_MEMORY_DOC_ID']
#     return get_docs_connector().read_doc(doc_id)
#
#
# def update_agent_memory(updated_memory: str) -> dict:
#     \"\"\"
#     Replace the agent's persistent memory with the provided text.
#
#     Args:
#         updated_memory: Complete new memory document text.
#
#     Returns:
#         API response confirming the update.
#     \"\"\"
#     doc_id = os.environ['AGENT_MEMORY_DOC_ID']
#     return get_docs_connector().write_doc(doc_id, updated_memory)
