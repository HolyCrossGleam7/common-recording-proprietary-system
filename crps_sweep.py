from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from crps_wallet_ledger import JsonLedger, money_minor_to_str

POOL_ID = "pool"  # must be <= 20 chars


@dataclass(frozen=True)
class SweepResult:
    swept_from_orgs: List[dict]
    distributions: List[dict]
    total_swept_minor: int


def compute_equal_distribution(total_minor: int, people_ids: List[str]) -> List[Tuple[str, int]]:
    """
    Deterministic split of integer cents:
    - base = floor(total / n)
    - remainder cents distributed to people in sorted order
    Returns list of (person_id, amount_minor).
    """
    if total_minor < 0:
        raise ValueError("total_minor cannot be negative")
    if not people_ids:
        raise ValueError("people_ids cannot be empty")

    ids = sorted(people_ids)
    n = len(ids)

    base = total_minor // n
    rem = total_minor - base * n

    out: List[Tuple[str, int]] = []
    for i, pid in enumerate(ids):
        extra = 1 if i < rem else 0
        out.append((pid, base + extra))
    return out


def run_end_of_day_sweep(ledger: JsonLedger, memo: str = "end_of_day") -> SweepResult:
    """
    Sweep *all positive* org balances to POOL_ID, then distribute pool equally to all people.
    Ensures:
      - org balances go to 0 (assuming they were >= 0)
      - pool goes back to 0 after distribution
    """
    balances = ledger.replay_balances_minor()
    orgs = ledger.list_orgs()
    people = ledger.list_people()

    if not people:
        raise ValueError("No people registered to distribute to.")
    if not orgs:
        raise ValueError("No orgs registered to sweep from.")

    swept_txs: List[dict] = []
    total_swept = 0

    # 1) Sweep org positives into pool
    for org_id in sorted(orgs):
        bal = int(balances.get(org_id, 0))
        if bal > 0:
            tx = ledger.post_tx(org_id, POOL_ID, bal, memo=f"{memo}:sweep")
            swept_txs.append(tx)
            total_swept += bal

    # 2) Distribute pool equally
    if total_swept == 0:
        return SweepResult(swept_from_orgs=swept_txs, distributions=[], total_swept_minor=0)

    dist_plan = compute_equal_distribution(total_swept, people)

    dist_txs: List[dict] = []
    for pid, amt in dist_plan:
        if amt <= 0:
            continue
        tx = ledger.post_tx(POOL_ID, pid, amt, memo=f"{memo}:dist")
        dist_txs.append(tx)

    return SweepResult(swept_from_orgs=swept_txs, distributions=dist_txs, total_swept_minor=total_swept)


def export_distribution_batch_json(result: SweepResult) -> dict:
    items = [{"to": tx["receiverId"], "amountMinor": int(tx["amountMinor"])} for tx in result.distributions]
    return {
        "type": "crps_distribution_batch_v1",
        "unit": "Phoenix",
        "symbol": "Φ",
        "from": POOL_ID,
        "totalSweptMinor": int(result.total_swept_minor),
        "items": items,
    }
