with right:
    # --- One unified card ---
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    # Ministry Tracker
    st.markdown("<div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="mini-grid">
          <div class="mini-card"><div class="mini-label">Prayer</div><div class="mini-value">{ministry['prayer']}</div></div>
          <div class="mini-card"><div class="mini-label">Studies</div><div class="mini-value">{ministry['studies']}</div></div>
          <div class="mini-card"><div class="mini-label">Follow Ups</div><div class="mini-value">{ministry.get('follow_ups', 0)}</div></div>
          <div class="mini-card"><div class="mini-label">Baptisms</div><div class="mini-value">{ministry['baptisms']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Divider
    st.markdown("<hr style='border:0;border-top:1px solid rgba(255,255,255,.15);margin:12px 0'>", unsafe_allow_html=True)

    # Channel Stats
    st.markdown("<div class='section'>Channel Stats</div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="kpi-card youtube" style="width:100%;text-align:left;">
          <div class="kpi-head">
            <i class="fa-brands fa-youtube icon" style="color:#ff3d3d"></i>
            <span class="kpi-name">YouTube</span>
          </div>
          <div class="kpi-label">Subscribers</div><div class="kpi-value">{fmt_num(youtube['subs'])}</div>
          <div class="kpi-label">Total Views</div><div class="kpi-value">{fmt_num(youtube['total'])}</div>
        </div>
    """, unsafe_allow_html=True)

    # YouTube Views (7-day)
    st.markdown("<div class='section'>YouTube Views (Last 7 Days, complete data only)</div>", unsafe_allow_html=True)
    st.markdown("<div class='small'>ℹ️ YouTube Analytics can lag up to 48h. Latest day may be missing until processed.</div>", unsafe_allow_html=True)

    vals = yt_last7_vals[:]
    maxv = max(vals) if vals else 1
    for d, v in zip(yt_last7_labels, vals):
        pct = int((v / maxv) * 100) if maxv else 0
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{d}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{fmt_num(int(v))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # close unified card
