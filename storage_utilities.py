"""
Cloud Storage read helper for inbound files (user-uploaded attachments).

The Forum uploads files users send your agent to its own GCS bucket and
references them in the message text as `[IMAGE: gs://... | mime]`. Use
`download_uploaded_file()` from your tools to fetch the bytes — do NOT
construct a bare `storage.Client()` yourself.

Why the bare client fails
-------------------------
The deployed engine runs inside The Forum's project, so ADC bills GCS
calls there — but the per-agent SA holds
`roles/serviceusage.serviceUsageConsumer` only on its OWN project (the
`agent_serviceusage_consumer` binding in terraform/main.tf). A bare
client therefore 403s with:

    ... does not have serviceusage.services.use access to the Google
    Cloud project. Permission 'serviceusage.services.use' denied

The request dies at billing before the object ACL is consulted, so the
error appears regardless of whether the bucket IAM is correct. The fix
is the same quota-project pinning `docs_utilities.py` does for the
Workspace APIs: bill the call to the agent's own project.

Both prerequisites ship with this template:
  - the bucket grant in terraform/main.tf (`engine_inbound_files_reader`)
  - AGENT_PROJECT_ID in .env (written by get_started_linux.sh)

Testing caveat
--------------
The quota-project failure does NOT reproduce locally: impersonated or
gcloud-user credentials carry no quota project, so the exact call that
403s in the deployed engine succeeds on a dev machine. "It works with
the SA's credentials locally" proves the IAM grants, not this code path.
Verify changes to this module against a deployed Reasoning Engine.
"""
import os
from typing import Optional, Tuple

import google.auth
from google.cloud import storage


def _build_storage_client() -> storage.Client:
    credentials, _ = google.auth.default()
    agent_project = os.environ.get("AGENT_PROJECT_ID")
    # Bill GCS calls to the agent's own project, where the SA has
    # serviceusage.serviceUsageConsumer, instead of the Forum project the
    # engine runs in, where it deliberately has no such grant.
    if agent_project and hasattr(credentials, "with_quota_project"):
        credentials = credentials.with_quota_project(agent_project)
    return storage.Client(project=agent_project or None, credentials=credentials)


# Process-wide cached client, mirroring docs_utilities.get_docs_connector().
_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    """Return a process-wide cached, quota-project-pinned storage client."""
    global _client
    if _client is None:
        _client = _build_storage_client()
    return _client


def parse_gcs_uri(gcs_uri: str) -> Tuple[str, str]:
    """Split a `gs://bucket/path/to/object` URI into (bucket, object)."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Not a gs:// URI: {gcs_uri!r}")
    bucket, _, blob = gcs_uri[len("gs://"):].partition("/")
    if not bucket or not blob:
        raise ValueError(f"Malformed gs:// URI (need gs://bucket/object): {gcs_uri!r}")
    return bucket, blob


def download_uploaded_file(gcs_uri: str) -> bytes:
    """
    Download an inbound file (user-uploaded attachment) from GCS.

    Args:
        gcs_uri: The `gs://bucket/object` reference The Forum embedded in
            the message text (e.g. from an `[IMAGE: gs://... | mime]` tag).

    Returns:
        The object's raw bytes.

    Raises:
        ValueError: if `gcs_uri` is not a well-formed gs:// URI.
        google.api_core.exceptions.Forbidden: if the per-agent SA lacks
            read access on the bucket (see `engine_inbound_files_reader`
            in terraform/main.tf) — or, if the message mentions
            `serviceusage.services.use`, the quota project isn't pinned
            (AGENT_PROJECT_ID unset; see module docstring).
        google.api_core.exceptions.NotFound: if the object has expired —
            The Forum's inbound-files bucket has a 1-day lifecycle, so
            stale references stop resolving.
    """
    bucket, blob = parse_gcs_uri(gcs_uri)
    return get_storage_client().bucket(bucket).blob(blob).download_as_bytes()
