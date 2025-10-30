# tc-top

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

# Filter by workerType (regex pattern)
uv run tc-top <decision_task_id> --workerType '.*-amd'

# Filter by task label (regex pattern)
uv run tc-top <decision_task_id> --label '.*xpcshell.*'

# Filter by task kind (regex pattern, default: '^(test|mochitest)$')
uv run tc-top <decision_task_id> --kind '^test$'

# Skip cache and download fresh data
uv run tc-top <decision_task_id> --no-cache

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
3. Download `profile_resource-usage.json` artifacts concurrently from test tasks
4. Compute average CPU percent, virtual memory, and IO rate
5. Display three ranked tables showing the top tasks per metric
6. Display per-task-type aggregations with average and max values

**Note:** Taskcluster tasks and artifacts expire after a period of time (typically 1 year for artifacts). If you encounter "Task not found" or "Resource not found" errors, the decision task or its associated test tasks may have expired. Use a recent decision task ID from an active Taskcluster instance.

## Caching

The tool caches downloaded data to `/tmp/tc-top/<decision_task_id>/` for faster repeated access:

```
/tmp/tc-top/<decision_task_id>/
├── task-graph.json                    # Cached task graph
├── artifacts/<task_id>.json           # Cached artifact listings
└── metrics/<task_id>.json             # Cached profile_resource-usage.json files
```

### Cache Benefits
- **First run**: Downloads and caches all data (~3-4 seconds)
- **Subsequent runs**: Uses cached data (~0.7-0.9 seconds) - **~97% faster**
- **Artifact listing cache**: Avoids repeated API calls to `listLatestArtifacts()`
- **Connection pooling**: Reuses HTTP connections to avoid SSL handshake overhead

### Cache Management
```bash
# Skip cache and force fresh download
uv run tc-top <decision_task_id> --no-cache

# Clear cache for a specific decision task
rm -rf /tmp/tc-top/<decision_task_id>

# Clear all cached data
rm -rf /tmp/tc-top
```

### Performance
With caching and connection pooling enabled:
- **Without cache**: 27s → 3.3s (87% faster)
- **With cache**: 27s → 0.8s (97% faster)

The combination of HTTP connection pooling and artifact listing caching provides exceptional performance for iterative analysis workflows.

## Field Mapping

This tool's implementation is based on analysis of sample files in `./samples/`:

### From `task-graph.json`
- **Task kind filter**: `kind == "test"` or `"mochitest"`
  - The task graph is a dictionary where keys are task IDs
  - Each entry contains a `kind` field identifying the task type
  - This identifies test tasks (as opposed to build, decision, or other task types)
  - The tool downloads `public/task-graph.json` from the decision task for efficient filtering

### From `profile_resource-usage.json`
The profile resource usage file contains profiler markers with resource measurements:

- **CPU Percent**: `.threads[].markers.data[]` where `type == "CPU"`
  - Field: `cpuPercent` as string (e.g., "6.5%")
  - Type: String percentage
  - Computed as: Average of all CPU marker values

- **Virtual Memory**: `.threads[].markers.data[]` where `type == "Mem"`
  - Field: `used` (bytes used)
  - Type: Integer (bytes)
  - Example: `1293303808` (≈ 1.2 GiB)
  - System total estimated from `cached` and `buffers` fields
  - Computed as: Average memory used as percentage of system total

- **IO**: `.threads[].markers.data[]` where `type == "IO"`
  - Fields: `read_bytes` and `write_bytes`
  - Type: Integer (bytes)
  - Computed as: Sum of all read_bytes and write_bytes divided by time span
  - Time span calculated from `.threads[].markers.startTime` and `endTime` arrays

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
