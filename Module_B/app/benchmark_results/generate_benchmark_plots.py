import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def shorten_endpoint(endpoint: str) -> str:
    endpoint = endpoint.replace("GET /api/", "")
    endpoint = endpoint.replace("/project/", "proj/")
    if len(endpoint) <= 38:
        return endpoint
    return endpoint[:35] + "..."


def main():
    base_dir = Path(__file__).resolve().parent
    before_path = base_dir / "api_benchmark_before.json"
    after_path = base_dir / "api_benchmark_after.json"

    before_data = load_json(before_path)
    after_data = load_json(after_path)

    before_map = {item["endpoint"]: item for item in before_data["api_results"]}
    after_map = {item["endpoint"]: item for item in after_data["api_results"]}

    endpoints = [ep for ep in before_map.keys() if ep in after_map]
    labels = [shorten_endpoint(ep) for ep in endpoints]

    before_avg = [before_map[ep]["avg_ms"] for ep in endpoints]
    after_avg = [after_map[ep]["avg_ms"] for ep in endpoints]

    pct_change = []
    for ep in endpoints:
        b = before_map[ep]["avg_ms"]
        a = after_map[ep]["avg_ms"]
        pct_change.append(((a - b) / b) * 100.0)

    before_p95 = [before_map[ep]["p95_ms"] for ep in endpoints]
    after_p95 = [after_map[ep]["p95_ms"] for ep in endpoints]

    x = list(range(len(endpoints)))
    width = 0.38

    # 1) Average response time comparison
    plt.figure(figsize=(14, 7))
    plt.bar([i - width / 2 for i in x], before_avg, width=width, label="Before", color="#cc6f3d")
    plt.bar([i + width / 2 for i in x], after_avg, width=width, label="After", color="#2f7f65")
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Average Response Time (ms)")
    plt.title("API Benchmark: Before vs After (Average)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(base_dir / "plot_avg_before_after.png", dpi=180)
    plt.close()

    # 2) Percent change chart
    colors = ["#2f7f65" if value < 0 else "#c23a22" for value in pct_change]
    plt.figure(figsize=(14, 7))
    bars = plt.bar(x, pct_change, color=colors)
    plt.axhline(0, color="black", linewidth=1)
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Change in Avg Response Time (%)")
    plt.title("API Benchmark: Percentage Change (After vs Before)")
    for bar, value in zip(bars, pct_change):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + (0.8 if value >= 0 else -0.8),
            f"{value:.1f}%",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
        )
    plt.tight_layout()
    plt.savefig(base_dir / "plot_avg_percent_change.png", dpi=180)
    plt.close()

    # 3) p95 response time comparison
    plt.figure(figsize=(14, 7))
    plt.bar([i - width / 2 for i in x], before_p95, width=width, label="Before p95", color="#9e8f3d")
    plt.bar([i + width / 2 for i in x], after_p95, width=width, label="After p95", color="#3d5a9e")
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("p95 Response Time (ms)")
    plt.title("API Benchmark: Before vs After (p95)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(base_dir / "plot_p95_before_after.png", dpi=180)
    plt.close()

    print("Created plots:")
    print("- plot_avg_before_after.png")
    print("- plot_avg_percent_change.png")
    print("- plot_p95_before_after.png")


if __name__ == "__main__":
    main()
