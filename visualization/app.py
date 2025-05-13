import streamlit as st
import pandas as pd
import fsspec
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------- Streamlit config ----------
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit&display=swap');
        html, body, div, p, label, input, textarea, button, h1, h2, h3, h4, h5, h6, span {
            font-family: 'Kanit', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

st.subheader("รายงานคุณภาพอากาศภายในกรุงเทพมหานคร")
st_autorefresh(interval=60000, key="refresh") 

# ---------- lakeFS config ----------
ACCESS_KEY = "access_key"
SECRET_KEY = "secret_key"
lakefs_endpoint = "http://lakefs-dev:8000/"
repo = "dust-concentration"
branch = "main"
base_path = f"{repo}/{branch}/pm_data.parquet"

storage_options = {
    "key": ACCESS_KEY,
    "secret": SECRET_KEY,
    "client_kwargs": {
        "endpoint_url": lakefs_endpoint
    }
}

fs = fsspec.filesystem("s3", **storage_options)

# ---------- Get latest partition path ----------
def get_latest_partition_path():
    paths = fs.glob(f"{base_path}/year=*/month=*/day=*/hour=*")
    if not paths:
        return None

    def extract_datetime(p):
        parts = p.split("/")
        y = int(parts[-4].split("=")[1])
        m = int(parts[-3].split("=")[1])
        d = int(parts[-2].split("=")[1])
        h = int(parts[-1].split("=")[1])
        return datetime(y, m, d, h)

    latest_path = max(paths, key=extract_datetime)
    return f"s3a://{latest_path}"

# ---------- Load latest data ----------
@st.cache_data(ttl=1800) 
def load_latest_data():
    latest_path = get_latest_partition_path()
    if latest_path is None:
        return pd.DataFrame()

    try:
        df = pd.read_parquet(latest_path, storage_options=storage_options)
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถโหลดไฟล์: {e}")
        return pd.DataFrame()

    required_columns = {'lat', 'long', 'timestamp'}
    if not required_columns.issubset(df.columns):
        st.warning("⚠️ ข้อมูลล่าสุดยังไม่ครบหรือยังเขียนไม่เสร็จ")
        return pd.DataFrame()

    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df

# ---------- Load and filter data ----------
df = load_latest_data()
if df.empty:
    st.error("ไม่พบข้อมูลในพาร์ทิชันล่าสุด")
else:
    latest_time = df['timestamp'].max()
    df_latest = df[df['timestamp'] == latest_time]

    def get_aqi_level_and_color(aqi):
        if aqi <= 50:
            return "Good", "#00E400"
        elif aqi <= 100:
            return "Moderate", "#FFFF00"
        elif aqi <= 150:
            return "Sensitive", "#FF7E00"
        elif aqi <= 200:
            return "Unhealthy", "#FF0000"
        elif aqi <= 300:
            return "Very Unhealthy", "#8F3F97"
        else:
            return "Hazardous", "#7E0023"

    df_latest["AQI_level"], df_latest["AQI_color"] = zip(*df_latest["AQI.aqi"].apply(get_aqi_level_and_color))
    df_latest['search_key'] = df_latest['nameTH'] + " (" + df_latest['district'] + ")"
    search_list = sorted(df_latest['search_key'].unique())
    default_location = "สำนักงานเขตคลองเตย (คลองเตย)"
    selected_search = st.selectbox("ค้นหาสถานที่หรือเขต", search_list, index=search_list.index(default_location))

    df_filtered = df_latest[df_latest['search_key'] == selected_search]

    if df_filtered.empty:
        st.warning("❌ ไม่พบข้อมูลสำหรับพื้นที่ที่เลือก")
    else:
        record = df_filtered.iloc[0]
        aqi = record['AQI.aqi']
        pm25 = record['PM25.value']
        name = record['nameTH']
        district = record['district']
        aqi_level = record["AQI_level"]
        aqi_color = record["AQI_color"]

        st.markdown(f"""
            <div style="text-align: center; font-size: 27px; font-weight: 600; margin-bottom: 1rem;">
                {name} ({district})
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="
                background-color: {aqi_color};
                padding: 1rem 2rem;
                border-radius: 12px;
                text-align: center;
                width: fit-content;
                margin: 0 auto 2rem auto;
                color: white;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            ">
                <div style="font-size: 1.5rem; font-weight: bold;">
                    AQI {aqi} - {aqi_level}
                </div>
                <div style="font-size: 1.2rem;">
                    PM2.5 - {pm25} µg/m³
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("แผนที่คุณภาพอากาศ")

        custom_scale = [
            (0, "#00E400"),
            (50, "#FFFF00"),
            (100, "#FF7E00"),
            (150, "#FF0000"),
            (200, "#8F3F97"),
            (300, "#7E0023"),
        ]
        scale_values = [x[0] for x in custom_scale]
        scale_colors = [x[1] for x in custom_scale]
        norm_scale = [(v / max(scale_values), c) for v, c in zip(scale_values, scale_colors)]

        fig = px.scatter_mapbox(
            df_latest,
            lat="lat",
            lon="long",
            hover_name="nameTH",
            hover_data=["AQI.aqi", "AQI_level", "PM25.value", "district"],
            color="AQI.aqi",
            color_continuous_scale=norm_scale,
            range_color=[0, 300],
            size="AQI.aqi",
            size_max=18,
            zoom=9,
            center={"lat": 13.75, "lon": 100.52},
            height=550
        )
        fig.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                title="AQI",
                tickvals=[0, 50, 100, 150, 200, 300],
                ticktext=["Good", "Moderate", "Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"]
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("ข้อมูลทั้งหมด")
        df_with_timestamp_index = df_latest[["timestamp", "nameTH", "district", "AQI.aqi", "PM25.value"]].set_index("timestamp")
        st.dataframe(df_with_timestamp_index, use_container_width=True)
        st.caption(f"ข้อมูลล่าสุดเมื่อ: {latest_time}")