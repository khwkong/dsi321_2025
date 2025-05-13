import streamlit as st
import pandas as pd
import time
import fsspec
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
from st_aggrid import GridOptionsBuilder, AgGrid
from streamlit_autorefresh import st_autorefresh


# ---------- Streamlit config ----------
st.set_page_config(layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit&display=swap');
        html, body, div, p, label, input, textarea, button, h1, h2, h3, h4, h5, h6, span {
            font-family: 'Kanit', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

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

# ---------- Get latest date path ----------
def get_latest_date_path():
    paths = fs.glob(f"{base_path}/year=*/month=*/day=*")
    if not paths:
        return None

    def extract_date(p):
        parts = p.split("/")
        y = int(parts[-3].split("=")[1])
        m = int(parts[-2].split("=")[1])
        d = int(parts[-1].split("=")[1])
        return datetime(y, m, d)

    latest_date_path = max(paths, key=extract_date)
    return latest_date_path

# ---------- Load all hourly data for latest date ----------
@st.cache_data(ttl=60)
def load_latest_day_data(max_retries=5):
    now = datetime.now()
    date_path = get_latest_date_path()
    if not date_path:
        return pd.DataFrame(), now

    hour_paths = fs.glob(f"{date_path}/hour=*")
    if not hour_paths:
        return pd.DataFrame(), now

    expected_files = len(hour_paths)
    attempt = 0
    while attempt < max_retries:
        dfs = []
        for p in hour_paths:
            try:
                df_part = pd.read_parquet(f"s3a://{p}", storage_options=storage_options)
                dfs.append(df_part)
            except Exception:
                pass

        if len(dfs) == expected_files:
            break 
        else:
            attempt += 1
            if attempt < max_retries:
                time.sleep(3)

    if len(dfs) != expected_files:
        st.warning("⚠️ ข้อมูลยังมาไม่ครบ โหลดได้แค่บางส่วน")
        raise ValueError("ไม่สามารถโหลดข้อมูลครบทุกไฟล์")

    df = pd.concat(dfs, ignore_index=True)
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    return df, now

# ---------- AQI level helper ----------
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

# ---------- Load and display ----------
df, cache_time = load_latest_day_data()

st.subheader("รายงานคุณภาพอากาศภายในกรุงเทพมหานคร")
thai_time = cache_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Bangkok"))
st.caption(f"🕑ข้อมูลล่าสุดเมื่อ: {thai_time.strftime('%d/%m/%Y %H:%M:%S')}")

if df.empty:
    st.error("ไม่พบข้อมูลในวันที่ล่าสุด")
else:
    latest_time = df['timestamp'].max()
    latest_hour = latest_time.hour
    df_latest = df[df['timestamp'].dt.hour == latest_hour].copy()

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

    # ---------- Dashboard ----------
    st.subheader("Dashboard")
    st.markdown("###### ค่าเฉลี่ยคุณภาพอากาศภายในกรุงเทพฯ")

    daily_mean_aqi = df["AQI.aqi"].mean()
    daily_mean_pm25 = df["PM25.value"].mean()
    level, color = get_aqi_level_and_color(daily_mean_aqi)

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        st.markdown(f"""
            <div style="
                background-color:{color};
                padding: 1rem 2rem;
                border-radius: 12px;
                text-align: center;
                color: white;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            ">
                <div style="font-size: 1.1rem;">ค่าเฉลี่ย AQI</div>
                <div style="font-size: 1.5rem; font-weight: bold;">AQI {daily_mean_aqi:.0f} - {level}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="
                background-color:#1338BE;
                padding: 1rem 2rem;
                border-radius: 12px;
                text-align: center;
                color: white;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            ">
                <div style="font-size: 1.1rem;">ค่าเฉลี่ย PM2.5</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{daily_mean_pm25:.1f} µg/m³</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        pass

    # ---------- Map and AQI Chart ----------
    st.markdown("")
    st.markdown("")

    custom_scale = [
        (0, "#00E400"), (50, "#FFFF00"), (100, "#FF7E00"),
        (150, "#FF0000"), (200, "#8F3F97"), (300, "#7E0023")
    ]
    scale_values = [x[0] for x in custom_scale]
    scale_colors = [x[1] for x in custom_scale]
    norm_scale = [(v / max(scale_values), c) for v, c in zip(scale_values, scale_colors)]

    col_map, col_chart = st.columns([1.55, 1.45])

    mapbox_style = "carto-positron"

    with col_map:
        st.markdown("###### แผนที่คุณภาพอากาศ")
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
            center={"lat": 13.77, "lon": 100.6027},
            height=500
        )
        fig.update_layout(
            mapbox_style=mapbox_style,
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                title="AQI",
                tickvals=[0, 50, 100, 150, 200, 300],
                ticktext=["Good", "Moderate", "Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"],
            ),
            font=dict(family="Kanit", size=12)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_chart:
        st.markdown("###### 5 สถานที่ในกรุงเทพฯที่มีค่า AQI สูงที่สุด (today)")
        top5 = df_latest.nlargest(5, "AQI.aqi")["nameTH"].unique()
        df_top5 = df[df["nameTH"].isin(top5)].copy()
        df_top5["hour"] = df_top5["timestamp"].dt.hour
        df_top5["hour_str"] = df_top5["hour"].apply(lambda x: f"{x:02d}:00")

        fig_top5 = px.line(
            df_top5,
            x="hour_str",
            y="AQI.aqi",
            color="nameTH",
            markers=True,
            labels={"hour_str": "เวลา", "AQI.aqi": "ค่า AQI", "nameTH": "ชื่อสถานที่"},
        )
        fig_top5.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=40, b=80),  
            legend=dict(
                orientation="h",        
                yanchor="bottom",
                y=-1.1,                
                xanchor="center",
                x=0.5
            ),
            font=dict(family="Kanit", size=12)         
        )
        st.plotly_chart(fig_top5, use_container_width=True)

    # ---------- Latest hour table ----------
    st.subheader("ข้อมูลทั้งหมด (ชั่วโมงล่าสุด)")

    df_latest_display = df_latest[["timestamp", "nameTH", "district", "AQI.aqi", "PM25.value"]]

    # GridOptions
    gb = GridOptionsBuilder.from_dataframe(df_latest_display)
    gridOptions = gb.build()

    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Kanit&display=swap');
            .ag-theme-streamlit {
                font-family: 'Kanit', sans-serif;
                font-size: 16px;
            }
        </style>
    """, unsafe_allow_html=True)

    AgGrid(df_latest_display, gridOptions=gridOptions, theme="streamlit", fit_columns_on_grid_load=True)