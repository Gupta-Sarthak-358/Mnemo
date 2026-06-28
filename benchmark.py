"""Retrieval benchmark for Mnemo.

Usage:
    python benchmark.py                           # queries_v2.json
    python benchmark.py --queries queries_v1.json

Note: Results may be warm-cache. For a true cold-cache benchmark,
restart the daemon before running. See benchmarks/CACHE.md.
"""
import json
import sys
import time
import urllib.request
import urllib.parse

ENDPOINT = "http://127.0.0.1:8765"
BENCHMARKS_DIR = "benchmarks"
RESULTS_DIR = f"{BENCHMARKS_DIR}/results"


def load_queries(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def search(query):
    url = f"{ENDPOINT}/search?q={urllib.parse.quote(query)}&limit=8"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return None


def run(queries_path):
    queries = load_queries(queries_path)

    top1 = 0
    top3 = 0
    top5 = 0
    total = len(queries)
    latencies = []
    results_log = []

    headers = {"Category": 12, "Query": 50, "Top-1": 8, "Top-3": 8, "Lat(ms)": 8}
    print(f"{'Category':<{headers['Category']}} {'Query':<{headers['Query']}} {'Top-1':<{headers['Top-1']}} {'Top-3':<{headers['Top-3']}} {'Lat(ms)':<{headers['Lat(ms)']}}")
    print("-" * 90)

    for q in queries:
        data = search(q["query"])
        lat = data["latency_ms"] if data else 0
        latencies.append(lat)

        if data is None:
            print(f"{q['category']:<{headers['Category']}} {q['query'][:48]:<{headers['Query']}} {'ERR':<{headers['Top-1']}} {'':<{headers['Top-3']}} {'':<{headers['Lat(ms)']}}")
            results_log.append({"query": q["query"], "category": q["category"], "error": True})
            continue

        filenames = [r["filename"] for r in data.get("results", [])]
        acceptable = q["acceptable"]

        t1 = any(f in acceptable for f in filenames[:1])
        t3 = any(f in acceptable for f in filenames[:3])
        t5 = any(f in acceptable for f in filenames[:5])

        if t1:
            top1 += 1
        if t3:
            top3 += 1
        if t5:
            top5 += 1

        ok1 = "+" if t1 else " "
        ok3 = "+" if t3 else " "
        print(f"{q['category']:<{headers['Category']}} {q['query'][:48]:<{headers['Query']}} {ok1:<{headers['Top-1']}} {ok3:<{headers['Top-3']}} {lat:<{headers['Lat(ms)']}.0f}")

        results_log.append({
            "query": q["query"],
            "category": q["category"],
            "acceptable": acceptable,
            "top_1": t1,
            "top_3": t3,
            "top_5": t5,
            "ranked_filenames": filenames,
            "latency_ms": lat,
        })

    print("-" * 90)
    avg_lat = sum(latencies) / max(len(latencies), 1)
    print(f"\nResults ({total} queries):")
    print(f"  Top-1 accuracy:  {top1}/{total} ({top1/total*100:.0f}%)")
    print(f"  Top-3 accuracy:  {top3}/{total} ({top3/total*100:.0f}%)")
    print(f"  Top-5 accuracy:  {top5}/{total} ({top5/total*100:.0f}%)")
    print(f"  Avg latency:     {avg_lat:.0f} ms")

    print(f"\nBy category:")
    by_cat = {}
    for cat in ["keyword", "conceptual", "vague", "ambiguous"]:
        cat_entries = [r for r in results_log if r["category"] == cat]
        cat_t1 = sum(1 for r in cat_entries if r["top_1"])
        cat_t3 = sum(1 for r in cat_entries if r["top_3"])
        print(f"  {cat:<12} top-1={cat_t1}/{len(cat_entries)}  top-3={cat_t3}/{len(cat_entries)}")
        by_cat[cat] = {"top_1": cat_t1, "total": len(cat_entries)}

    # Save results
    date_str = time.strftime("%Y-%m-%d")
    result_summary = {
        "date": date_str,
        "queries_file": queries_path,
        "total": total,
        "top_1": top1,
        "top_3": top3,
        "top_5": top5,
        "avg_latency_ms": round(avg_lat, 1),
        "by_category": by_cat,
        "results": results_log,
    }
    result_path = f"{RESULTS_DIR}/{date_str}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_summary, f, indent=2)
    print(f"\nSaved to {result_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    queries_file = args[0] if args else f"{BENCHMARKS_DIR}/queries_v2.json"
    run(queries_file)
