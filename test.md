# Smoke Test for Template Changes

**Audience: template maintainers.** Anyone modifying `get_started_linux.sh`, `terraform/`, `deploy_and_update.sh`, or `register_agent.py` must walk through this test against a real GCP project before requesting PR review. CI cannot verify infrastructure or platform integration end-to-end.

**This file is deleted by `get_started_linux.sh`** — it does not ship with the agent that an end user builds from the template.

## What this test proves

Following this template from `git clone` to "the bot replies on Slack" works in a single pass, with no manual GCP wiring beyond what `get_started_linux.sh` walks the operator through.

## Prerequisites

Before starting:

1. **A test GCP project** with billing linked. Reuse if possible (faster), or create fresh. The test will create resources in this project and the easiest cleanup is a full `terraform destroy`.
2. **A test Slack workspace** you control and can install apps into. (Slack is the easiest platform to test — fastest bot creation, easiest message delivery.)
3. **A local clone of [The Forum](https://github.com/Comites-ai/the-forum)** that's already deployed to its own GCP project and operational. The Forum must be reachable on its Cloud Run URL.
4. **CLI tools installed**: `gcloud` (authenticated, both `auth login` and `auth application-default login`), `terraform` (≥ 1.2), `python3`, `pip`, `adk`.

## Test steps

### Step 1: Fresh clone of your branch

```bash
# Clone the branch you want to test into a directory with a valid
# Python identifier name (no hyphens — ADK uses the dir as a package name).
git clone -b YOUR_BRANCH git@github.com:Comites-ai/agent-template.git smoke_test_agent
cd smoke_test_agent

# Confirm the working tree is the version under test (in particular, that
# you don't have any uncommitted changes that wouldn't ship to an end user).
git status
```

### Step 2: Bootstrap a Slack app

In your test Slack workspace:

1. https://api.slack.com/apps → Create New App → From scratch → name it `smoke-test-agent` (or similar) → pick your test workspace.
2. **OAuth & Permissions** → Bot Token Scopes → add at minimum `chat:write`, `im:history`, `im:read`. (Add `files:read` if you want to test image input.)
3. **Install to Workspace** → copy the Bot User OAuth Token (`xoxb-...`). You'll paste this into `get_started_linux.sh`.
4. **Basic Information** → copy the Signing Secret. The Forum needs this in its own `.env` / Secret Manager — verify The Forum's `SLACK_SIGNING_SECRET` includes this app's secret (comma-separated list) and that The Forum has been redeployed if you added it.
5. Leave the Slack tab open — you'll come back to configure Event Subscriptions in Step 8.

### Step 3: Run `get_started_linux.sh`

```bash
./get_started_linux.sh
```

Answer the prompts:

- Path to The Forum repo: the absolute path to your local Forum clone.
- Agent display name: `Smoke Test Agent`.
- `bot_account_id`: `smoke-test-agent`.
- GCP project: your test project ID.
- Region: `us-central1` (or whatever matches The Forum).
- Models: defaults are fine.
- Platforms: select **Slack only** for this smoke test.
- Memory doc: skip (`n`) for this test.
- Run `terraform apply` now: **yes**.
- When prompted for the Slack bot token: paste the `xoxb-...` token from Step 2.

The script should:

- Verify gcloud auth and the project exists.
- Bootstrap APIs (`serviceusage`, `cloudresourcemanager`, `secretmanager`, `aiplatform`).
- Generate `.env` and `terraform/terraform.tfvars`.
- Uncomment Section 2 (Slack) in `terraform/main.tf`.
- Create the GCS state bucket and wire up the backend in `providers.tf`.
- Run `terraform init`.
- Run `terraform apply -target=google_secret_manager_secret.slack_bot_token` (secret container).
- Populate the Slack token via `gcloud secrets versions add`.
- Run the full `terraform apply` (IAM bindings, service account, staging bucket).
- Rewrite `README.md` and `AGENTS.md` preface.
- Delete itself, `MAINTAINER_SETUP.md`, and this `test.md`.

**Expected end state**: `README.md` now starts with "# Smoke Test Agent"; `test.md`, `MAINTAINER_SETUP.md`, and `get_started_linux.sh` no longer exist; `terraform/terraform.tfvars` and `.env` are present and populated.

If any step fails, the script should exit with a clear error and leave you in a recoverable state.

### Step 4: Deploy

```bash
./deploy_and_update.sh
```

Expected:

- Step 1: "No existing Reasoning Engine found" (first deploy).
- Step 2: ADK deploys the agent. Takes 3-5 minutes. Output ends with a `reasoningEngines/<long-id>` resource name.
- Step 3: Smoke test creates a session against the new engine. Should print `OK`.
- Step 4: `register_agent.py` runs. Should detect Slack (`[OK] Slack: bot @smoke-test-agent ...`), write the Firestore doc, print `AGENT_ID=...`.
- Step 5: "No stale sessions to clear" (first deploy).
- Step 6: "No old Reasoning Engine to clean up" (first deploy).
- Final banner: "Deployment complete!"

### Step 5: Verify the agent's registered in The Forum's Firestore

```bash
gcloud firestore documents list agents --project=<FORUM_PROJECT_ID>
```

There should be a document with `display_name=Smoke Test Agent`, `vertex_ai_agent_id=projects/<test-project>/locations/us-central1/reasoningEngines/<id>`, and a `platforms` array containing a Slack entry.

### Step 6: Configure Slack Event Subscriptions

Back in your Slack app:

1. **Event Subscriptions** → Enable Events.
2. **Request URL**: `https://<your-forum-cloud-run-url>/api/v1/slack/events`. Wait for the green checkmark (verifies The Forum can sign-verify your test app's signing secret).
3. **Subscribe to bot events** → add `message.im`.
4. Save. If prompted to reinstall to workspace, do so.

### Step 7: Send a DM and verify the stub response

1. In Slack, find your test bot in the Apps sidebar.
2. Open a DM.
3. Send: `hello`.

**Expected response**:

> HI! I'm a new agent that is being created using the comites.ai template! I haven't been configured to do anything yet.

If you get exactly that text, the template works end-to-end. ✅

### Step 8: Test a redeploy

Make a trivial change (e.g., add a print statement to `agent.py`), then:

```bash
./deploy_and_update.sh
```

Expected:

- Step 1: Finds the existing Reasoning Engine.
- Step 6: Cleans up the OLD Reasoning Engine (not the new one).
- Sending another DM to the bot still works (and now hits the new engine).

This proves the blue/green logic.

### Step 9: Cleanup

```bash
# In smoke_test_agent/terraform
terraform destroy

# Delete the Reasoning Engine
gcloud ai reasoning-engines list --region=us-central1 --project=<test-project>
gcloud ai reasoning-engines delete <ENGINE_ID> --region=us-central1 --project=<test-project>

# (Optional) delete the state bucket
gcloud storage rm -r gs://<test-project>-tfstate

# Delete the Firestore record
# Use the Firestore console: agents collection → delete the Smoke Test Agent doc

# Delete the Slack app
# In api.slack.com/apps → your test app → Basic Information → Delete App

# Delete the local clone
cd .. && rm -rf smoke_test_agent
```

## Failure modes worth debugging before merging

If any of these happen during the test, fix on a branch before merging:

- **`get_started_linux.sh` fails partway through** and leaves the repo in a state where a re-run doesn't work cleanly. Idempotency matters — the operator should be able to fix the underlying issue and re-run.
- **`terraform apply` produces a 403 Permission Denied** that the script didn't catch in pre-flight. Add the missing pre-flight check.
- **`register_agent.py` says "No platform secrets found"** even though terraform apply succeeded. The secret-population step in `get_started_linux.sh` is broken.
- **The bot doesn't respond** but the Reasoning Engine is healthy. Most likely cause: The Forum's `SLACK_SIGNING_SECRET` doesn't include your test app's signing secret (or you didn't redeploy The Forum after adding it). Second most likely: missing IAM binding on the Slack token secret.
- **The bot replies but with the wrong text** (or with multiple messages). The stub instruction in `agent.py` is wrong, or the model is being chatty despite "always respond with this exact text".
- **Redeploy doesn't update the bot's behavior**. Either Firestore wasn't updated (check `vertex_ai_agent_id` in the agent doc) or stale sessions weren't cleared (check `sessions` collection in The Forum's Firestore for sessions still pointing at the old engine).

## Where to look when things break

```bash
# get_started_linux.sh output
# (re-run with `bash -x ./get_started_linux.sh` to see every command)

# terraform state
cd terraform && terraform show

# Reasoning Engine logs
gcloud logging read 'resource.type="aiplatform.googleapis.com/ReasoningEngine"' \
  --project=<test-project> --limit=50

# The Forum's Cloud Run logs
gcloud run services logs read the-forum \
  --project=<forum-project> --region=us-central1 --limit=50

# Firestore — agent registration
gcloud firestore documents list agents --project=<forum-project>

# Firestore — sessions for this agent
# (filter manually in the console; gcloud doesn't have a query filter for this)
```
