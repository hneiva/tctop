"""CLI entry point for tc-top."""

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import click
import taskcluster

from tc_resource_top import api, metrics, formatting


def process_task(
    queue: taskcluster.Queue, task_info: dict, decision_task_id: str, use_cache: bool
) -> tuple[str, str, str, dict | None]:
    """
    Process a single task: find and download resource-usage.json.

    Args:
        queue: Taskcluster Queue client
        task_info: Dict with 'task_id', 'label', and 'worker_type' keys
        decision_task_id: Decision task ID for cache path
        use_cache: Whether to use cache

    Returns:
        Tuple of (task_id, label, worker_type, resource_data or None)
    """
    task_id = task_info["task_id"]
    label = task_info["label"]
    worker_type = task_info.get("worker_type", "")

    artifact_name = api.find_resource_usage_artifact(
        queue, task_id, decision_task_id=decision_task_id, use_cache=use_cache
    )
    if not artifact_name:
        return (task_id, label, worker_type, None)

    resource_data = api.download_artifact(
        queue, task_id, artifact_name, decision_task_id=decision_task_id, use_cache=use_cache
    )
    return (task_id, label, worker_type, resource_data)


@click.command()
@click.argument("decision_task_id")
@click.option(
    "--records",
    "-n",
    type=int,
    default=10,
    help="Number of top tasks to display per metric (default: 10)",
)
@click.option(
    "--root-url",
    default="https://firefox-ci-tc.services.mozilla.com",
    help="Taskcluster root URL (default: Firefox CI)",
)
@click.option(
    "--kind",
    type=str,
    default="^(test|mochitest)$",
    help="Filter tasks by kind (regex pattern, default: 'test|mochitest')",
)
@click.option(
    "--workerType",
    type=str,
    default=None,
    help="Filter tasks by workerType (regex pattern, e.g., '.*-amd')",
)
@click.option(
    "--label",
    type=str,
    default=None,
    help="Filter tasks by label (regex pattern, e.g., '.*xpcshell.*')",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Skip using cache and download all data fresh from Taskcluster",
)
def cli(decision_task_id: str, records: int, root_url: str, kind: str, workertype: str, label: str, no_cache: bool) -> None:
    """
    Analyze Taskcluster resource usage for test tasks.

    Given a DECISION_TASK_ID, finds the associated task group, filters to
    tasks of kind "test", downloads resource-usage.json artifacts, computes
    average CPU percent, virtual memory, and IO rate, and displays the top N
    tasks per metric.
    """
    start_time = time.time()

    try:
        # Initialize Taskcluster Queue with shared session for connection pooling
        session = api.get_session()
        queue = taskcluster.Queue({"rootUrl": root_url}, session=session)

        # Determine cache usage
        use_cache = not no_cache

        # Download task graph from decision task
        click.echo(f"Downloading task graph from decision task {decision_task_id}...")
        task_graph = api.get_task_graph(queue, decision_task_id, use_cache=use_cache)

        # Extract test tasks from graph
        click.echo("Extracting tasks from task graph...")
        try:
            test_tasks = api.get_test_tasks_from_graph(task_graph, kind_pattern=kind)
        except re.error as e:
            click.echo(f"Invalid regex pattern for --kind '{kind}': {e}", err=True)
            sys.exit(1)

        click.echo(f"Found {len(test_tasks)} tasks matching kind pattern '{kind}'")

        # Filter by workerType if specified
        if workertype:
            try:
                worker_pattern = re.compile(workertype)
                filtered_tasks = []
                for task in test_tasks:
                    worker_type = task.get("worker_type", "")
                    if worker_pattern.search(worker_type):
                        filtered_tasks.append(task)

                click.echo(f"Filtered to {len(filtered_tasks)} tasks matching workerType pattern '{workertype}'")
                test_tasks = filtered_tasks
            except re.error as e:
                click.echo(f"Invalid regex pattern '{workertype}': {e}", err=True)
                sys.exit(1)

        # Filter by label if specified
        if label:
            try:
                label_pattern = re.compile(label)
                filtered_tasks = []
                for task in test_tasks:
                    task_label = task.get("label", "")
                    if label_pattern.search(task_label):
                        filtered_tasks.append(task)

                click.echo(f"Filtered to {len(filtered_tasks)} tasks matching label pattern '{label}'")
                test_tasks = filtered_tasks
            except re.error as e:
                click.echo(f"Invalid regex pattern '{label}': {e}", err=True)
                sys.exit(1)

        if not test_tasks:
            click.echo("No test tasks found matching criteria", err=True)
            sys.exit(1)

        # Download artifacts concurrently
        click.echo("Downloading resource usage artifacts...")
        all_metrics: List[metrics.TaskMetrics] = []

        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {
                executor.submit(process_task, queue, task_info, decision_task_id, use_cache): task_info
                for task_info in test_tasks
            }

            for future in as_completed(futures):
                task_id, label, worker_type, resource_data = future.result()

                if resource_data is None:
                    click.echo(f"! Skipping {task_id}: no resource-usage.json", err=True)
                    continue

                try:
                    task_metrics = metrics.compute_metrics(task_id, label, worker_type, resource_data)
                    all_metrics.append(task_metrics)
                except metrics.MetricsError as e:
                    click.echo(f"! Skipping {task_id}: {e}", err=True)

        if not all_metrics:
            click.echo("No metrics computed (all tasks skipped)", err=True)
            sys.exit(1)

        click.echo(f"Computed metrics for {len(all_metrics)} tasks\n")

        # Sort and display rankings
        # Sort by each metric (descending), with task_id as tiebreaker for determinism
        cpu_top = sorted(
            all_metrics, key=lambda m: (-m.cpu_percent, m.task_id)
        )
        virt_top = sorted(
            all_metrics, key=lambda m: (-m.virt_percent, m.task_id)
        )
        io_top = sorted(
            all_metrics, key=lambda m: (-m.io_bytes_per_sec, m.task_id)
        )

        formatting.print_top_metrics(cpu_top, virt_top, io_top, records)

        # Print execution time
        elapsed_time = time.time() - start_time
        click.echo(f"Execution time: {elapsed_time:.2f}s")

    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
