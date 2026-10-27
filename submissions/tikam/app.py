"""Streamlit UI for the URL Shortener.

Run with:  streamlit run submissions/tikam/app.py
"""

from __future__ import annotations

import streamlit as st

from shortener import (
    shorten,
    resolve,
    get_stats,
    list_all_urls,
    ShortenerError,
)
from database import init_db

st.set_page_config(page_title="URL Shortener", page_icon="🔗", layout="wide")

# ── one-time DB init ───────────────────────────────────────────────────
init_db()

# ── sidebar navigation ─────────────────────────────────────────────────
page = st.sidebar.radio("Navigate", ["🔗 Shorten URL", "🔍 Resolve / Stats", "📊 Dashboard"])

# ── Shorten page ───────────────────────────────────────────────────────
if page == "🔗 Shorten URL":
    st.title("🔗 Shorten a URL")

    with st.form("shorten_form", clear_on_submit=False):
        url = st.text_input("Destination URL", placeholder="https://example.com/very/long/path")
        col1, col2 = st.columns(2)
        with col1:
            custom_alias = st.text_input("Custom alias (optional)", placeholder="my-link")
        with col2:
            expiry_hours = st.number_input(
                "Expiry (hours, optional)", min_value=1, max_value=8760, value=None, step=1, format="%d"
            )
        submitted = st.form_submit_button("Shorten", use_container_width=True)

    if submitted:
        try:
            alias = custom_alias.strip() if custom_alias and custom_alias.strip() else None
            hours = int(expiry_hours) if expiry_hours else None
            result = shorten(url, custom_alias=alias, expiry_hours=hours)

            short_link = f"http://localhost:8501/?code={result['short_code']}"
            st.success("URL shortened successfully!")
            st.code(short_link)
            st.caption(f"Short code: `{result['short_code']}`")

            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                if result.get("is_existing"):
                    st.info("♻️ Reused existing short code (same URL)")
                else:
                    st.info("🆕 New short code generated")
            with meta_col2:
                if result.get("expires_at"):
                    st.info(f"⏰ Expires: {result['expires_at']}")
            with meta_col3:
                st.info(f"✅ Normalised: `{result['normalized_url']}`")

        except ShortenerError as e:
            st.error(str(e))

# ── Resolve / Stats page ───────────────────────────────────────────────
elif page == "🔍 Resolve / Stats":
    st.title("🔍 Resolve or Inspect a Short Code")

    code_input = st.text_input("Enter short code", placeholder="abc123")
    action = st.radio("Action", ["🔗 Resolve (simulated redirect)", "📊 Stats"], horizontal=True)

    if code_input.strip() and st.button("Go", use_container_width=True):
        code = code_input.strip()

        if action == "🔗 Resolve (simulated redirect)":
            result = resolve(code)
            if result["status"] == "found":
                st.success(f"**302 Found** → [{result['url']}]({result['url']})")
                st.caption("In production, the server returns HTTP 302 with a Location header.")
            elif result["status"] == "expired":
                st.warning("**410 Gone** — This short link has expired.")
                if result.get("expires_at"):
                    st.caption(f"Expired at: {result['expires_at']}")
            else:
                st.error("**404 Not Found** — No URL matches this short code.")

        elif action == "📊 Stats":
            stats = get_stats(code)
            if stats is None:
                st.error("**404 Not Found** — No URL matches this short code.")
            else:
                st.success(f"Stats for `{code}`")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Clicks", stats["total_clicks"])
                with col2:
                    st.metric("Last Accessed", stats.get("last_accessed") or "Never")
                with col3:
                    st.metric("Created", str(stats["created_at"])[:16])

                st.caption(f"**Original URL:** {stats['original_url']}")
                if stats.get("expires_at"):
                    st.caption(f"⏰ Expires: {stats['expires_at']}")

                if stats["clicks_per_day"]:
                    st.subheader("Clicks per Day")
                    daily_data = [{"Date": d, "Clicks": c} for d, c in stats["clicks_per_day"].items()]
                    st.bar_chart(daily_data, x="Date", y="Clicks")
                else:
                    st.caption("No clicks recorded yet.")

# ── Dashboard page ─────────────────────────────────────────────────────
elif page == "📊 Dashboard":
    st.title("📊 All Shortened URLs")
    urls = list_all_urls()

    if not urls:
        st.info("No URLs shortened yet. Go to 'Shorten URL' to create one!")
    else:
        for u in urls:
            is_expired = u["expires_at"] and u["expires_at"] <= (st.session_state.get("_now") or "")
            status = "🔴 Expired" if is_expired else "🟢 Active"
            with st.expander(
                f"`{u['short_code']}` → {u['original_url'][:60]}{'...' if len(u['original_url']) > 60 else ''}  "
                f"({u['clicks']} clicks)"
            ):
                st.markdown(f"""
                | Field | Value |
                |---|---|
                | Short Code | `{u['short_code']}` |
                | Original URL | {u['original_url']} |
                | Normalised URL | `{u['normalized_url']}` |
                | Custom | {"Yes" if u['is_custom'] else "No"} |
                | Created | {u['created_at']} |
                | Expires | {u.get('expires_at') or 'Never'} |
                | Total Clicks | {u['clicks']} |
                """)