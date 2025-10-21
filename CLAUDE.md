# perfshepherd

Python CLI tool for analyzing Taskcluster resource usage metrics from test tasks.

## Project Structure

- **src/tc_resource_top/** - Main package containing the CLI application
- **scripts/** - Utility scripts for development and debugging
- **samples/** - Sample JSON files used for testing and field mapping verification
- **pyproject.toml** - UV/pip package configuration, defines `tc-top` CLI entry point
- **README.md** - User documentation with usage examples and field mappings

## Key Features

- Downloads task graphs from Taskcluster decision tasks
- Filters tasks by kind (regex), workerType (regex), and label (regex)
- Computes metrics: CPU %, virtual memory %, IO bytes/sec
- Displays top N tasks per metric in formatted tables
- Caches downloaded data in `/tmp/perfshepherd/<decision_task_id>/` for performance
- Supports `--no-cache` flag to bypass caching

## Dependencies

Managed via UV package manager:
- taskcluster - Taskcluster API client
- orjson - Fast JSON parsing
- click - CLI framework
- requests - HTTP client for artifact downloads

## CLI Entry Point

`tc-top` command is defined in pyproject.toml, points to `tc_resource_top.cli:cli`
