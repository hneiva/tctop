"""Taskcluster API interactions."""

from typing import Iterator, Optional
import gzip
import io

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import taskcluster
import orjson

from tc_resource_top import cache


# Global session with connection pooling
_session = None


def get_session() -> requests.Session:
    """
    Get or create a shared requests session with connection pooling.

    Configures connection pooling to reuse connections and avoid
    repeated SSL handshakes, which are expensive (~0.9s each).

    Returns:
        Configured requests.Session with connection pooling
    """
    global _session
    if _session is None:
        _session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,  # Number of connection pools to cache
            pool_maxsize=30,      # Max connections per pool
            max_retries=retry_strategy,
            pool_block=False,
        )

        # Mount adapter for both http and https
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)

    return _session


def get_task_graph(queue: taskcluster.Queue, decision_task_id: str, use_cache: bool = True) -> dict:
    """
    Download and parse the task-graph.json from a decision task.

    Args:
        queue: Taskcluster Queue client
        decision_task_id: The decision task ID
        use_cache: Whether to use cache (default: True)

    Returns:
        Parsed task graph data

    Raises:
        Exception: If task graph cannot be downloaded or parsed
    """
    # Try cache first
    if use_cache:
        cache_path = cache.get_task_graph_path(decision_task_id)
        cached_data = cache.load_from_cache(cache_path)
        if cached_data is not None:
            return cached_data

    # Download from Taskcluster
    artifact_name = "public/task-graph.json"
    task_graph = download_artifact(queue, decision_task_id, artifact_name)

    if task_graph is None:
        raise Exception("Failed to download task-graph.json from decision task")

    # Save to cache
    if use_cache:
        cache_path = cache.get_task_graph_path(decision_task_id)
        cache.save_to_cache(cache_path, task_graph)

    return task_graph


def get_test_tasks_from_graph(task_graph: dict, kind_pattern: str = "^(test|mochitest)$") -> list[dict]:
    """
    Extract test tasks from a task graph.

    The task graph structure is a dict where keys are task IDs and values
    contain task definitions with a 'kind' field and 'label' field.

    Args:
        task_graph: Parsed task-graph.json content
        kind_pattern: Regex pattern to match task kinds (default: "test|mochitest")

    Returns:
        List of dicts with 'task_id', 'label', 'kind', and 'worker_type' for matching tasks
    """
    import re

    test_tasks = []
    kind_regex = re.compile(kind_pattern)

    for task_id, task_data in task_graph.items():
        # Skip if not a task entry
        if not isinstance(task_data, dict):
            continue

        # Check if kind matches pattern
        kind = task_data.get("kind", "")
        if not kind_regex.search(kind):
            continue

        # Get the label
        label = task_data.get("label", task_id)

        # Get workerType from task definition
        task_def = task_data.get("task", {})
        worker_type = task_def.get("workerType", "")

        test_tasks.append({
            "task_id": task_id,
            "label": label,
            "kind": kind,
            "worker_type": worker_type,
        })

    return test_tasks


def find_resource_usage_artifact(
    queue: taskcluster.Queue,
    task_id: str,
    decision_task_id: Optional[str] = None,
    use_cache: bool = True
) -> str | None:
    """
    Find the resource-usage.json artifact for a task.

    Args:
        queue: Taskcluster Queue client
        task_id: The task ID
        decision_task_id: Optional decision task ID for cache path
        use_cache: Whether to use cache (default: True)

    Returns:
        The artifact name, or None if not found
    """
    # Try cache first
    if use_cache and decision_task_id:
        cache_path = cache.get_artifacts_path(decision_task_id, task_id)
        cached_artifacts = cache.load_from_cache(cache_path)
        if cached_artifacts is not None:
            artifacts = cached_artifacts
        else:
            # Fetch from API
            try:
                artifacts = queue.listLatestArtifacts(task_id)
                # Save to cache
                cache.save_to_cache(cache_path, artifacts)
            except Exception:
                return None
    else:
        # No cache, fetch from API
        try:
            artifacts = queue.listLatestArtifacts(task_id)
        except Exception:
            return None

    # Look for resource-usage.json (case-insensitive)
    candidates = []
    for artifact in artifacts.get("artifacts", []):
        name = artifact.get("name", "")
        if "resource-usage.json" in name.lower():
            candidates.append(name)

    if not candidates:
        return None

    # Prefer exact match: /resource-usage.json (not prefixed with other words)
    for candidate in candidates:
        # Check if it ends with /resource-usage.json or is exactly resource-usage.json
        if candidate.endswith("/resource-usage.json") or candidate == "resource-usage.json":
            return candidate

    # Fallback: shortest name
    return min(candidates, key=len)


def download_artifact(
    queue: taskcluster.Queue,
    task_id: str,
    artifact_name: str,
    decision_task_id: Optional[str] = None,
    use_cache: bool = True,
) -> dict | None:
    """
    Download and parse an artifact.

    Supports gzip compression transparently and caching for resource-usage.json.

    Args:
        queue: Taskcluster Queue client
        task_id: The task ID
        artifact_name: The artifact name
        decision_task_id: Optional decision task ID for cache path (required for caching)
        use_cache: Whether to use cache (default: True)

    Returns:
        Parsed JSON data, or None on error
    """
    # Try cache for resource-usage.json if decision_task_id provided
    if use_cache and decision_task_id and "resource-usage.json" in artifact_name.lower():
        cache_path = cache.get_metrics_path(decision_task_id, task_id)
        cached_data = cache.load_from_cache(cache_path)
        if cached_data is not None:
            return cached_data

    # Download from Taskcluster using shared session with connection pooling
    try:
        url = queue.buildUrl("getLatestArtifact", task_id, artifact_name)
        session = get_session()
        response = session.get(url, timeout=30)
        response.raise_for_status()

        content = response.content

        # Check if gzipped
        if artifact_name.endswith(".gz") or content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)

        data = orjson.loads(content)

        # Save to cache for resource-usage.json
        if use_cache and decision_task_id and "resource-usage.json" in artifact_name.lower():
            cache_path = cache.get_metrics_path(decision_task_id, task_id)
            cache.save_to_cache(cache_path, data)

        return data
    except Exception:
        return None
