# src/

Source code for the `tc-resource-top` package.

## tc_resource_top/

Main package containing all application modules:

- **cli.py** - Click-based CLI entry point (`tc-top` command). Orchestrates the workflow: downloads task graph, filters tasks, downloads artifacts concurrently using ThreadPoolExecutor (12 workers), computes metrics, and displays ranked output. Handles all CLI options: --records, --root-url, --kind, --workerType, --label, --no-cache.

- **api.py** - Taskcluster API interactions. Functions for downloading task-graph.json from decision tasks, extracting test tasks by kind pattern (regex), finding resource-usage.json artifacts, and downloading artifacts with caching support. Uses requests library for HTTP and taskcluster.Queue for API interactions.

- **cache.py** - Filesystem caching utilities. Manages cache structure in `/tmp/perfshepherd/<decision_task_id>/` with task-graph.json and metrics/<task_id>.json. Uses orjson for fast serialization. Includes load/save functions and cache path helpers.

- **metrics.py** - Resource usage metrics computation. Parses resource-usage.json to compute CPU % (from overall.cpu_percent_mean), virtual memory % (avg of samples[*].virt as % of system.vmem_total), and IO bytes/sec (sum of overall.io[] / overall.duration). Defines TaskMetrics NamedTuple and MetricsError exception.

- **formatting.py** - Output display formatting. Functions for formatting bytes (binary units: KiB, MiB, GiB), CPU percentages, and bytes/sec rates. Prints ranked tables with aligned columns showing task ID (shortened), label, and metric values.

## Implementation Notes

- Uses concurrent.futures.ThreadPoolExecutor for parallel artifact downloads
- All filters (kind, workerType, label) support regex patterns
- Caching is transparent - cache hits avoid network requests
- Error handling skips tasks without resource-usage.json artifacts
- Task IDs are shortened to 7 characters for display
