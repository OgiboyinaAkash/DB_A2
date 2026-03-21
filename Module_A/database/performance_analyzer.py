import random
import time
import tracemalloc
from statistics import median

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from .bplustree import BPlusTree
    from .bruteforce import BruteForceDB
except ImportError:
    from bplustree import BPlusTree
    from bruteforce import BruteForceDB


class PerformanceAnalyzer:
    """Utility class to benchmark B+ Tree against brute-force operations."""

    def __init__(self, order=8, seed=42):
        self.order = order
        self._random = random.Random(seed)

    def _make_bplustree(self):
        return BPlusTree(order=self.order)

    def _make_bruteforce(self):
        return BruteForceDB()

    def _measure_time(self, fn, repeat=5):
        durations = []
        for _ in range(repeat):
            start = time.perf_counter()
            fn()
            durations.append(time.perf_counter() - start)
        return median(durations)

    def _measure_peak_memory(self, fn):
        tracemalloc.start()
        try:
            fn()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return peak

    def generate_dataset(self, size, key_range=None):
        """
        Generate unique integer keys and record payloads.

        Returns:
            keys: list[int]
            records: list[tuple[int, dict]]
        """
        if size < 1:
            return [], []

        if key_range is None:
            key_range = size * 10
        if key_range < size:
            raise ValueError("key_range must be >= size for unique keys")

        keys = self._random.sample(range(key_range), size)
        records = [(k, {"id": k, "value": f"record_{k}"}) for k in keys]
        return keys, records

    def _build_bplustree(self, records):
        tree = self._make_bplustree()
        for key, value in records:
            tree.insert(key, value)
        return tree

    def _build_bruteforce(self, records):
        db = self._make_bruteforce()
        for key, value in records:
            db.insert(key, value)
        return db

    def generate_search_keys(self, existing_keys, query_count=None):
        """
        Generate a randomized search workload independent from insertion order.

        The workload contains a mix of present and absent keys.
        """
        if not existing_keys:
            return []

        if query_count is None:
            query_count = max(100, len(existing_keys))

        existing_keys = list(existing_keys)
        existing_set = set(existing_keys)

        hit_count = min(len(existing_keys), query_count // 2)
        miss_count = max(0, query_count - hit_count)

        hits = self._random.sample(existing_keys, hit_count) if hit_count else []

        upper_bound = max(existing_keys) + len(existing_keys) * 10 + 1
        misses = []
        while len(misses) < miss_count:
            candidate = self._random.randrange(upper_bound)
            if candidate not in existing_set:
                misses.append(candidate)

        queries = hits + misses
        self._random.shuffle(queries)
        return queries

    def generate_range_queries(self, existing_keys, query_count=100):
        """Generate randomized [left, right] range query bounds."""
        if not existing_keys:
            return []

        sorted_keys = sorted(existing_keys)
        if len(sorted_keys) == 1:
            key = sorted_keys[0]
            return [(key, key)] * query_count

        queries = []
        for _ in range(query_count):
            left, right = self._random.sample(sorted_keys, 2)
            if left > right:
                left, right = right, left
            queries.append((left, right))
        return queries

    def measure_time_complexity(self, sizes, repeat=5):
        """
        Measure median runtime (seconds) for insert/search/range/delete.

        Returns a dictionary keyed by size with timings for each backend.
        """
        results = {}

        for size in sizes:
            keys, records = self.generate_dataset(size)
            search_keys = self.generate_search_keys(keys)
            range_queries = self.generate_range_queries(keys)
            delete_keys = self._random.sample(keys, len(keys)) if keys else []

            insert_records = records

            bpt_insert = self._measure_time(
                lambda: self._build_bplustree(insert_records),
                repeat=repeat,
            )
            brute_insert = self._measure_time(
                lambda: self._build_bruteforce(insert_records),
                repeat=repeat,
            )

            bpt_for_search = self._build_bplustree(records)
            brute_for_search = self._build_bruteforce(records)

            bpt_search = self._measure_time(
                lambda: self._time_searches(bpt_for_search, search_keys),
                repeat=repeat,
            )
            brute_search = self._measure_time(
                lambda: self._time_searches(brute_for_search, search_keys),
                repeat=repeat,
            )

            bpt_for_range = self._build_bplustree(records)
            brute_for_range = self._build_bruteforce(records)

            bpt_range = self._measure_time(
                lambda: self._time_range_queries(bpt_for_range, range_queries),
                repeat=repeat,
            )
            brute_range = self._measure_time(
                lambda: self._time_range_queries(brute_for_range, range_queries),
                repeat=repeat,
            )

            bpt_delete = self._measure_time(
                lambda: self._time_delete(self._build_bplustree(records), delete_keys),
                repeat=repeat,
            )
            brute_delete = self._measure_time(
                lambda: self._time_delete(self._build_bruteforce(records), delete_keys),
                repeat=repeat,
            )

            results[size] = {
                "bplustree": {
                    "insert": bpt_insert,
                    "search": bpt_search,
                    "range_query": bpt_range,
                    "delete": bpt_delete,
                },
                "bruteforce": {
                    "insert": brute_insert,
                    "search": brute_search,
                    "range_query": brute_range,
                    "delete": brute_delete,
                },
            }

        return results

    def measure_memory_usage(self, size):
        """
        Measure peak allocated memory (bytes) while building each backend.
        """
        _, records = self.generate_dataset(size)

        bpt_peak = self._measure_peak_memory(lambda: self._build_bplustree(records))
        brute_peak = self._measure_peak_memory(lambda: self._build_bruteforce(records))

        return {
            "size": size,
            "bplustree_peak_bytes": bpt_peak,
            "bruteforce_peak_bytes": brute_peak,
        }

    def compare_with_bruteforce(self, sizes, repeat=5):
        """
        Compare B+ Tree against brute-force across time and memory metrics.

        Returns:
            {
                "time": { ... per-size timings ... },
                "memory": [ ... per-size memory snapshots ... ],
                "summary": { ... speedup factors ... }
            }
        """
        time_results = self.measure_time_complexity(sizes=sizes, repeat=repeat)
        memory_results = [self.measure_memory_usage(size) for size in sizes]

        summary = {}
        for size, metrics in time_results.items():
            summary[size] = {}
            for op in ("insert", "search", "range_query", "delete"):
                bpt_value = metrics["bplustree"][op]
                brute_value = metrics["bruteforce"][op]
                if bpt_value == 0:
                    speedup = float("inf")
                else:
                    speedup = brute_value / bpt_value
                summary[size][op] = {
                    "bplustree_seconds": bpt_value,
                    "bruteforce_seconds": brute_value,
                    "speedup_vs_bruteforce": speedup,
                }

        return {
            "time": time_results,
            "memory": memory_results,
            "summary": summary,
        }

    def _time_delete(self, structure, keys):
        for key in keys:
            structure.delete(key)

    def _time_searches(self, structure, keys):
        for key in keys:
            structure.search(key)

    def _time_range_queries(self, structure, bounds):
        for left, right in bounds:
            structure.range_query(left, right)

    def conduct_performance_testing(self, sizes=None, repeat=5):
        """
        Run randomized performance tests for insert/search/range/delete and memory.

        Args:
            sizes: Iterable of dataset sizes. Defaults to range(100, 100000, 1000).
            repeat: Number of repetitions for median timing.

        Returns:
            dict: Combined timing, memory and summary metrics.
        """
        if sizes is None:
            sizes = list(range(100, 100000, 1000))
        else:
            sizes = list(sizes)

        if not sizes:
            raise ValueError("sizes must not be empty")

        return self.compare_with_bruteforce(sizes=sizes, repeat=repeat)

    def plot_results(self, results, show=True, save_dir=None, prefix="performance"):
        """
        Visualize time, speedup, and memory metrics using Matplotlib.

        Args:
            results: Output dictionary from conduct_performance_testing().
            show: Whether to show plots interactively.
            save_dir: Optional folder path to save generated figures.
            prefix: Filename prefix when save_dir is provided.

        Returns:
            dict: Mapping of plot names to matplotlib Figure objects.
        """
        if plt is None:
            raise ImportError(
                "matplotlib is required for plotting. Install it with: pip install matplotlib"
            )

        sizes = sorted(results["time"].keys())
        operations = ("insert", "search", "range_query", "delete")
        figures = {}

        fig_time, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
        axes = axes.flatten()

        for idx, op in enumerate(operations):
            bpt_times = [results["time"][size]["bplustree"][op] for size in sizes]
            brute_times = [results["time"][size]["bruteforce"][op] for size in sizes]

            axes[idx].plot(sizes, bpt_times, marker="o", label="B+ Tree")
            axes[idx].plot(sizes, brute_times, marker="s", label="Brute Force")
            axes[idx].set_title(f"{op.replace('_', ' ').title()} Time")
            axes[idx].set_xlabel("Dataset Size")
            axes[idx].set_ylabel("Seconds")
            axes[idx].grid(True, alpha=0.3)
            axes[idx].legend()

        fig_time.suptitle("B+ Tree vs Brute Force: Time Comparison", fontsize=14)
        fig_time.tight_layout()
        figures["time"] = fig_time

        fig_speedup, axes_speedup = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
        axes_speedup = axes_speedup.flatten()

        for idx, op in enumerate(operations):
            speedups = [results["summary"][size][op]["speedup_vs_bruteforce"] for size in sizes]
            axes_speedup[idx].plot(sizes, speedups, marker="^", color="green")
            axes_speedup[idx].axhline(1.0, color="red", linestyle="--", linewidth=1)
            axes_speedup[idx].set_title(f"{op.replace('_', ' ').title()} Speedup")
            axes_speedup[idx].set_xlabel("Dataset Size")
            axes_speedup[idx].set_ylabel("Speedup (x)")
            axes_speedup[idx].grid(True, alpha=0.3)

        fig_speedup.suptitle("B+ Tree Speedup over Brute Force", fontsize=14)
        fig_speedup.tight_layout()
        figures["speedup"] = fig_speedup

        memory_by_size = {item["size"]: item for item in results["memory"]}
        memory_sizes = sorted(memory_by_size.keys())
        bpt_memory = [memory_by_size[size]["bplustree_peak_bytes"] for size in memory_sizes]
        brute_memory = [memory_by_size[size]["bruteforce_peak_bytes"] for size in memory_sizes]

        fig_memory, ax_memory = plt.subplots(figsize=(12, 6))
        ax_memory.plot(memory_sizes, bpt_memory, marker="o", label="B+ Tree")
        ax_memory.plot(memory_sizes, brute_memory, marker="s", label="Brute Force")
        ax_memory.set_title("Peak Memory Usage")
        ax_memory.set_xlabel("Dataset Size")
        ax_memory.set_ylabel("Peak Bytes")
        ax_memory.grid(True, alpha=0.3)
        ax_memory.legend()
        fig_memory.tight_layout()
        figures["memory"] = fig_memory

        if save_dir:
            import os

            os.makedirs(save_dir, exist_ok=True)
            fig_time.savefig(os.path.join(save_dir, f"{prefix}_time.png"), dpi=150)
            fig_speedup.savefig(os.path.join(save_dir, f"{prefix}_speedup.png"), dpi=150)
            fig_memory.savefig(os.path.join(save_dir, f"{prefix}_memory.png"), dpi=150)

        if show:
            plt.show()

        return figures


def run_and_plot_performance(order=8, sizes=None, repeat=5, show=True, save_dir=None):
    """
    Convenience function to execute SubTask 4 end-to-end.
    """
    analyzer = PerformanceAnalyzer(order=order)
    results = analyzer.conduct_performance_testing(sizes=sizes, repeat=repeat)
    analyzer.plot_results(results, show=show, save_dir=save_dir)
    return results


if __name__ == "__main__":
    analyzer = PerformanceAnalyzer(order=8)
    # Smaller default set for command-line runs; pass a larger range if needed.
    demo_sizes = list(range(100, 5100, 500))
    benchmark_results = analyzer.conduct_performance_testing(sizes=demo_sizes, repeat=5)
    analyzer.plot_results(benchmark_results, show=True, save_dir=None)
