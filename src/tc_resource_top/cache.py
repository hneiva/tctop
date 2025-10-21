"""Caching utilities for downloaded Taskcluster data."""

import json
from pathlib import Path
from typing import Optional

import orjson


CACHE_ROOT = Path("/tmp/perfshepherd")


def get_cache_dir(decision_task_id: str, subdir: Optional[str] = None) -> Path:
    """
    Get the cache directory for a decision task.

    Args:
        decision_task_id: The decision task ID
        subdir: Optional subdirectory (e.g., 'definition', 'metrics')

    Returns:
        Path to cache directory
    """
    cache_dir = CACHE_ROOT / decision_task_id
    if subdir:
        cache_dir = cache_dir / subdir
    return cache_dir


def get_task_graph_path(decision_task_id: str) -> Path:
    """
    Get the cache path for a task graph.

    Args:
        decision_task_id: The decision task ID

    Returns:
        Path to cached task-graph.json
    """
    return get_cache_dir(decision_task_id) / "task-graph.json"


def get_metrics_path(decision_task_id: str, task_id: str) -> Path:
    """
    Get the cache path for task metrics (resource-usage.json).

    Args:
        decision_task_id: The decision task ID
        task_id: The task ID

    Returns:
        Path to cached resource-usage.json
    """
    return get_cache_dir(decision_task_id, "metrics") / f"{task_id}.json"


def load_from_cache(cache_path: Path) -> Optional[dict]:
    """
    Load data from cache if it exists.

    Args:
        cache_path: Path to cached file

    Returns:
        Parsed JSON data, or None if cache doesn't exist or is invalid
    """
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "rb") as f:
            return orjson.loads(f.read())
    except Exception:
        # Cache file is corrupted or invalid
        return None


def save_to_cache(cache_path: Path, data: dict) -> None:
    """
    Save data to cache.

    Args:
        cache_path: Path to cache file
        data: Data to cache
    """
    try:
        # Create parent directories
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Write data
        with open(cache_path, "wb") as f:
            f.write(orjson.dumps(data))
    except Exception:
        # Silently fail on cache write errors
        pass


def clear_cache(decision_task_id: Optional[str] = None) -> None:
    """
    Clear cache for a specific decision task or all cached data.

    Args:
        decision_task_id: Optional decision task ID. If None, clears all cache.
    """
    import shutil

    if decision_task_id:
        cache_dir = get_cache_dir(decision_task_id)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
    else:
        if CACHE_ROOT.exists():
            shutil.rmtree(CACHE_ROOT)
