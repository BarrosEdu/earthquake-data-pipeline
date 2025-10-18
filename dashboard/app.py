
import os
import time
import math
import requests
import pandas as pd
import streamlit as st
import pydeck as pdk

from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Earthquake Monitor (API-driven)", layout="wide")

# ------------------------
# Config
# ------------------------
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "https://earthquake-ce5c9a0f9ec7.herokuapp.com/")
st.sidebar.title("⚙️ Settings")
api_base = st.sidebar.text_input("API Base URL", value=DEFAULT_API_BASE, help=f"FastAPI base URL {DEFAULT_API_BASE}")

mode = st.sidebar.radio("Query Mode", ["Recent", "Around"])

layer_style = st.sidebar.selectbox(
    "Map layer style",
    ["Circles (recommended)", "3D columns"],
    index=0,
    help="Circles are easier to see"
)
highlight_biggest = st.sidebar.checkbox("Highlight biggest quake", value=True)
add_heatmap = st.sidebar.checkbox("Add heatmap overlay", value=False)

st.sidebar.markdown("---")
hours = st.sidebar.number_input("Hours window", min_value=1, max_value=168, value=24, step=1)
min_mag = st.sidebar.number_input("Min magnitude", min_value=0.0, max_value=10.0, value=0.0, step=0.1, format="%.1f")
limit = st.sidebar.number_input("Limit", min_value=1, max_value=500, value=200, step=10)

if mode == "Around":
    st.sidebar.markdown("---")
    st.sidebar.caption("Proximity filter (PostGIS via API)")
    lat = st.sidebar.number_input("Latitude", value=34.05, format="%.6f")
    lon = st.sidebar.number_input("Longitude", value=-118.25, format="%.6f")
    radius_km = st.sidebar.number_input("Radius (km)", min_value=1.0, max_value=1000.0, value=300.0, step=10.0, format="%.1f")

# ------------------------
# Helpers
# ------------------------
@st.cache_data(show_spinner=False, ttl=30)
def fetch_recent(api_base: str, hours: int, min_mag: float, limit: int):
    url = f"{api_base}/earthquakes/recent"
    params = dict(hours=hours, min_mag=min_mag, limit=limit)
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(show_spinner=False, ttl=30)
def fetch_around(api_base: str, lat: float, lon: float, radius_km: float, hours: int, min_mag: float, limit: int):
    url = f"{api_base}/earthquakes/around"
    params = dict(lat=lat, lon=lon, radius_km=radius_km, hours=hours, min_mag=min_mag, limit=limit)
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def to_dataframe(items):
    if not items:
        return pd.DataFrame(columns=["id","mag","place","time_utc","lat","lon","depth_km"])
    df = pd.DataFrame(items)
    for col in ["mag","lat","lon","depth_km"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "time_utc" in df.columns:
        df["time_utc"] = pd.to_datetime(df["time_utc"], errors="coerce", utc=True)
    return df

# ------------------------
# UI/UX
# ------------------------
st.title("🌎 Earthquake Monitor — API mode")

with st.expander("About this dashboard", expanded=False):
    st.write("""
    This Streamlit dashboard **does not connect to the database**.  
    It consumes the existing **FastAPI** endpoints:
    - `GET /earthquakes/recent`
    - `GET /earthquakes/around`
    """)
    st.code(f"export API_BASE_URL={DEFAULT_API_BASE}", language="bash")

# Fetch data
try:
    if mode == "Recent":
        data = fetch_recent(api_base, hours, min_mag, limit)
    else:
        data = fetch_around(api_base, lat, lon, radius_km, hours, min_mag, limit)
    df = to_dataframe(data)
    status_ok = True
    error_msg = ""
except Exception as e:
    df = to_dataframe([])
    status_ok = False
    error_msg = str(e)

# Metrics
left, right = st.columns([1,3])

with left:
    st.subheader("Summary")
    st.metric("Events", len(df))
    if len(df):
        st.metric("Avg Magnitude", f"{df['mag'].mean():.2f}")
        st.metric("Max Magnitude", f"{df['mag'].max():.2f}")
    if not status_ok:
        st.error(f"Failed to fetch data: {error_msg}")

with right:
    st.subheader("Map")
    if len(df) and {"lat","lon"}.issubset(df.columns):
        # center of map
        mean_lat = float(df["lat"].mean())
        mean_lon = float(df["lon"].mean())

        # compute sizes & colors
        
        df["_size_m"] = df["mag"].fillna(0).apply(lambda m: 25000 + (m * 40000))
        df["_elev"] = df["mag"].fillna(0).apply(lambda m: 500 + m * 1200)

        
        def color_from_mag(m):
            m = 0 if pd.isna(m) else float(m)
            if m < 2:   return [80, 160, 255]   
            if m < 4:   return [255, 200, 80]   
            if m < 6:   return [255, 140, 60]   
            return [255, 70, 70]                
        df["_color"] = df["mag"].apply(color_from_mag)

        # layers
        layers = []

        if layer_style == "Circles (recommended)":
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=df.rename(columns={"lat":"latitude","lon":"longitude"}),
                get_position='[longitude, latitude]',
                get_radius="_size_m",
                pickable=True,
                filled=True,
                get_fill_color="_color",
                stroked=True,
                get_line_color=[255, 255, 255],
                line_width_min_pixels=1,
                radius_min_pixels=4,   
                radius_max_pixels=60
            ))
        else:
            layers.append(pdk.Layer(
                "ColumnLayer",
                data=df.rename(columns={"lat":"latitude","lon":"longitude"}),
                get_position='[longitude, latitude]',
                get_elevation="_elev",
                elevation_scale=1,
                pickable=True,
                auto_highlight=True,
                get_fill_color="_color",
                radius=20000
            ))

        # highlight events
        if highlight_biggest and len(df):
            imax = df["mag"].idxmax()
            if pd.notna(imax):
                biggest = df.loc[[imax]].rename(columns={"lat":"latitude","lon":"longitude"}).copy()
                layers.append(pdk.Layer(
                    "ScatterplotLayer",
                    data=biggest,
                    get_position='[longitude, latitude]',
                    get_radius=biggest["_size_m"].iloc[0] * 1.4,
                    pickable=False,
                    filled=False,
                    stroked=True,
                    get_line_color=[255, 255, 0],  
                    line_width_min_pixels=3,
                    radius_min_pixels=10
                ))

        # heatmap 
        if add_heatmap and len(df):
            layers.append(pdk.Layer(
                "HeatmapLayer",
                data=df.rename(columns={"lat":"latitude","lon":"longitude"}),
                get_position='[longitude, latitude]',
                get_weight="mag",
                aggregation='MEAN'
            ))

        # view
        view_state = pdk.ViewState(latitude=mean_lat, longitude=mean_lon, zoom=2)

        tooltip = {
            "html": "<b>Mag:</b> {mag}<br/><b>Place:</b> {place}<br/><b>Time (UTC):</b> {time_utc}",
            "style": {"backgroundColor": "rgba(0,0,0,0.7)", "color": "white"}
        }

        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, tooltip=tooltip))
    else:
        st.info("No data to plot. Try widening the time window or lowering the min magnitude.")


st.subheader("Table")
st.dataframe(df, use_container_width=True)

st.caption("Data source: FastAPI service powered by PostgreSQL/PostGIS backend (queried via API only).")
