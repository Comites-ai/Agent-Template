# Comites.ai Agent Template

A starter template for building AI agents that run on Vertex AI Agent Engine and serve users through **[The Forum](https://github.com/Comites-ai/the-forum)** — Comites.ai's open-source middleware that bridges Slack, Google Chat, Telegram, and Discord to your agent.

> **You are reading the template's README.** Once you run `./get_started_linux.sh`, this file is rewritten to be about *your* agent — what it does, how to deploy it, etc. The "what is this template" content is only here for the first-time setup.

## What you get

A repo that, on first deploy, gives you a working stub agent reachable from at least one messaging platform. Once you've confirmed the pipeline works end-to-end, you fill in real agent logic. No manual GCP wiring; no copy-pasting registration scripts; no figuring out which IAM binding you forgot.

Specifically:

- **`agent.py`** — stub root agent that replies with a recognizable greeting until you replace its instruction with real logic.
- **`terraform/`** — IaC for the agent's dedicated GCP project (service account, secrets per platform, IAM bindings to The Forum, ADK staging bucket, Workspace API enablements). All platform sections commented out until you select them.
- **`deploy_and_update.sh`** — blue/green deploy + smoke test + Firestore registration + stale-session cleanup.
- **`register_agent.py`** — auto-detects which platforms are enabled (by probing Secret Manager) and writes the agent record to The Forum's Firestore. Validates every token via the platform's own API before writing.
- **`get_started_linux.sh`** — interactive bootstrap that asks you a handful of questions, generates `.env` + `terraform.tfvars`, uncomments the right terraform sections, provisions the state bucket, optionally runs `terraform apply` + populates secrets, rewrites this README to be about your agent, and self-deletes.
- **`AGENTS.md`** — hard rules for AI coding agents working in the repo (and equally useful for humans).

## Architecture

```
┌──────────────────────────────────────────────────────┐
│         Messaging platforms                          │
│   (Slack · Google Chat · Telegram · Discord)         │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│  The Forum (Cloud Run)                               │
│  github.com/Comites-ai/the-forum                     │
│  · Routes messages to the right agent (via Firestore)│
│  · Manages sessions, identity, scheduled jobs        │
│  · Hosts the scheduler MCP server                    │
└──────────────────────────┬───────────────────────────┘
                           │  (cross-project call)
                           ▼
┌──────────────────────────────────────────────────────┐
│  YOUR AGENT (Vertex AI Reasoning Engine)             │
│  Lives in this repo · Deployed by deploy_and_update  │
│  · Conducts conversations using your prompt + tools  │
│  · Reads secrets / accesses Google Workspace via its │
│    own service account                               │
└──────────────────────────────────────────────────────┘
```

## Prerequisites

Before running `./get_started_linux.sh`:

1. **A local clone of [The Forum](https://github.com/Comites-ai/the-forum)** with its own `.env` and `terraform/terraform.tfvars` already populated. `get_started_linux.sh` reads from these to figure out what project The Forum runs in and what its public URL is.
2. **A GCP project for this agent** (separate from The Forum's project) with billing linked. Create with:
   ```bash
   gcloud projects create YOUR_AGENT_PROJECT \
     --name="Your Agent Name" \
     --organization=YOUR_ORG_ID
   gcloud beta billing projects link YOUR_AGENT_PROJECT \
     --billing-account=YOUR_BILLING_ACCT
   ```
   `get_started_linux.sh` verifies the project exists and offers helpful errors if billing or APIs are missing — but it does not create the project for you (deliberate: project creation is one-time and not really a fit for an idempotent bootstrap script).
3. **CLI tools installed and on `$PATH`**: `gcloud`, `terraform` (≥ 1.2), `python3`, `pip`, `adk` (`pip install google-adk`).
4. **`gcloud` authenticated**: both `gcloud auth login` and `gcloud auth application-default login`.
5. **For at least one messaging platform you intend to test with**: you'll need the bot already created on the platform's side (Slack app, Telegram BotFather, etc.), so you can paste the token into `get_started_linux.sh` when it prompts you. See [The Forum's `FOR_AGENT_DEVELOPERS.md`](https://github.com/Comites-ai/the-forum/blob/main/docs/FOR_AGENT_DEVELOPERS.md) for per-platform bot creation steps.

## Quick start

```bash
# 1. Clone this template (rename the directory to something that's a
#    valid Python identifier — no hyphens — since ADK uses the directory
#    name as the agent package name).
git clone <this-repo> my_agent
cd my_agent

# 2. Run the bootstrap. It walks you through everything and self-deletes
#    on success.
./get_started_linux.sh
```

After that, the repo is about *your* agent. Edit `agent.py` with your real prompt and tools, then redeploy:

```bash
./deploy_and_update.sh
```

## What `get_started_linux.sh` does

1. Verifies prerequisites and `gcloud` auth.
2. Locates your local clone of The Forum and reads its config.
3. Asks you for: agent display name, `bot_account_id`, GCP project, region, models, which platforms to enable.
4. Generates `.env` and `terraform/terraform.tfvars`.
5. Uncomments the platform sections you selected in `terraform/main.tf`.
6. Creates the GCS bucket for terraform state and wires up the `backend "gcs"` block in `terraform/providers.tf`.
7. Optionally: runs `terraform apply` (two-phase: secret containers first, then prompts silently for each platform token and `gcloud secrets versions add`, then full apply).
8. Optionally: wires up a Google Doc for persistent agent memory (prompts for the doc ID, sets `AGENT_MEMORY_DOC_ID` in `.env`, prints the SA email to share the doc with).
9. Rewrites this README and updates `AGENTS.md`'s preface for your agent.
10. Deletes the template-only files (`test.md`, `MAINTAINER_SETUP.md`) and itself.
11. Prints what to do next: configure platform webhooks (per-platform instructions for whichever you selected), then `./deploy_and_update.sh`.

## Repository layout

```
.
├── agent.py                  # ADK root agent (stub greeting until you replace)
├── __init__.py
├── custom_functions.py       # Your FunctionTool implementations
├── custom_agents.py          # Your sub-agents (used via AgentTool)
├── secret_utilities.py       # Secret Manager + retry helpers
├── requirements.txt
├── .env / .env.example       # Runtime config (.env is gitignored)
├── deploy_and_update.sh      # Blue/green deploy + smoke test + register
├── register_agent.py         # Auto-detects platforms, writes Firestore record
├── get_started_linux.sh      # One-shot bootstrap (self-deletes)
├── test.md                   # Template-maintainer smoke test (deleted by get_started)
├── MAINTAINER_SETUP.md       # For Comites.ai maintainers only (deleted by get_started)
├── AGENTS.md                 # Hard rules for AI agents working in this repo
├── terraform/
│   ├── main.tf               # All resources (platform sections commented)
│   ├── variables.tf
│   ├── terraform.tfvars      # Your config (gitignored)
│   ├── terraform.tfvars.example
│   ├── providers.tf          # GCS backend wired by get_started
│   └── README.md
├── LICENSE.txt               # AGPL-3.0
├── TRADEMARK.md
├── THIRD_PARTY_LICENSES
├── CONTRIBUTING.md           # CLA flow (same as The Forum)
└── .github/                  # CODEOWNERS, PR template, issue templates, CI
```

## License

AGPL-3.0. See [LICENSE.txt](LICENSE.txt) and [TRADEMARK.md](TRADEMARK.md). Because AGPL is a network copyleft, any agent you build from this template inherits AGPL-3.0 by default — meaning anyone who interacts with your deployed agent has the right to your agent's source. If you want to change the license on your fork, you can — but you have to actively do so and ensure you're not redistributing AGPL'd code under a more permissive license.

## Contributing to the template

See [CONTRIBUTING.md](CONTRIBUTING.md). Same CLA process as The Forum. Smoke test for template changes is in [test.md](test.md).

## Acknowledgements

This template is the convergence of patterns developed across The Forum and the existing Comites.ai agents (Growth Coach, Sommelier). It packages those patterns up so creating a new agent doesn't require excavating five years of decisions from five different repos.
