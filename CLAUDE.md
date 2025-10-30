# perfshepherd

Python CLI tool for analyzing Taskcluster resource usage metrics from test tasks.

## Project Structure

- **src/tc_resource_top/** - Main package containing the CLI application
- **scripts/** - Utility scripts for development and debugging
- **samples/** - Sample JSON files used for testing and field mapping verification
  - `profile_resource-usage.json` - Sample profile with threads/markers structure
  - `task.json` - Sample task definition
- **pyproject.toml** - UV/pip package configuration, defines `tc-top` CLI entry point
- **README.md** - User documentation with usage examples and field mappings

## Key Features

- Downloads task graphs from Taskcluster decision tasks
- Filters tasks by kind (regex), workerType (regex), and label (regex)
- Downloads `profile_resource-usage.json` artifacts from test tasks
- Parses profiler markers for CPU, Memory, and IO metrics
- Displays top N tasks per metric in formatted tables
- Shows per-task-type aggregations (avg/max for CPU, RAM, IO)
- Caches downloaded data in `/tmp/tc-top/<decision_task_id>/` for performance
- HTTP connection pooling for 97% faster execution with cache
- Dynamic worker pool based on CPU count

## Data Format

Uses `profile_resource-usage.json` with structure:
- `.threads[].markers.data[]` - Array of profiler markers
- Marker types: "CPU" (cpuPercent), "Mem" (used bytes), "IO" (read_bytes/write_bytes)

## Dependencies

Managed via UV package manager:
- taskcluster - Taskcluster API client
- orjson - Fast JSON parsing
- click - CLI framework
- requests - HTTP client with connection pooling

## CLI Entry Point

`tc-top` command is defined in pyproject.toml, points to `tc_resource_top.cli:cli`
