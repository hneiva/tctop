"""Resource usage metrics parsing and computation."""

from typing import NamedTuple


# Field mappings derived from ./samples/profile_resource-usage.json analysis
#
# Structure observed:
# - threads: array of thread objects
#   - markers: marker data structure
#     - data: array of marker objects with type-specific fields
#       - type: "CPU" | "Mem" | "IO"
#       - CPU markers: cpuPercent as string (e.g., "6.5%")
#       - Mem markers: used (bytes as integer)
#       - IO markers: read_bytes, write_bytes (integers)


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
    Compute metrics from profile_resource-usage.json data.

    Parses .threads[].markers.data array to extract:
    - CPU: markers with type == "CPU" -> cpuPercent (string like "6.5%")
    - Memory: markers with type == "Mem" -> used (bytes)
    - IO: markers with type == "IO" -> sum(read_bytes, write_bytes)

    Args:
        task_id: Task ID
        label: Human-friendly task label
        worker_type: Worker type
        resource_data: Parsed profile_resource-usage.json content

    Returns:
        Computed metrics

    Raises:
        MetricsError: If required fields are missing or invalid
    """
    # Extract all markers from all threads
    threads = resource_data.get("threads", [])
    if not threads:
        raise MetricsError("No threads found in profile data")

    cpu_values = []
    mem_values = []
    io_bytes_values = []

    # Get system memory total for calculating percentage
    # We'll use the meta section or calculate from mem markers
    meta = resource_data.get("meta", {})
    system_mem_total = None

    for thread in threads:
        markers = thread.get("markers", {})
        marker_data = markers.get("data", [])

        for marker in marker_data:
            marker_type = marker.get("type")

            if marker_type == "CPU":
                # Parse cpuPercent string (e.g., "6.5%")
                cpu_str = marker.get("cpuPercent", "")
                if cpu_str:
                    try:
                        # Remove % sign and convert to float
                        cpu_val = float(cpu_str.rstrip("%"))
                        cpu_values.append(cpu_val)
                    except (ValueError, AttributeError):
                        pass

            elif marker_type == "Mem":
                # Memory used in bytes
                mem_used = marker.get("used")
                if mem_used is not None and isinstance(mem_used, (int, float)):
                    mem_values.append(float(mem_used))

                # Try to get total memory from cached field if available
                if system_mem_total is None:
                    cached = marker.get("cached")
                    buffers = marker.get("buffers")
                    if mem_used and cached and buffers:
                        # Estimate total as used + cached + buffers (rough approximation)
                        system_mem_total = mem_used + cached + buffers

            elif marker_type == "IO":
                # Sum read and write bytes
                read_bytes = marker.get("read_bytes", 0)
                write_bytes = marker.get("write_bytes", 0)
                if isinstance(read_bytes, (int, float)) and isinstance(write_bytes, (int, float)):
                    io_bytes_values.append(float(read_bytes + write_bytes))

    # Compute average CPU percentage
    if not cpu_values:
        raise MetricsError("No valid CPU data")
    cpu_percent = sum(cpu_values) / len(cpu_values)

    # Compute average memory usage and convert to percentage
    if not mem_values:
        raise MetricsError("No valid memory data")
    avg_mem_used = sum(mem_values) / len(mem_values)

    # Convert to percentage - if we have system total, use it, otherwise report as 0
    virt_percent = 0.0
    if system_mem_total and system_mem_total > 0:
        virt_percent = (avg_mem_used / system_mem_total) * 100
    else:
        # Fallback: assume typical system has ~32GB RAM
        virt_percent = (avg_mem_used / (32 * 1024 * 1024 * 1024)) * 100

    # Compute average IO rate (bytes per second)
    # We need to calculate the time span
    io_bytes_per_sec = 0.0
    if io_bytes_values:
        # Get time span from markers
        if threads and threads[0].get("markers"):
            start_times = threads[0]["markers"].get("startTime", [])
            end_times = threads[0]["markers"].get("endTime", [])

            if start_times and end_times:
                # Filter out None values and calculate duration
                valid_start_times = [t for t in start_times if t is not None]
                valid_end_times = [t for t in end_times if t is not None]

                if valid_start_times and valid_end_times:
                    min_start = min(valid_start_times)
                    max_end = max(valid_end_times)
                    duration = (max_end - min_start) / 1000.0  # Convert ms to seconds

                    if duration > 0:
                        # Calculate rate: total bytes / duration
                        total_io_bytes = sum(io_bytes_values)
                        io_bytes_per_sec = total_io_bytes / duration

    return TaskMetrics(
        task_id=task_id,
        label=label,
        worker_type=worker_type,
        cpu_percent=cpu_percent,
        virt_percent=virt_percent,
        io_bytes_per_sec=io_bytes_per_sec,
    )
