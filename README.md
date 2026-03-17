# Common Recording Proprietary System (CRPS)

This tool simulates democratic economic distribution using **Phoenix (Φ)** credits.  
Organizations generate positive balances during the day through transactions.  
At the end of the day, all org balances are swept to zero and distributed equally across all registered people.  
Batch export is compatible with Community Credit Mesh (desktop, PWA, LoRa).

---

## Setup (EndeavourOS / Arch Linux)

```bash
sudo pacman -Syu
sudo pacman -S python python-pip python-virtualenv git
```
Clone and set up:
```bash
git clone https://github.com/HolyCrossGleam7/common-recording-proprietary-system.git
cd common-recording-proprietary-system

python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Run (Streamlit)

```bash
streamlit run app/streamlit_app.py
```
Streamlit will provide a web dashboard (usually at http://localhost:8501).

---

## Workflow

1. **Register org/company wallets** (IDs ≤ 20 chars)
2. **Register people** (IDs ≤ 20 chars; same as CCM/LoRa/PWA wallets)
3. **Record transactions** (org or org→person)
4. **End-of-day sweep**  
   - All positive org balances swept to `pool`
   - Pool is distributed equally to all people; deterministic rounding (2 decimals, minor units)
   - Any org with a negative balance blocks sweep and shows error
5. **Export batch**  
   - Download JSON batch: portable for CCM desktop/PWA/LoRa
   - Example format below

---

## Credit unit

- **Phoenix (Φ)**  
- All amounts are stored as **minor units**:  
  - `1234` = `12.34 Φ`  
  - `"amountMinor"`: integer cents for accuracy/compatibility

---

## Example batch file (Option A)

```json
{
  "type": "crps_distribution_batch_v1",
  "unit": "Phoenix",
  "symbol": "Φ",
  "from": "pool",
  "totalSweptMinor": 345,
  "items": [
    {"to": "alice", "amountMinor": 123},
    {"to": "bob", "amountMinor": 122},
    {"to": "carol", "amountMinor": 100}
  ]
}
```

Each entry: `pool` → `to` for `amountMinor` credits, ready to import/broadcast in CCM.

---

## Troubleshooting

- All IDs must be **≤ 20 chars**
- No orgs can have negative balances at sweep time
- Use the **Streamlit app** interface for workflow, batch export
- All output is compatible with CCM apps (desktop, PWA, LoRa)

---

## License

GNU GPLv3 — see LICENSE for details.
