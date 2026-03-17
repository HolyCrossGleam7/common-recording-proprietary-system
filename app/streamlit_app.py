from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from crps_sweep import export_distribution_batch_json, run_end_of_day_sweep
from crps_wallet_ledger import (
    DEFAULT_LEDGER_PATH,
    ENV_LEDGER_PATH,
    JsonLedger,
    UNIT_NAME,
    UNIT_SYMBOL,
    money_minor_from_str,
    money_minor_to_str,
)

st.set_page_config(page_title=f"CRPS — {UNIT_NAME} ({UNIT_SYMBOL})", layout="wide")
st.title("CRPS — End-of-day sweep + equal distribution")
st.caption(f"Unit: {UNIT_NAME} ({UNIT_SYMBOL}) • Amounts use minor units (cents) • Mode 1 batch export/import")

with st.sidebar:
    st.header("Storage")
    st.write(f"Env override: `{ENV_LEDGER_PATH}`")
    ledger_path = st.text_input("Ledger path", value=str(DEFAULT_LEDGER_PATH))

ledger = JsonLedger(Path(ledger_path))

tab_setup, tab_tx, tab_sweep, tab_view = st.tabs(["Setup", "Transactions", "End-of-day sweep", "View ledger"])

with tab_setup:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Register org/company wallet")
        org_id = st.text_input("Org ID (<=20 chars)", key="org_id")
        if st.button("Add org"):
            try:
                ledger.add_org(org_id)
                st.success(f"Added org: {org_id}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.write("Current orgs:")
        st.dataframe(ledger.list_orgs(), use_container_width=True)

    with c2:
        st.subheader("Register person ID")
        person_id = st.text_input("Person ID (<=20 chars)", key="person_id")
        if st.button("Add person"):
            try:
                ledger.add_person(person_id)
                st.success(f"Added person: {person_id}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.write("Current people:")
        st.dataframe(ledger.list_people(), use_container_width=True)

with tab_tx:
    st.subheader("Record a transaction (org/company activity)")
    sender = st.text_input("senderId", placeholder="orgA")
    receiver = st.text_input("receiverId", placeholder="orgB or personX")
    amt = st.text_input(f"amount ({UNIT_SYMBOL})", value="1.00")
    memo = st.text_input("memo", value="activity")

    if st.button("Post transaction"):
        try:
            minor = money_minor_from_str(amt)
            if minor <= 0:
                raise ValueError("Amount must be > 0")
            ledger.post_tx(sender, receiver, minor, memo=memo)
            st.success(f"Posted {amt} {UNIT_SYMBOL} from {sender} -> {receiver}")
            st.rerun()
        except Exception as e:
            st.error(str(e))

with tab_sweep:
    st.subheader("Run end-of-day sweep")
    st.write("This will sweep *all positive* org balances to `pool` and distribute equally to all people.")
    memo = st.text_input("Sweep memo prefix", value="EOD")

    if st.button("Run sweep now"):
        try:
            result = run_end_of_day_sweep(ledger, memo=memo)
            st.success(f"Swept total: {money_minor_to_str(result.total_swept_minor)} {UNIT_SYMBOL}")

            st.write("Sweeps from orgs -> pool:")
            st.dataframe(result.swept_from_orgs, use_container_width=True)

            st.write("Distributions from pool -> people:")
            st.dataframe(result.distributions, use_container_width=True)

            batch = export_distribution_batch_json(result)
            st.download_button(
                "Download distribution batch JSON",
                data=json.dumps(batch, indent=2, ensure_ascii=False),
                file_name="distribution_batch.json",
                mime="application/json",
            )
        except Exception as e:
            st.error(str(e))

with tab_view:
    st.subheader("Balances (replay)")
    bals = ledger.replay_balances_minor()
    rows = [{"id": k, "balance": money_minor_to_str(v)} for k, v in sorted(bals.items(), key=lambda x: x[0])]
    st.dataframe(rows, use_container_width=True)

    st.subheader("Transactions")
    st.dataframe(ledger.list_transactions(), use_container_width=True)
