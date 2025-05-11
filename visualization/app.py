import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
import plotly.express as px

# ---------- config ----------
ACCESS_KEY = "access_key"
SECRET_KEY = "secret_key"
lakefs_endpoint = "http://lakefs-dev:8000/"

repo = "dust-concentration"
branch = "main"
path = "pm_data.parquet"

lakefs_s3_path = f"s3a://{repo}/{branch}/{path}"

storage_options = {
    "key": ACCESS_KEY,
    "secret": SECRET_KEY,
    "client_kwargs": {
        "endpoint_url": lakefs_endpoint
    }
}

# ---------- load data ----------
@st.cache_data
def load_data():
    df = pd.read_parquet(lakefs_s3_path, storage_options=storage_options)
    
    # lat lon convert
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
   
    # 'timestamp' to datetime object (find latest data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    return df

df = load_data()

# ---------- latest data ----------
latest_time = df['timestamp'].max()
df_latest = df[df['timestamp'] == latest_time]

st.subheader(f"🕐 ข้อมูลล่าสุด: {latest_time}")

# ---------- color map ----------
aqi_color_map = {
    1: "#00E400",  # good
    2: "#FFFF00",  # moderate
    3: "#FF7E00",  # unhealthy for sensitive groups
    4: "#FF0000",  # unhealthy
    5: "#8F3F97",  # very unhealthy
    6: "#7E0023",  # hazardous
}

df_latest['aqi_color'] = df_latest['AQI.color_id'].map(aqi_color_map)

# ---------- map plot ----------
fig = px.scatter_mapbox(
    df_latest,
    lat="lat",
    lon="long",
    hover_name="nameTH",
    hover_data=["AQI.aqi", "PM25.value", "district"],
    color="AQI.aqi",
    color_continuous_scale="RdYlGn_r",
    size_max=15,
    zoom=10,
    height=600
)

fig.update_layout(mapbox_style="carto-positron")
st.plotly_chart(fig, use_container_width=True)

# ---------- table ----------
st.subheader("📊 ตารางข้อมูล")
st.dataframe(
    df_latest[["timestamp", "nameTH", "district", "AQI.aqi", "PM25.value"]],
    use_container_width=True
)