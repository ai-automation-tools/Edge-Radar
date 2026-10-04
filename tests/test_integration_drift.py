"""integration_drift.probe_series: flags the M1 failure class, passes clean data."""

from integration_drift import FAIL, OK, WARN, probe_series, rules_template


def _event(away, home, commence="2026-10-04T17:00:00Z"):
    return {"away_team": away, "home_team": home, "commence_time": commence, "bookmakers": []}


def _game(ticker, team, rules):
    return {
        "ticker": ticker,
        "yes_sub_title": team,
        "rules_primary": rules,
        "yes_ask_dollars": "0.50",
        "no_ask_dollars": "0.51",
        "yes_bid_dollars": "0.49",
    }


EVENTS = [
    _event("Denver Broncos", "San Francisco 49ers"),
    _event("Detroit Lions", "Carolina Panthers"),
]


def _slate(rules_fmt):
    out = []
    for i in range(3):
        out.append(
            _game(
                f"KXNFLGAME-26OCT04DENSF-SF{i}",
                "San Francisco",
                rules_fmt.format(a="Denver", b="San Francisco"),
            )
        )
        out.append(
            _game(
                f"KXNFLGAME-26OCT04DETCAR-DET{i}",
                "Detroit",
                rules_fmt.format(a="Detroit", b="Carolina"),
            )
        )
    return out


def test_clean_slate_is_ok():
    r = probe_series(
        "KXNFLGAME", _slate("If X wins the {a} vs {b} professional football game"), EVENTS
    )
    assert r["level"] == OK
    assert r["parse_rate"] == 1.0 and r["match_rate"] == 1.0


def test_unknown_wording_fails_parse():
    # The M1 shape: a league word the extractor does not know -> no teams at all.
    r = probe_series(
        "KXNFLGAME", _slate("If X wins the {a} vs {b} Gridiron Football contest"), EVENTS
    )
    assert r["level"] == FAIL
    assert r["parse_rate"] == 0.0
    assert r["examples"]["unparsed"]


def test_missing_field_fails():
    slate = _slate("If X wins the {a} vs {b} professional football game")
    del slate[0]["yes_ask_dollars"]
    assert probe_series("KXNFLGAME", slate, EVENTS)["level"] == FAIL


def test_unposted_games_are_not_misses():
    r = probe_series("KXNFLGAME", _slate("If X wins the {a} vs {b} professional football game"), [])
    assert r["measurable"] == 0 and r["match_rate"] is None and r["level"] == OK


def test_unmatched_team_warns_or_fails():
    # Event pairs, but the YES team resolves to neither side (the spread-suffix shape).
    slate = [
        _game(
            f"KXNFLGAME-26OCT04DENSF-X{i}",
            "DEN wins by",
            "If X wins the Denver vs San Francisco professional game",
        )
        for i in range(6)
    ]
    assert probe_series("KXNFLGAME", slate, EVENTS)["level"] in (WARN, FAIL)


def test_rules_template_abstracts_names_and_numbers():
    m = {
        "rules_primary": "If DET Lions wins by more than 7.5 points in the DET Lions vs "
        "CAR Panthers Pro Football game originally scheduled for Oct 4, 2026, "
        "then the market resolves to Yes."
    }
    t = rules_template(m, ("DET Lions", "CAR Panthers"), "DET Lions")
    assert "DET" not in t and "7.5" not in t and "<DATE>" in t
    assert t.endswith("originally scheduled for <DATE>")


def test_autofix_changed_keeps_first_path_intact(monkeypatch):
    import drift_autofix as da

    # Porcelain lines start with a space; a strip() once ate "s" of "scripts".
    monkeypatch.setattr(
        da, "_git", lambda *a, **k: " M scripts/kalshi/edge_detector.py\n?? tests/test_new.py"
    )
    assert da._changed(None) == [
        ("M", "scripts/kalshi/edge_detector.py"),
        ("??", "tests/test_new.py"),
    ]


def test_autofix_allowlist():
    from drift_autofix import ALLOWED

    for ok in ("scripts/kalshi/edge_detector.py", "tests/test_edge_detection.py"):
        assert ALLOWED.match(ok)
    for bad in (
        "scripts/kalshi/kalshi_executor.py",
        "scripts/kalshi/integration_drift.py",
        "app/config.py",
        ".env",
        "scripts/schedulers/maintenance/drift_check.bat",
    ):
        assert not ALLOWED.match(bad)
