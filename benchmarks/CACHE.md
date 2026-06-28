# Cache & Benchmark Consistency

Mnemo caches search results for 5 minutes (query_cache table in SQLite).

## Cold vs Warm Cache

| State | Source | Typical latency |
|-------|--------|-----------------|
| Cold | First query after daemon start | 30-50 ms |
| Warm | Repeated query within 5 min | 0-1 ms |

## Running a Cold-Cache Benchmark

Restart the daemon before the run:

```powershell
# 1. Kill existing daemon (Ctrl+C or taskkill)
# 2. Start fresh
mnemo daemon

# 3. In another terminal, run benchmark
python benchmark.py
```

## Why This Matters

- Never mix cold and warm results in the same comparison.
- Mark each result file (`benchmarks/results/YYYY-MM-DD.json`) with cache state.
- If a query shows 0 ms latency, it came from cache — exclude it from latency averages.
