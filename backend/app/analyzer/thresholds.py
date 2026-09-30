from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyzerThresholds:
    # Rule 1: large sequential scan
    seq_scan_min_rows: int = 5_000
    seq_scan_critical_rows: int = 100_000

    # Rule 2: sequential scan with a filter that discards most rows
    filter_min_rows_removed: int = 1_000
    filter_min_discard_ratio: float = 0.5

    # Rule 3: a single node dominating execution time
    high_time_min_ms: float = 10.0
    high_time_share: float = 0.5

    # Rule 4: estimated vs actual rows
    estimate_min_rows: int = 1_000
    estimate_ratio: float = 10.0

    # Rule 5: expensive sort
    sort_min_ms: float = 10.0

    # Rule 6: nested loop cost
    nested_loop_min_rows: int = 10_000
    nested_loop_min_ms: float = 10.0
