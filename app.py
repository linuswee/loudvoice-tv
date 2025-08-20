import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")

# Load assets
ASSETS = Path(__file__).parent / "assets"

def svg_str(name: str) -> str:
    p = ASSETS / name
    return p.read_text(encoding="utf-8") if p.exists() else ""

# Header with logo
st.markdown(
    f"""
    <div style='display:flex; align-items:center; justify-content:center; margin-bottom:20px;'>
        <img src="data:image/svg+xml;utf8,{svg_str('logo_placeholder.svg')}" width="60">
        <h1 style='color:yellow; margin-left:15px;'>LOUDVOICE Dashboard</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Mock data
views_data = pd.DataFrame({
    "Category": ["Music Videos", "Reels"],
    "Views": [12340, 8450]
})

map_data = pd.DataFrame({
    "Country": ["Malaysia", "Thailand", "Philippines", "Indonesia"],
    "Views": [3400, 2200, 1800, 1400]
})

tasks_data = pd.DataFrame({
    "Task": ["Prepare filming", "Edit reels", "Upload content", "Team meeting"],
    "Status": ["Not Ready", "In Progress", "Done", "In Progress"]
})

# Charts row
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Global Reach (Last 7 Days)")
    fig_map = px.choropleth(
        map_data, locations="Country", locationmode="country names",
        color="Views", hover_name="Country",
        color_continuous_scale=px.colors.sequential.YlOrRd
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col2:
    st.subheader("Next Filming Timeslots")
    st.write("📅 Monday 10 AM — Worship Set")
    st.write("📅 Wednesday 2 PM — Testimony Recording")
    st.write("📅 Friday 4 PM — Youth Reels")

# Views bar chart
st.subheader("Views by Category (Last Week)")
fig_bar = px.bar(views_data, x="Category", y="Views",
                 color="Category",
                 color_discrete_map={
                     "Music Videos": "royalblue",
                     "Reels": "orange"
                 })
st.plotly_chart(fig_bar, use_container_width=True)

# Tasks with progress bars
st.subheader("Daily Tasks")

status_colors = {
    "Not Ready": "red",
    "In Progress": "yellow",
    "Done": "green"
}

for _, row in tasks_data.iterrows():
    color = status_colors[row.Status]
    st.markdown(f"""
        <div style='margin-bottom:10px;'>
            <strong>{row.Task}</strong>
            <div style='background-color:lightgray; border-radius:5px; height:20px; position:relative;'>
                <div style='background-color:{color}; width:{'100%' if row.Status=='Done' else '60%' if row.Status=='In Progress' else '20%'};
                            height:100%; border-radius:5px;'></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Social media icons row
st.markdown(
    f"""
    <div style='display:flex; justify-content:center; margin-top:40px;'>
        <div style='margin:0 15px;'>{svg_str('youtube.svg')}</div>
        <div style='margin:0 15px;'>{svg_str('instagram.svg')}</div>
        <div style='margin:0 15px;'>{svg_str('tiktok.svg')}</div>
    </div>
    """,
    unsafe_allow_html=True
)
