"""Formatting utilities for output display."""

from typing import List
from tc_resource_top.metrics import TaskMetrics


def format_bytes(num_bytes: float) -> str:
    """
    Format bytes using binary units (KiB, MiB, GiB, TiB).

    Args:
        num_bytes: Number of bytes

    Returns:
        Formatted string with one decimal place and unit
    """
    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"

    num_bytes /= 1024.0
    if num_bytes < 1024:
        return f"{num_bytes:.1f} KiB"

    num_bytes /= 1024.0
    if num_bytes < 1024:
        return f"{num_bytes:.1f} MiB"

    num_bytes /= 1024.0
    if num_bytes < 1024:
        return f"{num_bytes:.1f} GiB"

    num_bytes /= 1024.0
    return f"{num_bytes:.1f} TiB"


def format_bytes_per_sec(bytes_per_sec: float) -> str:
    """
    Format bytes per second using binary units.

    Args:
        bytes_per_sec: Bytes per second

    Returns:
        Formatted string with unit suffix /s
    """
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"

    bytes_per_sec /= 1024.0
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} KiB/s"

    bytes_per_sec /= 1024.0
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} MiB/s"

    bytes_per_sec /= 1024.0
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} GiB/s"

    bytes_per_sec /= 1024.0
    return f"{bytes_per_sec:.1f} TiB/s"


def format_cpu_percent(percent: float) -> str:
    """
    Format CPU percentage with one decimal place.

    Args:
        percent: CPU percentage (0-100)

    Returns:
        Formatted string with % suffix
    """
    return f"{percent:.1f} %"


def shorten_task_id(task_id: str, length: int = 7) -> str:
    """
    Shorten a task ID for display.

    Args:
        task_id: Full task ID
        length: Number of characters to keep

    Returns:
        Shortened task ID
    """
    return task_id[:length]


def print_ranking_table(
    title: str,
    metrics_list: List[TaskMetrics],
    metric_name: str,
    format_func,
    top_n: int,
) -> None:
    """
    Print a ranking table for a specific metric.

    Args:
        title: Table title
        metrics_list: List of TaskMetrics sorted by the metric (descending)
        metric_name: Attribute name of the metric to display
        format_func: Function to format the metric value
        top_n: Number of top entries to display
    """
    print(f"\n{title} — Top {top_n}")
    print("─" * 120)

    for rank, m in enumerate(metrics_list[:top_n], start=1):
        metric_value = getattr(m, metric_name)
        formatted_value = format_func(metric_value)

        # Format: rank, value, task_id (full), worker_type, label
        print(f"{rank:2d}  {formatted_value:>15s}  {m.task_id}  {m.worker_type:35s}  {m.label}")


def format_percent(percent: float) -> str:
    """
    Format a percentage with one decimal place.

    Args:
        percent: Percentage value

    Returns:
        Formatted string with % suffix
    """
    return f"{percent:.1f} %"


def print_top_metrics(
    cpu_top: List[TaskMetrics],
    virt_top: List[TaskMetrics],
    io_top: List[TaskMetrics],
    top_n: int,
) -> None:
    """
    Print all three ranking tables.

    Args:
        cpu_top: List of metrics sorted by CPU (descending)
        virt_top: List of metrics sorted by virtual memory (descending)
        io_top: List of metrics sorted by IO (descending)
        top_n: Number of top entries to display
    """
    print_ranking_table("Top CPU (%)", cpu_top, "cpu_percent", format_cpu_percent, top_n)
    print_ranking_table("Top Virtual Memory (%)", virt_top, "virt_percent", format_percent, top_n)
    print_ranking_table("Top IO (bytes/sec)", io_top, "io_bytes_per_sec", format_bytes_per_sec, top_n)
    print()  # Add blank line at end
