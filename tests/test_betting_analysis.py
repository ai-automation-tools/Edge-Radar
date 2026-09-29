"""Tests for `betting_analysis.py` render helpers.

Regression coverage for the longshot table crashing on settlement records
that are missing `edge_estimated` / `fair_value` (the trade ledger already
guards these; the longshot table did not — see 2026-07-14 repo review #3).
"""

from datetime import datetime, timezone

import betting_analysis


def _longshot_row(**overrides):
    row = {
        "_ts": datetime(2026, 7, 20, 19, 40, tzinfo=timezone.utc),
        "ticker": "KXMLBGAME-26JUL20SFKC-KC",
        "side": "yes",
        "market_price_at_entry": 0.10,  # < 0.15 → qualifies as a longshot
        "edge_estimated": 0.05,
        "fair_value": 0.15,
        "won": False,
        "net_pnl": -1.0,
    }
    row.update(overrides)
    return row


class TestRenderLongshotNoneGuard:
    def test_missing_edge_and_fair_value_does_not_crash(self):
        rows = [_longshot_row(edge_estimated=None, fair_value=None)]
        out = "\n".join(betting_analysis._render_longshot(rows))
        # renders the row with placeholders instead of raising TypeError
        assert "—" in out
        assert "10¢" in out  # price still renders (it's the filter key, never None)

    def test_present_values_still_render_numerically(self):
        rows = [_longshot_row()]
        out = "\n".join(betting_analysis._render_longshot(rows))
        assert "+5.0%" in out
        assert "15%" in out

    def test_one_bad_row_does_not_kill_the_others(self):
        rows = [
            _longshot_row(edge_estimated=None, fair_value=None),
            _longshot_row(),
        ]
        out = "\n".join(betting_analysis._render_longshot(rows))
        assert "+5.0%" in out  # the good row survived
        assert "—" in out  # the bad row rendered a placeholder


def _clv_row(clv, contracts=2, reason="t_minus_5", ticker="KXMLBTOTAL-26SEP111905NYMNYY-11"):
    return {
        "ticker": ticker,
        "side": "no",
        "market_price_at_entry": 0.70,
        "contracts": contracts,
        "clv": clv,
        "close_capture_reason": reason if clv is not None else None,
    }


_SIDE_ONLY = [("Side", lambda r: (r.get("side") or "?").upper(), None)]


class TestClvSection:
    """S9: mean CLV in points with a bootstrap CI, coverage beside every figure."""

    def test_coverage_counts_filled_rows_only(self):
        # A zero-fill resting order settles into the log but has no entry
        # price, so it must not count as a capture miss.
        rows = [_clv_row(0.02), _clv_row(None, reason=None), _clv_row(None, contracts=0)]
        out = "\n".join(betting_analysis._render_clv(rows, _SIDE_ONLY))
        assert "captured 1/2 (50%)" in out
        assert "+2.00 pts" in out

    def test_low_coverage_warns(self):
        rows = [_clv_row(0.01)] + [_clv_row(None, reason=None)] * 3
        out = "\n".join(betting_analysis._render_clv(rows, _SIDE_ONLY))
        assert "Coverage is below 60%" in out

    def test_no_clv_says_so_instead_of_printing_zero(self):
        out = "\n".join(betting_analysis._render_clv([_clv_row(None, reason=None)], _SIDE_ONLY))
        assert "No settled bet in this window carries a CLV" in out
        assert "pts" not in out

    def test_bootstrap_ci_brackets_the_mean_and_is_reproducible(self):
        vals = [-2.0, -1.0, 0.0, 1.0, 5.0]
        lo, hi = betting_analysis._bootstrap_ci(vals)
        assert lo < sum(vals) / len(vals) < hi
        assert betting_analysis._bootstrap_ci(vals) == (lo, hi)
        assert betting_analysis._bootstrap_ci([1.0]) is None
