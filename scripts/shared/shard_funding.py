"""Just-in-time cash movement between Kalshi exchange shards.

Kalshi sharded the exchange on **2026-08-24**: Crypto moved to shard 2, Tennis &
Baseball to shard 3, everything else stayed on shard 0; on **2026-09-10** Basketball
joined shard 3 and Commodities shard 2. **Cash does not follow the markets.** An order
against a market on a shard where the account holds no funds fails `404 user_not_found`
-- the market resolves, then the per-shard user lookup does not (see CHANGELOG
2026-08-27).

**Which shard a market is on is never inferred from its sport.** The executor reads
`exchange_index` off the market payload per ticker (`_shard_for` in
`kalshi_executor.py`), so a category moving shards -- as Basketball did -- needs no
code change. The sport-to-shard mapping exists in code only as `shard_names()`'s
display fallback, and that reads the venue first (verified 2026-10-05: NBA on 3).

Sizing is deliberately whole-account: `bankroll` is `get_balance()["balance"]`, the
sum across every shard (operator's call, 2026-08-27). So an order can be correctly
sized against the full balance and still be unspendable where it lands. This module
closes that gap by moving exactly the shortfall from the funding shard immediately
before the order is placed.

**Design constraints, all learned the hard way:**

* **Exactly the shortfall, never a round-up.** Cash parked on a sports shard cannot
  back an NFL order. Over-moving quietly reallocates the bankroll.
* **Capped.** `MAX_AUTO_SHARD_TRANSFER` bounds a single move. A shortfall computed
  wrongly should bounce off the cap, not drain shard 0.
* **Verified, not assumed.** Kalshi: "Cross-exchange-index subaccount transfers run
  in up to three non-atomic steps. If a later step fails, completed steps are not
  undone." So the destination balance is re-read afterwards, and the order is
  skipped if the money did not arrive.
* **Never in DRY_RUN.** `intra_exchange_transfer()` blocks it too; this is the
  belt to that suspenders, because the whole point is unattended operation.
* **One attempt per order.** No retry loop around a money movement.
"""

from __future__ import annotations

import logging

log = logging.getLogger("shard_funding")

__all__ = ["shard_balances", "shard_names", "ensure_shard_funded"]

# Display names only. Last seen at ``GET /exchange/status`` on 2026-10-05; the
# venue's list wins whenever it answers, this is for an offline or stubbed client.
FALLBACK_SHARD_NAMES: dict[int, str] = {
    0: "Default",
    1: "Combos",
    2: "Crypto & Commodities",
    3: "Tennis, Baseball, Basketball",
}


def shard_names(client) -> dict[int, str]:
    """Map shard index -> the venue's description, for display.

    Reads ``exchange_index_statuses`` from ``GET /exchange/status``, which is
    the only place Kalshi publishes which categories trade on which shard. The
    list moved (Basketball to 3 and Commodities to 2 on 2026-09-10) while a
    hardcoded copy in ``doctor.py`` kept printing the 08-24 names, so the
    venue is authoritative and ``FALLBACK_SHARD_NAMES`` is only for a client
    that cannot answer. Never a money decision: the executor reads a market's
    own ``exchange_index`` before placing, whatever this says.
    """
    read = getattr(client, "get_exchange_status", None)
    if read is None:
        return dict(FALLBACK_SHARD_NAMES)
    try:
        statuses = (read() or {}).get("exchange_index_statuses") or []
        names = {
            int(s["exchange_index"]): str(s.get("description") or "?")
            for s in statuses
            if "exchange_index" in s
        }
    except Exception as e:  # noqa: BLE001
        log.warning("Exchange status read failed; using fallback shard names: %s", e)
        return dict(FALLBACK_SHARD_NAMES)
    return names or dict(FALLBACK_SHARD_NAMES)


def shard_balances(client, shards) -> dict[int, float]:
    """Map shard index -> available dollars for THIS subaccount, for `shards`.

    The top-level `balance` is the SUM across shards and is what sizing uses;
    this is the per-shard view that determines what an order can actually spend.

    **Not `balance_breakdown`.** That field is account-wide and ignores the
    `subaccount` param (verified 2026-09-08: as subaccount 1, holding $40 all on
    shard 0, it reported `{0: 109.79, 3: 13.76}` — the primary's cash folded in).
    Reading it here made the guard fail OPEN in exactly the case it exists for:
    a fork wallet with $0 on shard 3 saw the primary's $13.76, found no
    shortfall, and let the order through to a `404 user_not_found`. One scoped
    `get_shard_balance()` call per shard is the only correct read, so ask for
    just the shards the decision needs rather than all four.

    Returns {} if the client cannot answer -- callers fail open on that, which is
    pre-sharding behaviour. Returning nothing is safe; returning another wallet's
    balance is not.
    """
    read = getattr(client, "get_shard_balance", None)
    if read is None:
        return {}
    out: dict[int, float] = {}
    for shard in shards:
        try:
            out[int(shard)] = float(read(shard))
        except Exception as e:  # noqa: BLE001
            log.warning("Per-shard balance read failed for shard %s: %s", shard, e)
            return {}
    return out


def ensure_shard_funded(
    client,
    shard: int | None,
    cost: float,
    *,
    enabled: bool,
    source_shard: int,
    max_transfer: float,
    dry_run: bool,
) -> tuple[bool, str | None]:
    """Make `cost` spendable on `shard`, moving cash from `source_shard` if needed.

    Returns ``(ok, note)``. ``ok`` False means do not place this order. ``note`` is
    a human line for the console/log when something happened worth saying; None
    when nothing needed doing.

    Fails **open** on a shard we cannot identify (``shard is None``): pre-sharding
    behaviour, and the venue's own error is the backstop. Fails **closed** on a
    transfer that did not land -- an order placed against money that never arrived
    is the failure this exists to prevent.
    """
    if shard is None or shard == source_shard:
        return True, None

    balances = shard_balances(client, (shard, source_shard))
    if not balances:
        # Client cannot answer per-shard (older API shape, or a stubbed client)
        # -- nothing to reason about. Let the venue arbitrate, as before sharding.
        return True, None

    available = balances.get(shard, 0.0)
    if available >= cost:
        return True, None

    shortfall = round(cost - available, 4)

    if shortfall > max_transfer:
        return False, (
            f"shard {shard} short ${shortfall:,.2f}, over the "
            f"${max_transfer:,.2f} single-transfer cap — not moved."
        )

    source_available = balances.get(source_shard, 0.0)
    if source_available < shortfall:
        return False, (
            f"shard {shard} short ${shortfall:,.2f} but shard "
            f"{source_shard} only holds ${source_available:,.2f}."
        )

    # `enabled` is checked AFTER the cap/source tests and skipped entirely in a
    # dry run (2026-09-08). A dry run moves no money, so the flag that governs
    # *whether we are allowed to move money* has nothing to say about it -- and
    # checking it first silently gutted the evidence window: every shard-3
    # candidate (all MLB games, the in-season sport) was refused before it could
    # be simulated, logging a `status: error` row that can never settle instead
    # of a dry-run bet that can. The cap and source-funds tests DO still run in
    # dry runs: those would block a live order for reasons unrelated to the
    # flag, so simulating past them would overstate what could fill.
    #
    # Tradeoff, deliberate: with AUTO_SHARD_TRANSFER=false a dry run now
    # simulates a bet that a live run would skip. That is right for measuring
    # the STRATEGY (does the edge model work at the tails?) and wrong for
    # measuring the PLUMBING -- hence the note says so out loud.
    if dry_run:
        off = "" if enabled else " (AUTO_SHARD_TRANSFER off — ignored in dry run)"
        return True, (
            f"[dry-run] would move ${shortfall:,.2f} " f"shard {source_shard} -> {shard}{off}"
        )

    if not enabled:
        return False, (
            f"shard {shard} holds ${available:,.2f}, needs ${cost:,.2f} "
            f"— short ${shortfall:,.2f}. AUTO_SHARD_TRANSFER is off."
        )

    log.info(
        "Auto-funding shard %s: $%.4f from shard %s (need $%.2f, have $%.2f)",
        shard,
        shortfall,
        source_shard,
        cost,
        available,
    )
    try:
        client.intra_exchange_transfer(
            shortfall, source_shard=source_shard, destination_shard=shard
        )
    except Exception as e:  # noqa: BLE001
        log.error(
            "Auto shard transfer failed (%s -> %s, $%.4f): %s", source_shard, shard, shortfall, e
        )
        return False, f"shard transfer failed: {e}"

    # Non-atomic: confirm it actually landed rather than trusting the 200.
    settled = shard_balances(client, (shard,)).get(shard, 0.0)
    if settled < cost:
        log.error(
            "Transfer to shard %s reported success but balance is $%.4f, "
            "need $%.2f — order skipped, funds may be mid-flight.",
            shard,
            settled,
            cost,
        )
        return False, (
            f"transfer to shard {shard} did not settle "
            f"(${settled:,.2f} < ${cost:,.2f}) — order skipped"
        )

    return True, (
        f"moved ${shortfall:,.2f} shard {source_shard} -> {shard} " f"(now ${settled:,.2f})"
    )


def _demo() -> None:
    """Self-check — no network, no money."""

    class FakeClient:
        def __init__(self, balances, transfer_lands=True, raises=None):
            self._b = dict(balances)
            self._lands = transfer_lands
            self._raises = raises
            self.transfers: list[tuple[float, int, int]] = []

        def get_shard_balance(self, exchange_index):
            return self._b.get(int(exchange_index), 0.0)

        def get_balance(self):
            # Deliberately account-wide and WRONG per-subaccount, mirroring the
            # real API. Nothing here may read it; the bug was that we did.
            return {
                "balance_breakdown": [
                    {"exchange_index": k, "balance": "999.0000"} for k in (0, 1, 2, 3)
                ]
            }

        def intra_exchange_transfer(self, amount, source_shard, destination_shard):
            if self._raises:
                raise self._raises
            self.transfers.append((amount, source_shard, destination_shard))
            if self._lands:
                self._b[source_shard] -= amount
                self._b[destination_shard] = self._b.get(destination_shard, 0) + amount
            return {"transfer_id": "fake"}

    kw = dict(enabled=True, source_shard=0, max_transfer=25.0, dry_run=False)

    # already funded -> no transfer
    c = FakeClient({0: 70.0, 3: 15.0})
    assert ensure_shard_funded(c, 3, 10.0, **kw) == (True, None)
    assert c.transfers == []

    # funding shard itself is never topped up from itself
    assert ensure_shard_funded(c, 0, 10.0, **kw) == (True, None)

    # unknown shard fails OPEN (pre-sharding behaviour)
    assert ensure_shard_funded(c, None, 10.0, **kw) == (True, None)

    # REGRESSION (2026-09-08): the decision must come from the per-shard read,
    # never from `balance_breakdown` -- which the fake reports as a uniform $999,
    # standing in for the real API folding another subaccount's cash in. If this
    # wallet is empty on shard 3, that must be a shortfall no matter what the
    # breakdown claims.
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **{**kw, "enabled": False})
    assert not ok and "holds $0.00" in note, note

    # a client that cannot answer per-shard fails OPEN, as before sharding
    class NoShardRead:
        def get_balance(self):
            return {"balance_breakdown": [{"exchange_index": 3, "balance": "999.0000"}]}

    assert ensure_shard_funded(NoShardRead(), 3, 10.0, **kw) == (True, None)

    # shortfall moved exactly, not rounded up
    c = FakeClient({0: 70.0, 3: 2.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **kw)
    assert ok and c.transfers == [(8.0, 0, 3)], c.transfers
    assert "moved $8.00" in note

    # over the cap -> refused, nothing moved
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 40.0, **{**kw, "max_transfer": 25.0})
    assert not ok and "cap" in note and c.transfers == []

    # source too poor -> refused
    c = FakeClient({0: 3.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **kw)
    assert not ok and "only holds" in note and c.transfers == []

    # disabled -> refused, and says so
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **{**kw, "enabled": False})
    assert not ok and "AUTO_SHARD_TRANSFER is off" in note and c.transfers == []

    # dry run -> approved, nothing moved
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **{**kw, "dry_run": True})
    assert ok and "[dry-run]" in note and c.transfers == []

    # dry run IGNORES the disabled flag (2026-09-08) -- otherwise every shard-3
    # candidate logs an un-settleable error row instead of simulated evidence.
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **{**kw, "dry_run": True, "enabled": False})
    assert ok and "ignored in dry run" in note and c.transfers == [], note

    # ...but a dry run still honours the cap and the source-funds test, which
    # would block a live order for reasons the flag has nothing to do with.
    c = FakeClient({0: 70.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 40.0, **{**kw, "dry_run": True, "max_transfer": 25.0})
    assert not ok and "cap" in note, note

    c = FakeClient({0: 3.0, 3: 0.0})
    ok, note = ensure_shard_funded(c, 3, 10.0, **{**kw, "dry_run": True})
    assert not ok and "only holds" in note, note

    # transfer raises -> refused
    c = FakeClient({0: 70.0, 3: 0.0}, raises=RuntimeError("boom"))
    ok, note = ensure_shard_funded(c, 3, 10.0, **kw)
    assert not ok and "failed" in note

    # non-atomic partial: 200 OK but money never landed -> refused
    c = FakeClient({0: 70.0, 3: 0.0}, transfer_lands=False)
    ok, note = ensure_shard_funded(c, 3, 10.0, **kw)
    assert not ok and "did not settle" in note

    print("shard_funding self-check OK")


if __name__ == "__main__":
    _demo()
