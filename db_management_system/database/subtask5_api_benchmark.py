"""
SubTask 5 API Benchmark Runner
Measures endpoint response times before and after SQL indexing.

Usage examples:
  python database/subtask5_api_benchmark.py --phase before --base-url http://127.0.0.1:5000
  python database/subtask5_api_benchmark.py --phase after --base-url http://127.0.0.1:5000
"""

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import requests


def require_ok(response, context):
    if response.status_code >= 400:
        raise RuntimeError(f"{context} failed ({response.status_code}): {response.text}")


def timed_call(session, method, url, token=None, json_body=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    start = time.perf_counter()
    response = session.request(method, url, json=json_body, headers=headers, timeout=20)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return response, elapsed_ms


def benchmark_endpoint(session, base_url, token, workload, repeats):
    timings = []
    errors = 0

    for _ in range(repeats):
        response, elapsed_ms = timed_call(
            session=session,
            method=workload["method"],
            url=f"{base_url}{workload['path']}",
            token=token,
            json_body=workload.get("body"),
        )
        timings.append(elapsed_ms)
        if response.status_code >= 400:
            errors += 1

    return {
        "endpoint": f"{workload['method']} {workload['path']}",
        "repeats": repeats,
        "avg_ms": round(statistics.mean(timings), 3),
        "p95_ms": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 3),
        "min_ms": round(min(timings), 3),
        "max_ms": round(max(timings), 3),
        "errors": errors,
    }


def run_benchmark(base_url, phase, repeats, username, password, output_dir):
    session = requests.Session()

    login_resp = session.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=20,
    )
    require_ok(login_resp, "Login")
    token = login_resp.json().get("session_token")
    if not token:
        raise RuntimeError("Login succeeded but no session_token returned")

    reset_resp = session.post(
        f"{base_url}/api/admin/performance/reset-metrics",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    require_ok(reset_resp, "Reset performance metrics")

    workloads = [
        {"method": "GET", "path": "/api/project/products"},
        {"method": "GET", "path": "/api/project/products?category_id=1&sort=price_desc"},
        {"method": "GET", "path": "/api/project/products/1"},
        {"method": "GET", "path": "/api/project/customers"},
        {"method": "GET", "path": "/api/project/customers?email=rahul.verma@example.com"},
        {"method": "GET", "path": "/api/project/sales"},
        {"method": "GET", "path": "/api/project/sales?customer_id=1&sort=sale_date_desc"},
        {"method": "GET", "path": "/api/project/sale_items"},
        {"method": "GET", "path": "/api/project/sale_items?sale_id=10"},
        {"method": "GET", "path": "/api/member-portfolio"},
        {"method": "GET", "path": "/api/admin/groups"},
    ]

    results = []
    for workload in workloads:
        result = benchmark_endpoint(session, base_url, token, workload, repeats)
        results.append(result)

    stats_resp = session.get(
        f"{base_url}/api/admin/performance/endpoint-stats",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    require_ok(stats_resp, "Fetch endpoint stats")

    insights_resp = session.get(
        f"{base_url}/api/admin/performance/insights",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    require_ok(insights_resp, "Fetch endpoint insights")

    payload = {
        "phase": phase,
        "timestamp": datetime.utcnow().isoformat(),
        "base_url": base_url,
        "repeats": repeats,
        "api_results": results,
        "server_endpoint_stats": stats_resp.json(),
        "server_endpoint_insights": insights_resp.json(),
    }

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = output_path / f"subtask5_api_{phase}.json"
    report_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Saved benchmark report: {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SubTask 5 API benchmarks")
    parser.add_argument("--phase", required=True, choices=["before", "after"], help="Benchmark phase")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="API base URL")
    parser.add_argument("--repeats", type=int, default=30, help="Requests per endpoint")
    parser.add_argument("--username", default="aarav", help="Admin username")
    parser.add_argument("--password", default="Aarav@123", help="Admin password")
    parser.add_argument(
        "--output-dir",
        default="database/benchmark_results",
        help="Directory for benchmark result files",
    )
    args = parser.parse_args()

    run_benchmark(
        base_url=args.base_url,
        phase=args.phase,
        repeats=args.repeats,
        username=args.username,
        password=args.password,
        output_dir=args.output_dir,
    )
