"""S22 / Gate 6b (2026-09-13): never hold both sides of one game.

Found in the settled book, not in review. One real pair, 466 rows:

    KXNFLGAME-26SEP10SFLAR-LAR    yes  3 @ 63c  ("Los Angeles R win?")
    KXNFLSPREAD-26SEP10SFLAR-SF8  yes  6 @ 11c  ("San Francisco wins by over 7.5?")

LAR to win *and* SF to win by 8+. At most one could ever pay, and both were
held into settlement. It cleared the whole chain:

  * Gate 5  -- different tickers.
  * Gate 6  -- `_event_key` keeps the series prefix, so `KXNFLGAME-...SFLAR`
               and `KXNFLSPREAD-...SFLAR` are *different events*. `MAX_PER_EVENT=2`
               is really "2 per series per game"; one real game has held **6**.
  * Gate 7  -- game-scoped and would have matched, but it is a 48h window over
               the trade log and the legs were **70 days** apart (06-01, 08-10).

So no gate compared DIRECTION. 6b does, and only that: it rejects bets that are
arithmetically unable to win together, never merely correlated ones.
"""

import pytest
from opportunity import Opportunity

import kalshi_executor as ke
from kalshi_executor import directional_claim, opposing_position, size_order

# The real pair, verbatim.
LAR_ML = "KXNFLGAME-26SEP10SFLAR-LAR"
SF_SPREAD = "KXNFLSPREAD-26SEP10SFLAR-SF8"


def _opp(ticker, side="yes", category="game", price=0.30):
    return Opportunity(
        ticker=ticker, title="", category=category, side=side,
        market_price=price, fair_value=price + 0.12, edge=0.12, edge_source="test",
        confidence="high", liquidity_score=9.0, composite_score=9.9,
        details={"bid_ask_spread": 0.01},
    )


class TestDirectionalClaim:
    """A moneyline is the margin-0 case of a spread; that is what lets one
    comparison cover the moneyline-vs-spread pair that actually occurred."""

    def test_moneyline_is_margin_zero(self):
        assert directional_claim(LAR_ML, "yes") == ("26SEP10SFLAR", "LAR", "yes", 0)

    def test_spread_splits_team_from_points(self):
        assert directional_claim(SF_SPREAD, "yes") == ("26SEP10SFLAR", "SF", "yes", 8)

    @pytest.mark.parametrize("strike,team,pts", [
        ("ATL11", "ATL", 11), ("NO5", "NO", 5), ("UCLA7", "UCLA", 7),
        ("TB11", "TB", 11), ("KC4", "KC", 4), ("LAC28", "LAC", 28),
    ])
    def test_real_strikes_from_the_book(self, strike, team, pts):
        got = directional_claim(f"KXNFLSPREAD-26SEP13XXYY-{strike}", "yes")
        assert got == ("26SEP13XXYY", team, "yes", pts)

    def test_totals_say_nothing_about_the_winner(self):
        assert directional_claim("KXNFLTOTAL-26SEP13ATLPIT-63", "no") is None

    @pytest.mark.parametrize("ticker", [
        "KXMLB-26-LAD",                      # futures: no game segment
        "KXBTCD-26SEP13-B120000",            # prediction market
        "MALFORMED",
        "KXNFLSPREAD-26SEP13XXYY-NODIGITS",  # strike carries no margin
    ])
    def test_unreadable_tickers_are_not_claims(self, ticker):
        assert directional_claim(ticker, "yes") is None

    def test_bad_side_is_not_a_claim(self):
        assert directional_claim(LAR_ML, "") is None
        assert directional_claim(LAR_ML, "maybe") is None

    def test_same_teams_different_day_are_different_games(self):
        a = directional_claim("KXNFLGAME-26SEP10SFLAR-LAR", "yes")
        b = directional_claim("KXNFLGAME-26DEC20SFLAR-LAR", "yes")
        assert a[0] != b[0], "game key must stay date-bearing, unlike matchup_key"

    def test_doubleheader_games_stay_distinct(self):
        a = directional_claim("KXMLBSPREAD-26SEP101610TEXSEA-TEX3", "yes")
        b = directional_claim("KXMLBSPREAD-26SEP101910TEXSEA-TEX3", "yes")
        assert a[0] != b[0], "the embedded start time must survive in the game key"


class TestTheRealPair:
    """The regression that motivated the gate."""

    def test_sf_spread_is_blocked_while_lar_moneyline_is_held(self):
        assert opposing_position(SF_SPREAD, "yes", {LAR_ML: "yes"}) == LAR_ML

    def test_it_is_symmetric(self):
        assert opposing_position(LAR_ML, "yes", {SF_SPREAD: "yes"}) == SF_SPREAD

    def test_gate_6b_rejects_it_end_to_end(self):
        sized = size_order(
            _opp(SF_SPREAD, category="spread", price=0.11),
            bankroll=100.0, open_positions=1, daily_pnl=0.0,
            open_sides={LAR_ML: "yes"},
        )
        assert sized.contracts == 0
        assert "opposing_side" in sized.risk_approval
        assert LAR_ML in sized.risk_approval

    def test_without_the_held_position_it_passes_6b(self):
        sized = size_order(
            _opp(SF_SPREAD, category="spread", price=0.11),
            bankroll=100.0, open_positions=1, daily_pnl=0.0, open_sides={},
        )
        assert "opposing_side" not in sized.risk_approval


class TestContradictionRules:
    def test_two_teams_both_to_win_outright(self):
        held = {"KXNFLGAME-26SEP13TBCIN-TB": "yes"}
        assert opposing_position("KXNFLGAME-26SEP13TBCIN-CIN", "yes", held)

    def test_two_teams_both_to_cover(self):
        held = {"KXNFLSPREAD-26SEP13TBCIN-TB11": "yes"}
        assert opposing_position("KXNFLSPREAD-26SEP13TBCIN-CIN3", "yes", held)

    def test_yes_at_a_wider_margin_than_a_held_no(self):
        """Winning by >10 implies winning by >4, so the NO leg is already lost."""
        held = {"KXNFLSPREAD-26SEP13ATLPIT-ATL4": "no"}
        assert opposing_position("KXNFLSPREAD-26SEP13ATLPIT-ATL11", "yes", held)

    def test_the_reverse_order_is_caught_too(self):
        held = {"KXNFLSPREAD-26SEP13ATLPIT-ATL11": "yes"}
        assert opposing_position("KXNFLSPREAD-26SEP13ATLPIT-ATL4", "no", held)

    def test_moneyline_yes_against_held_no_on_a_cover(self):
        """"ATL wins" (margin > 0) does NOT imply "ATL wins by > 4"."""
        held = {"KXNFLSPREAD-26SEP13ATLPIT-ATL4": "no"}
        assert opposing_position("KXNFLGAME-26SEP13ATLPIT-ATL", "yes", held) is None


class TestWhatMustStayAllowed:
    """6b rejects the impossible, not the merely correlated. Every pair here is
    jointly satisfiable and appears in the real book."""

    def test_the_band_trade(self):
        """YES by >4 with NO by >10 is "wins by 5-10" -- both legs can win."""
        held = {"KXNFLSPREAD-26SEP13ATLPIT-ATL11": "no"}
        assert opposing_position("KXNFLSPREAD-26SEP13ATLPIT-ATL4", "yes", held) is None

    def test_spread_plus_total_on_one_game(self):
        held = {"KXNFLTOTAL-26SEP13ATLPIT-63": "no"}
        assert opposing_position("KXNFLSPREAD-26SEP13ATLPIT-ATL11", "yes", held) is None

    def test_moneyline_plus_spread_on_the_same_team(self):
        held = {"KXNFLGAME-26SEP09NESEA-NE": "yes"}
        assert opposing_position("KXNFLSPREAD-26SEP09NESEA-NE5", "yes", held) is None

    def test_win_narrowly(self):
        """Real NHL row: CAR to win, NO on CAR by >2.5. Coherent."""
        held = {"KXNHLGAME-26JUN09CARVGK-CAR": "yes"}
        assert opposing_position("KXNHLSPREAD-26JUN09CARVGK-CAR2", "no", held) is None

    def test_two_no_legs_on_different_teams(self):
        """Neither side covering big is perfectly possible -- a close game."""
        held = {"KXNFLSPREAD-26SEP13ARILAC-LAC28": "no"}
        assert opposing_position("KXNFLSPREAD-26SEP13ARILAC-ARI28", "no", held) is None

    def test_different_games_never_interact(self):
        held = {"KXNFLGAME-26SEP13TBCIN-TB": "yes"}
        assert opposing_position("KXNFLGAME-26SEP13ATLPIT-PIT", "yes", held) is None

    def test_same_ticker_is_gate_5s_job(self):
        assert opposing_position(LAR_ML, "yes", {LAR_ML: "yes"}) is None

    def test_futures_are_exempt_at_the_gate(self):
        """Futures outcomes partition an event by design -- Gate 6's own rule."""
        held = {"KXNFLGAME-26SEP10SFLAR-LAR": "yes"}
        sized = size_order(
            _opp(SF_SPREAD, category="futures", price=0.11),
            bankroll=100.0, open_positions=1, daily_pnl=0.0, open_sides=held,
        )
        assert "opposing_side" not in sized.risk_approval


class TestFailureModes:
    def test_no_held_positions_is_a_no_op(self):
        assert opposing_position(SF_SPREAD, "yes", None) is None
        assert opposing_position(SF_SPREAD, "yes", {}) is None

    def test_unreadable_held_rows_are_skipped_not_fatal(self):
        held = {"GARBAGE": "yes", "": "no", LAR_ML: "yes"}
        assert opposing_position(SF_SPREAD, "yes", held) == LAR_ML

    def test_gate_is_inert_when_sides_are_unavailable(self):
        """Callers that never pass `open_sides` behave exactly as before."""
        sized = size_order(
            _opp(SF_SPREAD, category="spread", price=0.11),
            bankroll=100.0, open_positions=1, daily_pnl=0.0,
        )
        assert "opposing_side" not in sized.risk_approval


class TestPositionSideDecoding:
    """Kalshi signs `position_fp` and ships it as a string: + is long YES."""

    @pytest.mark.parametrize("fp,expected", [
        ("2.00", "yes"), ("-1.00", "no"), ("0.01", "yes"), ("-0.01", "no"),
    ])
    def test_sign_maps_to_side(self, fp, expected):
        qty = float(fp)
        assert ("yes" if qty > 0 else "no") == expected

    def test_real_rows_decode_to_their_logged_sides(self):
        """Straight from the live book on 2026-09-13."""
        live = [
            ("KXNFLSPREAD-26SEP14DENKC-KC4", "2.00", "yes"),
            ("KXNFLTOTAL-26SEP13DALNYG-70", "-1.00", "no"),
            ("KXNFLTOTAL-26SEP14DENKC-22", "1.00", "yes"),
            ("KXNCAAFSPREAD-26SEP19TEMTOL-TEM3", "-0.01", "no"),
        ]
        for ticker, fp, logged_side in live:
            assert ("yes" if float(fp) > 0 else "no") == logged_side, ticker


class TestRestingOrdersAreVisible:
    """Half the real contradictions involved a leg that never filled.

    `KXWCSPREAD-26JUN26EGYIRI-EGY2` was ordered 2026-06-20 and never filled;
    on 06-22 the pipeline bought `IRI2` -- Egypt by 2+ *and* Iran by 2+. A
    zero-fill order has `position_fp == 0`, so the positions feed shows nothing.
    """

    class _Client:
        def __init__(self, orders):
            self._orders = orders

        def get_orders(self, status=None, limit=None):
            return {"orders": self._orders}

    def test_side_is_read_from_the_log_not_the_venue(self):
        """v2 reports a NO buy as an `ask`; trusting that inverts the side."""
        client = self._Client([
            {"ticker": "KXNFLSPREAD-26SEP13ATLPIT-ATL4",
             "order_id": "abc", "remaining_count_fp": "3", "side": "ask"},
        ])
        log_rows = [{"order_id": "abc", "side": "no"}]
        assert ke.resting_sides(client, log_rows) == {
            "KXNFLSPREAD-26SEP13ATLPIT-ATL4": "no"
        }

    def test_filled_orders_are_not_resting(self):
        client = self._Client([
            {"ticker": "KXNFLGAME-26SEP13TBCIN-TB",
             "order_id": "abc", "remaining_count_fp": "0", "side": "bid"},
        ])
        assert ke.resting_sides(client, [{"order_id": "abc", "side": "yes"}]) == {}

    def test_unidentifiable_order_fails_open(self):
        """No log row -> omitted, not guessed. Over-blocking on a guessed side
        would reject coherent bets."""
        client = self._Client([
            {"ticker": "KXNFLGAME-26SEP13TBCIN-TB",
             "order_id": "nosuch", "remaining_count_fp": "2", "side": "bid"},
        ])
        assert ke.resting_sides(client, []) == {}

    def test_api_failure_never_blocks_a_batch(self):
        class Boom:
            def get_orders(self, **kw):
                raise RuntimeError("503")
        assert ke.resting_sides(Boom(), []) == {}

    def test_the_world_cup_pair_is_caught(self):
        client = self._Client([
            {"ticker": "KXWCSPREAD-26JUN26EGYIRI-EGY2",
             "order_id": "egy", "remaining_count_fp": "5", "side": "bid"},
        ])
        held = ke.resting_sides(client, [{"order_id": "egy", "side": "yes"}])
        assert opposing_position(
            "KXWCSPREAD-26JUN26EGYIRI-IRI2", "yes", held
        ) == "KXWCSPREAD-26JUN26EGYIRI-EGY2"
