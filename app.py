import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import streamlit as st
import json, os, base64
from datetime import date
from scraper import scrape_hn
from mailer  import (
    add_subscriber, remove_subscriber,
    send_welcome_email, load_subscribers,
    send_daily_newsletters, send_to_subscriber
)

ARCHIVE_FILE = "hn_daily_archive.json"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YC Daily",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.caption(" >> Developers info & Navigation button on top left")
# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d0d0d !important;
    color: #e8e0d0 !important;
}
[data-testid="stSidebar"] {
    background-color: #0a0a0a !important;
    border-right: 1px solid #ff6600;
}
#MainMenu, footer { visibility: hidden; }
h1,h2,h3 { font-family:'Bebas Neue',sans-serif; letter-spacing:2px; }
p,div,span,label { font-family:'IBM Plex Mono',monospace; }

.hn-divider { border:none; border-top:2px solid #ff6600; margin:0.4rem 0 1.4rem 0; }

/* Cards */
.article-card {
    background:#161616; border-left:4px solid #ff6600;
    border-radius:2px; padding:14px 18px; margin-bottom:10px;
}
.rank-num  { font-family:'Bebas Neue',sans-serif; font-size:2rem; color:#ff6600; line-height:1; }
.art-title { font-size:0.92rem; font-weight:600; color:#f0ead8; margin:4px 0 6px 0; line-height:1.4; }
.art-link  { font-size:0.72rem; color:#555; word-break:break-all; }
.badge     { background:#ff6600; color:#000; font-family:'Bebas Neue',sans-serif;
             font-size:1.05rem; padding:2px 10px; border-radius:2px; float:right; }

/* Archive */
.day-hdr   { font-family:'Bebas Neue',sans-serif; font-size:1.5rem; color:#ff6600;
             border-bottom:1px solid #222; padding-bottom:4px; margin:22px 0 10px 0; }
.arc-row   { display:flex; gap:14px; padding:9px 0; border-bottom:1px solid #1a1a1a; align-items:flex-start; }
.arc-rank  { color:#444; font-size:0.78rem; min-width:26px; }
.arc-title { color:#e8e0d0; font-size:0.83rem; flex:1; }
.arc-score { color:#ff6600; font-size:0.83rem; font-weight:600; white-space:nowrap; }

/* Subscribe form */
.sub-wrap  { max-width:500px; margin:0 auto; padding:40px 0; }
.sub-card  { background:#141414; border:1px solid #ff6600; border-radius:4px; padding:36px 32px; }
.sub-title { font-family:'Bebas Neue',sans-serif; font-size:2.4rem; color:#ff6600;
             letter-spacing:3px; margin-bottom:4px; }
.sub-sub   { font-family:'IBM Plex Mono',monospace; font-size:0.78rem; color:#555;
             margin-bottom:28px; }

/* Unsubscribe */
.unsub-wrap { max-width:440px; margin:60px auto; text-align:center; }
.unsub-icon { font-size:3rem; margin-bottom:12px; }
.unsub-title{ font-family:'Bebas Neue',sans-serif; font-size:2rem; color:#ff6600; letter-spacing:2px; }
.unsub-body { font-family:'IBM Plex Mono',monospace; font-size:0.82rem; color:#777; margin:12px 0 28px 0; }

/* Sidebar */
.sb-logo { font-family:'Bebas Neue',sans-serif; font-size:1.9rem; color:#ff6600; letter-spacing:3px; }

/* Streamlit input overrides */
input[type=text], input[type=email] {
    background:#0d0d0d !important; color:#e8e0d0 !important;
    border:1px solid #333 !important; border-radius:2px !important;
    font-family:'IBM Plex Mono',monospace !important;
}
input[type=text]:focus, input[type=email]:focus { border-color:#ff6600 !important; }
div[data-testid="stSelectbox"] > div { background:#0d0d0d !important; }
</style>
""", unsafe_allow_html=True)


# ── Query param check for unsubscribe deep-link ───────────────────────────────
# When user clicks Unsubscribe in email, URL has ?unsub=<base64email>
params      = st.query_params
unsub_param = params.get("unsub", None)   # None if not present


# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sb-logo">YC DAILY</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "nav",
        ["📬  Subscribe", "🔥  Live Rankings", "📅  Daily Archive", "🚪  Unsubscribe"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown(
        "<p style=\"color:#555;font-size:0.68rem;margin:0 0 4px 0;line-height:1.6;\">"
        "Data source:<br>"
        "<a href=\"https://news.ycombinator.com\" target=\"_blank\" style=\"color:#ff6600;text-decoration:none;\">news.ycombinator.com · Y Combinator</a>"
        "</p>"
        "<p style=\"color:#888;font-size:0.61rem;line-height:1.7;margin:0 0 12px 0;border-left:2px solid #ff6600;padding-left:8px;\">"
        "Scrapes public data from Hacker News for <strong style=\"color:#bbb;\">educational &amp; portfolio purposes only.</strong> "
        "Not affiliated with or endorsed by Y Combinator."
        "</p>"
        "<div style=\"border-top:1px solid #222;padding-top:12px;margin-top:4px;\">"
        "<p style=\"color:#666;font-size:0.62rem;margin:0 0 4px 0;font-weight:700;letter-spacing:1.5px;\">CREATED BY</p>"
        "<p style=\"color:#ff6600;font-size:0.78rem;font-weight:700;margin:0 0 12px 0;letter-spacing:2px;\">ADITYA PAWAR</p>"
        "<p style=\"margin:0 0 8px 0;\">"
        "<a href=\"mailto:adityabpawar.work@gmail.com\" style=\"color:#aaa;font-size:0.62rem;text-decoration:none;word-break:break-all;\">✉ adityabpawar.work@gmail.com</a>"
        "</p>"
        "<p style=\"margin:0 0 2px 0;\">"
        "<a href=\"https://www.linkedin.com/in/aditya-pawar-345908401\" target=\"_blank\" style=\"color:#aaa;font-size:0.62rem;font-weight:600;text-decoration:none;\">🔗 LinkedIn</a>"
        "</p>"
        "<p style=\"margin:0 0 10px 0;\">"
        "<a href=\"https://www.linkedin.com/in/aditya-pawar-345908401\" target=\"_blank\" style=\"color:#555;font-size:0.58rem;text-decoration:none;word-break:break-all;\">linkedin.com/in/aditya-pawar-345908401</a>"
        "</p>"
        "<p style=\"margin:0 0 2px 0;\">"
        "<a href=\"https://github.com/apcodes04\" target=\"_blank\" style=\"color:#aaa;font-size:0.62rem;font-weight:600;text-decoration:none;\">🐙 GitHub</a>"
        "</p>"
        "<p style=\"margin:0 0 4px 0;\">"
        "<a href=\"https://github.com/apcodes04\" target=\"_blank\" style=\"color:#555;font-size:0.58rem;text-decoration:none;\">github.com/apcodes04</a>"
        "</p>"
        "</div>",
        unsafe_allow_html=True
    )

# Auto-navigate to Unsubscribe page if deep-link param present
if unsub_param:
    page = "🚪  Unsubscribe"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — SUBSCRIBE
# ══════════════════════════════════════════════════════════════════════════════
if page == "📬  Subscribe":

    st.markdown("# 📬 SUBSCRIBE")
    st.markdown('<div class="hn-divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="sub-wrap">
    <div class="sub-card">
        <div class="sub-title">GET YC DAILY</div>
        <div class="sub-sub">Top 10 Hacker News articles delivered to your inbox every day.</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown("<br>", unsafe_allow_html=True)

        email = st.text_input(
            "Your Email Address",
            placeholder="you@gmail.com",
            key="sub_email"
        )

        # Time picker — hour and minute dropdowns
        st.markdown(
            '<p style="font-size:0.8rem;color:#888;margin-bottom:4px;">Daily Send Time</p>',
            unsafe_allow_html=True
        )
        tcol1, tcol2 = st.columns(2)
        with tcol1:
            hour = st.selectbox(
                "Hour", [f"{h:02d}" for h in range(24)],
                index=8,   # Default 08
                key="sub_hour",
                label_visibility="collapsed"
            )
        with tcol2:
            minute = st.selectbox(
                "Minute", ["00", "15", "30", "45"],
                index=0,
                key="sub_minute",
                label_visibility="collapsed"
            )

        send_time = f"{hour}:{minute}"   # e.g. '08:00'

        st.markdown(
            f'<p style="font-size:0.75rem;color:#555;margin:6px 0 18px 0;">'
            f'You will receive your first email now, then daily at <strong style="color:#ff6600;">'
            f'{send_time}</strong></p>',
            unsafe_allow_html=True
        )

        if st.button("Subscribe →", use_container_width=True, key="sub_btn"):
            if not email or "@" not in email:
                st.error("Please enter a valid email address.")
            else:
                added = add_subscriber(email, send_time)
                with st.spinner("🔍 Scraping Hacker News live..."):
                    try:
                        if added:
                            send_welcome_email(email, send_time)
                        ranked, today = send_daily_newsletters()
                        send_to_subscriber(email, ranked, today)
                        if added:
                            st.success(f"✅ Subscribed! Welcome email + today's Top 10 sent to **{email}**")
                            st.info(f"📅 You'll receive daily updates at **{send_time}**")
                        else:
                            st.info(f"📧 **{email}** is already subscribed — today's fresh Top 10 has been resent!")
                    except Exception as e:
                        if added:
                            st.warning(f"Subscribed but email failed: {e}")
                        else:
                            st.warning(f"Already subscribed but resend failed: {e}")

        # Show live subscriber count (base offset added for display)
        subs  = load_subscribers()
        real_count = sum(1 for s in subs.values() if s["active"])
        display_count = real_count + 1545
        st.markdown(
            f'<p style="text-align:center;font-size:1rem;color:#ff6600;margin-top:24px;font-weight:900;letter-spacing:1px;">&#x1F525; <strong>{display_count} active subscribers</strong></p>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — LIVE RANKINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔥  Live Rankings":

    st.markdown("# 🔥 HACKER NEWS")
    st.markdown('<div class="hn-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#444;font-size:0.76rem;margin-bottom:1.4rem;">'
                'Ranked by upvotes · refreshes on demand</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        refresh = st.button("⟳  Refresh", use_container_width=True)
    with c2:
        save_btn = st.button("💾  Save Today's Top 10", use_container_width=True)

    if "ranked" not in st.session_state or refresh:
        with st.spinner("Scraping Hacker News..."):
            st.session_state.ranked = scrape_hn()

    ranked = st.session_state.ranked

    if save_btn:
        from mailer import save_today
        saved = save_today(ranked)
        st.success(f"Saved top 10 for {saved}!")

    st.markdown(f'<p style="color:#333;font-size:0.72rem;">{len(ranked)} articles</p>',
                unsafe_allow_html=True)
    st.markdown("---")

    for rank, (upvotes, title, link) in enumerate(ranked, start=1):
        full = link if link.startswith("http") else f"https://news.ycombinator.com/{link}"
        st.markdown(f"""
        <div class="article-card">
            <span class="badge">▲ {upvotes}</span>
            <div class="rank-num">#{rank}</div>
            <div class="art-title">{title}</div>
            <div class="art-link">
                <a href="{full}" target="_blank" style="color:#ff6600;text-decoration:none;">{full}</a>
            </div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — DAILY ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅  Daily Archive":

    st.markdown("# 📅 DAILY ARCHIVE")
    st.markdown('<div class="hn-divider"></div>', unsafe_allow_html=True)

    archive = {}
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE) as f:
            archive = json.load(f)

    if not archive:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#333;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;">NO DATA YET</div>
            <p style="font-size:0.82rem;margin-top:8px;">
                Go to Live Rankings and click 💾 Save Today's Top 10
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        for day in sorted(archive.keys(), reverse=True):
            st.markdown(f'<div class="day-hdr">📆 {day}</div>', unsafe_allow_html=True)
            html = ""
            for i, a in enumerate(archive[day], 1):
                lnk = a["link"] if a["link"].startswith("http") else f"https://news.ycombinator.com/{a['link']}"
                html += f"""
                <div class="arc-row">
                  <span class="arc-rank">#{i}</span>
                  <span class="arc-title">
                    <a href="{lnk}" target="_blank" style="color:#e8e0d0;text-decoration:none;">
                      {a['title']}</a></span>
                  <span class="arc-score">▲ {a['upvotes']}</span>
                </div>"""
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")
        st.download_button(
            "⬇  Download Archive (JSON)",
            data=json.dumps(archive, indent=2),
            file_name="hn_archive.json",
            mime="application/json"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — UNSUBSCRIBE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚪  Unsubscribe":

    st.markdown("# 🚪 UNSUBSCRIBE")
    st.markdown('<div class="hn-divider"></div>', unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown('<br>', unsafe_allow_html=True)

        # Pre-fill email if coming from the email deep-link
        prefill = ""
        if unsub_param:
            try:
                prefill = base64.urlsafe_b64decode(unsub_param.encode()).decode()
            except Exception:
                prefill = ""

        st.markdown("""
        <div style="text-align:center;margin-bottom:24px;">
            <div style="font-size:2.5rem;">😔</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                        color:#ff6600;letter-spacing:2px;">Sorry to see you go</div>
            <p style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;
                      color:#555;margin-top:8px;">
                Enter your email below to unsubscribe from YC Daily.
            </p>
        </div>""", unsafe_allow_html=True)

        unsub_email = st.text_input(
            "Email to unsubscribe",
            value=prefill,              # Auto-filled if coming from email link
            placeholder="you@gmail.com",
            key="unsub_email"
        )

        if st.button("Unsubscribe", use_container_width=True, key="unsub_btn"):
            if not unsub_email or "@" not in unsub_email:
                st.error("Please enter a valid email address.")
            else:
                removed = remove_subscriber(unsub_email)
                if removed:
                    st.success(f"✅ **{unsub_email}** has been unsubscribed.")
                    st.markdown(
                        '<p style="font-size:0.78rem;color:#555;text-align:center;margin-top:12px;">'
                        'You won\'t receive any more emails from us.</p>',
                        unsafe_allow_html=True
                    )
                    # Clear the URL param so page looks clean
                    st.query_params.clear()
                else:
                    st.warning(f"**{unsub_email}** was not found or already unsubscribed.")

        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(
            '<p style="text-align:center;font-size:0.72rem;color:#2a2a2a;">'
            'Changed your mind? <a href="/" style="color:#ff6600;">Subscribe again</a></p>',
            unsafe_allow_html=True
        )
