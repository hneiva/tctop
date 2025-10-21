"""Resource usage metrics parsing and computation."""

from typing import NamedTuple


# Field mappings derived from ./samples/resource-usage.json analysis
#
# Structure observed:
# - overall: aggregate statistics
#   - cpu_percent_mean: float (0-100 percentage) - example: 26.97
#   - io: array of integers (total IO counters) - example: [69, 68704, 1167360, 3862331392, ...]
#   - duration: float (seconds) - example: 625.38
# - system: system information
#   - vmem_total: integer (total system virtual memory in bytes) - example: 33652011008
# - samples: array of measurement objects (fallback if overall is unavailable)
#   - virt: array of integers per process - example: [33652011008, 31841796096, 5.4]


class TaskMetrics(NamedTuple):
    """Computed metrics for a task."""

    task_id: str
    label: str
    worker_type: str  # Worker type (e.g., "t-linux-docker-noscratch-amd")
    cpu_percent: float  # Average CPU percentage (0-100)
    virt_percent: float  # Virtual memory utilization as percentage of system total
    io_bytes_per_sec: float  # IO rate in bytes per second


class MetricsError(Exception):
    """Error computing metrics."""

    pass


def compute_metrics(task_id: str, label: str, worker_type: str, resource_data: dict) -> TaskMetrics:
    """
    Compute metrics from resource-usage.json data.

    Uses the 'overall' section for aggregated data:
    - CPU: overall.cpu_percent_mean (percentage 0-100)
    - Virtual Memory: average of samples[*].virt arrays as % of system.vmem_total
    - IO: sum of overall.io array / overall.duration for bytes per second

    Fallback to samples if overall is not available.

    Args:
        task_id: Task ID
        label: Human-friendly task label
        worker_type: Worker type
        resource_data: Parsed resource-usage.json content

    Returns:
        Computed metrics

    Raises:
        MetricsError: If required fields are missing or invalid
    """
    overall = resource_data.get("overall", {})
    system = resource_data.get("system", {})
    samples = resource_data.get("samples", [])

    # CPU: use overall.cpu_percent_mean
    cpu_percent = overall.get("cpu_percent_mean")
    if cpu_percent is None:
        # Fallback: average from samples
        cpu_values = []
        for sample in samples:
            cpu = sample.get("cpu_percent_mean")
            if cpu is not None and isinstance(cpu, (int, float)):
                cpu_values.append(float(cpu))

        if not cpu_values:
            raise MetricsError("No valid CPU data")
        cpu_percent = sum(cpu_values) / len(cpu_values)

    # Virtual Memory: compute average of all virt values from samples, then calculate % of system total
    virt_percent = 0.0
    vmem_total = system.get("vmem_total")

    if samples and vmem_total and vmem_total > 0:
        # Collect all virt values from all samples
        all_virt_values = []
        for sample in samples:
            virt = sample.get("virt")
            if virt and isinstance(virt, list):
                for v in virt:
                    if isinstance(v, (int, float)) and v > 0:
                        all_virt_values.append(float(v))

        if all_virt_values:
            avg_virt = sum(all_virt_values) / len(all_virt_values)
            virt_percent = (avg_virt / vmem_total) * 100

    if virt_percent == 0.0 and not samples:
        raise MetricsError("No valid virtual memory data")

    # IO: sum all values in overall.io array and divide by duration
    io_rate = 0.0
    io_array = overall.get("io")
    duration = overall.get("duration")

    if io_array and isinstance(io_array, list) and duration and duration > 0:
        total_io_bytes = sum(v for v in io_array if isinstance(v, (int, float)))
        io_rate = total_io_bytes / duration

    return TaskMetrics(
        task_id=task_id,
        label=label,
        worker_type=worker_type,
        cpu_percent=cpu_percent,
        virt_percent=virt_percent,
        io_bytes_per_sec=io_rate,
    )
