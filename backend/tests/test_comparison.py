import pytest

from app.services.comparison_service import compare_analyses
from tests.factories import make_analysis, make_issue


def by_key(result):
    return {metric.key: metric for metric in result.metrics}


def test_clear_improvement_is_reported_with_measured_numbers():
    result = compare_analyses(make_analysis(84), make_analysis(31))

    assert result.verdict == "improved"
    assert result.summary == "Execution time improved by 63% (from 84.0 ms to 31.0 ms)."
    execution = by_key(result)["execution_time"]
    assert execution.change_pct == pytest.approx(-63.1, abs=0.1)
    assert execution.better is True


def test_tiny_difference_is_not_called_an_improvement():
    result = compare_analyses(make_analysis(84), make_analysis(82))

    assert result.verdict == "no_significant_change"
    assert "No significant difference" in result.summary
    assert by_key(result)["execution_time"].better is None


def test_clear_slowdown_is_a_regression():
    result = compare_analyses(make_analysis(10), make_analysis(30))

    assert result.verdict == "regressed"
    assert result.summary == "Execution time got worse by 200% (from 10.0 ms to 30.0 ms)."
    assert by_key(result)["execution_time"].better is False


def test_sub_millisecond_changes_are_treated_as_noise_even_if_the_percentage_is_large():
    result = compare_analyses(make_analysis(0.3), make_analysis(0.1))
    assert result.verdict == "no_significant_change"


def test_an_eleven_percent_change_is_significant():
    assert compare_analyses(make_analysis(100), make_analysis(89)).verdict == "improved"


def test_zero_times_do_not_crash():
    result = compare_analyses(make_analysis(0), make_analysis(0))
    assert result.verdict == "no_significant_change"


def test_percentage_is_none_when_the_before_value_is_zero():
    result = compare_analyses(make_analysis(10, rows=0), make_analysis(10, rows=5))
    assert by_key(result)["rows_returned"].change_pct is None


def test_different_row_counts_produce_a_warning():
    result = compare_analyses(make_analysis(84, rows=1000), make_analysis(31, rows=500))
    assert any("different numbers of rows" in note for note in result.notes)


def test_matching_row_counts_produce_no_such_warning():
    result = compare_analyses(make_analysis(84), make_analysis(31))
    assert not any("different numbers of rows" in note for note in result.notes)


def test_a_changed_plan_is_pointed_out():
    result = compare_analyses(make_analysis(84), make_analysis(3, node_type="Index Scan"))

    note = next(n for n in result.notes if "execution plan changed" in n)
    assert "Seq Scan(users)" in note
    assert "Index Scan(users)" in note


def test_an_unchanged_plan_is_not_mentioned():
    result = compare_analyses(make_analysis(84), make_analysis(31))
    assert not any("execution plan changed" in n for n in result.notes)


def test_multiple_runs_are_mentioned():
    result = compare_analyses(make_analysis(84), make_analysis(31), runs=3)
    assert result.runs == 3
    assert any("3 times" in n for n in result.notes)


def test_resolved_and_new_issues_are_listed():
    with_issue = make_analysis(84, issues=[make_issue()])
    without_issue = make_analysis(31)

    fixed = compare_analyses(with_issue, without_issue)
    assert fixed.resolved_issues == ["Large Sequential Scan on users"]
    assert fixed.new_issues == []

    worse = compare_analyses(without_issue, with_issue)
    assert worse.new_issues == ["Large Sequential Scan on users"]
    assert worse.resolved_issues == []


def test_fewer_issues_and_fewer_buffers_count_as_better():
    before = make_analysis(84, issues=[make_issue(), make_issue("SEQ_SCAN_WITH_FILTER")],
                           hits=100, reads=20)
    after = make_analysis(31, hits=10, reads=0)

    metrics = by_key(compare_analyses(before, after))

    assert metrics["issues_count"].before == 2 and metrics["issues_count"].after == 0
    assert metrics["issues_count"].better is True
    assert metrics["buffers"].before == 120 and metrics["buffers"].after == 10
    assert metrics["buffers"].better is True
