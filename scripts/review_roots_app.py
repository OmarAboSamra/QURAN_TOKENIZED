"""
Streamlit app for reviewing staged root corrections.

Launch with:
    streamlit run scripts/review_roots_app.py

The app reads ``data/root_review_staging.json`` (populated by the
reviewing agent via ``review_roots_stage.py``) and shows a table of
suspected-incorrect roots.  The human can:

    - Approve individual corrections (with optional root override)
    - Reject corrections they disagree with
    - Apply approved corrections to the database

Approved items are written to ``data/root_review_approved.json`` for
``review_roots_apply.py`` to commit to the database.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# sys.path fixup for backend imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

# ── File paths ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STAGING_FILE = DATA_DIR / "root_review_staging.json"
APPROVED_FILE = DATA_DIR / "root_review_approved.json"


# ── Helpers ─────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            return json.loads(text)
    return {"version": 1, "corrections": []}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Page config ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Root Review — Quran Backend",
    page_icon="📖",
    layout="wide",
)

# RTL support for Arabic text
st.markdown("""
<style>
    .arabic { direction: rtl; text-align: right; font-size: 1.3em; font-family: 'Traditional Arabic', 'Amiri', serif; }
    .root-tag { background: #e8f5e9; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .root-old { background: #ffebee; padding: 2px 8px; border-radius: 4px; text-decoration: line-through; }
    .conf-high { color: #2e7d32; font-weight: bold; }
    .conf-medium { color: #f57f17; }
    .conf-low { color: #c62828; }
    div[data-testid="stForm"] { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
</style>
""", unsafe_allow_html=True)


# ── Main UI ─────────────────────────────────────────────────────────

st.title("📖 Root Review Dashboard")

staging = load_json(STAGING_FILE)
approved_data = load_json(APPROVED_FILE)
corrections = staging.get("corrections", [])
approved_list = approved_data.get("corrections", [])

# Metrics row
col1, col2, col3 = st.columns(3)
col1.metric("Staged", len(corrections))
col2.metric("Approved (pending apply)", len(approved_list))
col3.metric("Target batch", "200")

if not corrections:
    st.info(
        "No corrections are staged for review. "
        "The reviewing agent needs to run first to populate "
        "`data/root_review_staging.json`."
    )
    st.stop()

st.markdown("---")
st.subheader(f"Review {len(corrections)} staged corrections")
st.caption(
    "Check **Approve** for corrections you agree with. "
    "You can edit the suggested root before approving. "
    "Use **Reject** to remove incorrect suggestions."
)

# ── Build the review form ───────────────────────────────────────────

with st.form("review_form"):
    decisions: list[dict] = []

    for idx, c in enumerate(corrections):
        with st.container():
            cols = st.columns([0.5, 2, 1.5, 1, 1.5, 1.5, 2.5, 1, 1])

            # Column 0: row number
            cols[0].markdown(f"**{idx + 1}**")

            # Column 1: Arabic word (RTL)
            cols[1].markdown(
                f'<div class="arabic">{c["text_ar"]}</div>',
                unsafe_allow_html=True,
            )

            # Column 2: Location
            cols[2].markdown(f'`{c["sura"]}:{c["aya"]}:{c["position"]}`')

            # Column 3: normalized
            cols[3].markdown(
                f'<div class="arabic">{c["normalized"]}</div>',
                unsafe_allow_html=True,
            )

            # Column 4: current root (strikethrough)
            current = c.get("current_root") or "—"
            cols[4].markdown(
                f'<span class="root-old arabic">{current}</span>',
                unsafe_allow_html=True,
            )

            # Column 5: suggested root (editable)
            edited_root = cols[5].text_input(
                "Root",
                value=c["suggested_root"],
                key=f"root_{idx}",
                label_visibility="collapsed",
            )

            # Column 6: reason
            cols[6].markdown(f'<small>{c["reason"]}</small>', unsafe_allow_html=True)

            # Column 7: confidence badge
            conf = c.get("confidence", "medium")
            conf_class = f"conf-{conf}"
            cols[7].markdown(
                f'<span class="{conf_class}">{conf}</span>',
                unsafe_allow_html=True,
            )

            # Column 8: approve checkbox
            approve = cols[8].checkbox("✓", key=f"approve_{idx}")

            decisions.append({
                "index": idx,
                "entry": c,
                "edited_root": edited_root,
                "approved": approve,
            })

        # Light separator
        if idx < len(corrections) - 1:
            st.markdown("<hr style='margin:2px 0; border: none; border-top: 1px solid #eee;'>",
                        unsafe_allow_html=True)

    # ── Action buttons ──────────────────────────────────────────────
    st.markdown("---")
    bcol1, bcol2, bcol3 = st.columns([1, 1, 2])
    approve_btn = bcol1.form_submit_button("✅ Approve selected", type="primary")
    reject_btn = bcol2.form_submit_button("❌ Reject selected")


# ── Handle form submission ──────────────────────────────────────────

if approve_btn:
    approved_entries = [d for d in decisions if d["approved"]]
    if not approved_entries:
        st.warning("No corrections selected. Check the boxes first.")
    else:
        # Move approved items from staging → approved file
        approved_data = load_json(APPROVED_FILE)
        approved_corrections = approved_data.get("corrections", [])

        approved_ids = set()
        for d in approved_entries:
            entry = {**d["entry"]}
            entry["final_root"] = d["edited_root"]  # human may have edited it
            entry["approved_at"] = datetime.now(timezone.utc).isoformat()
            approved_corrections.append(entry)
            approved_ids.add(d["entry"]["token_id"])

        approved_data["corrections"] = approved_corrections
        save_json(APPROVED_FILE, approved_data)

        # Remove approved items from staging
        staging["corrections"] = [
            c for c in staging["corrections"]
            if c["token_id"] not in approved_ids
        ]
        save_json(STAGING_FILE, staging)

        st.success(
            f"Approved {len(approved_entries)} corrections. "
            f"{len(staging['corrections'])} remaining in staging. "
            f"{len(approved_corrections)} total pending apply."
        )
        st.rerun()

if reject_btn:
    rejected_entries = [d for d in decisions if d["approved"]]
    if not rejected_entries:
        st.warning("No corrections selected. Check the boxes of items to reject.")
    else:
        rejected_ids = {d["entry"]["token_id"] for d in rejected_entries}
        staging["corrections"] = [
            c for c in staging["corrections"]
            if c["token_id"] not in rejected_ids
        ]
        save_json(STAGING_FILE, staging)

        st.success(
            f"Rejected {len(rejected_entries)} corrections. "
            f"{len(staging['corrections'])} remaining in staging."
        )
        st.rerun()


# ── Sidebar: Apply approved corrections ─────────────────────────────

with st.sidebar:
    st.header("Apply Corrections")
    approved_data = load_json(APPROVED_FILE)
    pending_count = len(approved_data.get("corrections", []))

    st.metric("Approved & pending apply", pending_count)

    if pending_count > 0:
        st.markdown(
            "Run this command to apply approved corrections to the database:"
        )
        st.code(
            "python scripts/review_roots_apply.py",
            language="bash",
        )
        st.caption("Add `--dry-run` to preview changes without committing.")

        if st.button("🔄 Apply now (from this UI)"):
            try:
                from scripts.review_roots_apply import apply_approved
                applied, errors = apply_approved(dry_run=False)
                if errors:
                    st.warning(f"Applied {applied} corrections with {len(errors)} errors.")
                    for err in errors[:5]:
                        st.error(err)
                else:
                    st.success(f"Successfully applied {applied} corrections to the database!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.header("Quick Stats")
    staging = load_json(STAGING_FILE)
    st.write(f"**Staging file:** {STAGING_FILE.name}")
    st.write(f"**Staged:** {len(staging.get('corrections', []))}")
    st.write(f"**Approved file:** {APPROVED_FILE.name}")
    st.write(f"**Pending apply:** {pending_count}")
