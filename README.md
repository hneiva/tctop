# tc-resource-top

A CLI tool for analyzing Taskcluster resource usage metrics. Given a decision task ID, it finds test tasks in the task group, downloads their `resource-usage.json` artifacts, and displays the top N tasks by CPU, virtual memory, and IO rate.

## Quick Start

### Installation with UV

1. Create a virtual environment:
   ```bash
   uv venv
   ```

2. Install the package in editable mode:
   ```bash
   uv pip install -e .
   ```

3. Verify installation:
   ```bash
   uv run tc-top --help
   ```

### Usage

```bash
# Basic usage with default settings (top 10 tasks)
uv run tc-top <decision_task_id>

# Show top 20 tasks per metric
uv run tc-top <decision_task_id> --records 20

# Use a different Taskcluster instance
uv run tc-top <decision_task_id> --root-url https://taskcluster.example.com
```

### Example

```bash
uv run tc-top WSaQdVPaTCGDBPiYr1X07g
```

This will:
1. Download the `task-graph.json` from the decision task
2. Extract all tasks with kind "test" from the task graph
3. Download `resource-usage.json` artifacts concurrently from test tasks
4. Compute average CPU percent, virtual memory, and IO rate
5. Display three ranked tables showing the top tasks per metric

**Note:** Taskcluster tasks and artifacts expire after a period of time (typically 1 year for artifacts). If you encounter "Task not found" or "Resource not found" errors, the decision task or its associated test tasks may have expired. Use a recent decision task ID from an active Taskcluster instance.

## Field Mapping

This tool's implementation is based on analysis of sample files in `./samples/`:

### From `task-graph.json`
- **Task kind filter**: `kind == "test"`
  - The task graph is a dictionary where keys are task IDs
  - Each entry contains a `kind` field identifying the task type
  - Example value: `"test"`
  - This identifies test tasks (as opposed to build, decision, or other task types)
  - The tool downloads `public/task-graph.json` from the decision task for efficient filtering

### From `resource-usage.json`
The resource usage file contains an array of samples, each with measurements:

- **CPU Percent**: `samples[*].cpu_percent_mean`
  - Type: Float (0-100 percentage)
  - Example: `12.5` means 12.5% CPU usage
  - Computed as: Mean of all sample values

- **Virtual Memory**: `samples[*].virt[0]`
  - Type: Integer (bytes)
  - Example: `33652011008` (≈ 31.3 GiB)
  - The `virt` field is an array; we use the first element (process virtual memory size)
  - Computed as: Mean of all sample values

- **IO Counters**: `samples[*].io[2]` (read_bytes) and `samples[*].io[3]` (write_bytes)
  - Type: Integer (bytes, cumulative counters)
  - Example: `[1, 0, 4096, 8192, ...]` → read_bytes=4096, write_bytes=8192
  - These are **cumulative** counters that increase over time
  - Computed as: `(Δread_bytes + Δwrite_bytes) / Δtime` using first and last samples
  - Timestamps from `samples[*].start` and `samples[*].end`

## Output Format

The tool displays three tables:

```
Top CPU (%) — Top 10
───────────────────────────────────────────────────────────────
 1          93.4 %  TQas1cd   mochitest-plain-1 (linux64)
 2          91.8 %  ZYx9pqr   xpcshell-2 (linux64)
...

Top Virtual Memory — Top 10
───────────────────────────────────────────────────────────────
 1        31.3 GiB  TQas1cd   mochitest-plain-1 (linux64)
...

Top IO (bytes/sec) — Top 10
───────────────────────────────────────────────────────────────
 1      45.2 MiB/s  TQas1cd   mochitest-plain-1 (linux64)
...
```

Units:
- CPU: Percentage with one decimal place
- Memory: Binary units (B, KiB, MiB, GiB, TiB)
- IO: Binary units per second (B/s, KiB/s, MiB/s, etc.)

## Dependencies

This project uses only the specified dependencies:
- `taskcluster` - Taskcluster client library
- `orjson` - Fast JSON parsing
- `click` - CLI framework
- `requests` - HTTP client for artifact downloads

## Project Structure

```
perfshepherd/
├── pyproject.toml
├── README.md
├── samples/
│   ├── resource-usage.json
│   └── task.json
├── scripts/
│   └── print_field_map.py
└── src/
    └── tc_resource_top/
        ├── __init__.py
        ├── api.py          # Taskcluster API interactions
        ├── cli.py          # CLI entry point
        ├── formatting.py   # Output formatting utilities
        └── metrics.py      # Metrics computation logic
```
