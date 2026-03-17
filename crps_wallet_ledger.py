from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

UNIT_NAME = "Phoenix"
UNIT_SYMBOL = "Φ"

ENV_LEDGER_PATH = "CRPS_LEDGER_PATH"
DEFAULT_LEDGER_PATH = Path("data") / "ledger.json"

MAX_ID_LEN = 20  # LoRa packet constraint


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_id(id_: str) -> str:
    id_ = (id_ or "").strip()
    if not id_:
        raise ValueError("ID cannot be empty")
    if len(id_) > MAX_ID_LEN:
        raise ValueError(f"ID too long (max {MAX_ID_LEN} chars): {id_!r}")
    return id_


def money_minor_from_str(amount: str) -> int:
    """
    Convert a decimal string like '12.34' to minor units int 1234.
    Avoid floats; do strict parsing.
    """
    s = (amount or "").strip()
    if not s:
        raise ValueError("Amount is required")

    neg = s.startswith("-")
    if neg:
        s = s[1:].strip()

    if "." in s:
        whole, frac = s.split(".", 1)
    else:
        whole, frac = s, ""

    whole = whole.strip() or "0"
    frac = (frac.strip() + "00")[:2]  # pad/truncate to 2

    if not whole.isdigit() or not frac.isdigit():
        raise ValueError("Amount must be numeric with up to 2 decimals")

    minor = int(whole) * 100 + int(frac)
    return -minor if neg else minor


def money_minor_to_str(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    minor = abs(int(minor))
    return f"{sign}{minor // 100}.{minor % 100:02d}"


@dataclass(frozen=True)
class Tx:
    id: str
    timestamp: str
    senderId: str
    receiverId: str
    amountMinor: int
    memo: str = ""


class JsonLedger:
    """
    Ledger format:
    {
      "meta": {"unit": "Phoenix", "symbol": "Φ"},
      "people": ["alice", ...],
      "orgs": ["orgA", ...],
      "transactions": [
        {"id": "...", "timestamp": "...", "senderId": "orgA", "receiverId": "bob", "amountMinor": 1234, "memo": "..."}
      ]
    }
    """

    def __init__(self, path: Optional[Path] = None):
        env = os.getenv(ENV_LEDGER_PATH)
        self.path = Path(env) if env else Path(path or DEFAULT_LEDGER_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {
                "meta": {"unit": UNIT_NAME, "symbol": UNIT_SYMBOL},
                "people": [],
                "orgs": [],
                "transactions": [],
            }
            self.save()

        self.data.setdefault("meta", {"unit": UNIT_NAME, "symbol": UNIT_SYMBOL})
        self.data.setdefault("people", [])
        self.data.setdefault("orgs", [])
        self.data.setdefault("transactions", [])
        self.data["meta"].setdefault("unit", UNIT_NAME)
        self.data["meta"].setdefault("symbol", UNIT_SYMBOL)

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def meta(self) -> Dict[str, str]:
        return dict(self.data.get("meta", {}))

    def list_people(self) -> List[str]:
        return list(self.data["people"])

    def list_orgs(self) -> List[str]:
        return list(self.data["orgs"])

    def add_person(self, person_id: str) -> None:
        pid = validate_id(person_id)
        if pid not in self.data["people"]:
            self.data["people"].append(pid)
            self.data["people"].sort()
            self.save()

    def add_org(self, org_id: str) -> None:
        oid = validate_id(org_id)
        if oid not in self.data["orgs"]:
            self.data["orgs"].append(oid)
            self.data["orgs"].sort()
            self.save()

    def list_transactions(self) -> List[Dict[str, Any]]:
        return list(self.data["transactions"])

    def new_tx_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        n = len(self.data["transactions"])
        return f"tx_{ts}_{n}"

    def post_tx(self, sender_id: str, receiver_id: str, amount_minor: int, memo: str = "") -> Dict[str, Any]:
        sender = validate_id(sender_id)
        receiver = validate_id(receiver_id)
        if sender == receiver:
            raise ValueError("senderId and receiverId must differ")
        if int(amount_minor) <= 0:
            raise ValueError("amountMinor must be > 0")

        tx = Tx(
            id=self.new_tx_id(),
            timestamp=utc_now_iso(),
            senderId=sender,
            receiverId=receiver,
            amountMinor=int(amount_minor),
            memo=memo or "",
        )
        d = tx.__dict__
        self.data["transactions"].append(d)
        self.save()
        return d

    def replay_balances_minor(self) -> Dict[str, int]:
        balances: Dict[str, int] = {}
        for t in self.data["transactions"]:
            try:
                s = t["senderId"]
                r = t["receiverId"]
                a = int(t["amountMinor"])
            except Exception:
                continue
            balances[s] = balances.get(s, 0) - a
            balances[r] = balances.get(r, 0) + a
        return balances

    def replay_balances_str(self) -> Dict[str, str]:
        return {k: money_minor_to_str(v) for k, v in self.replay_balances_minor().items()}
