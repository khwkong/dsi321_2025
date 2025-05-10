import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pathlib import Path
from prefect import flow, task


@task
def fetch_data() -> list[dict]:
    try:
        url = 'http://air4thai.pcd.go.th/services/getNewAQI_JSON.php'
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        return data['stations']
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


@task
def data_processing(data: list[dict], districts_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    df = pd.DataFrame(data)

    # check
    if 'AQILast' not in df.columns:
        print("❌ 'AQILast' column not found in the data. Skipping this run.")
        return pd.DataFrame()

    # check
    if df['AQILast'].dropna().empty:
        print("❌ 'AQILast' column is empty. Skipping this run.")
        return pd.DataFrame()

    print("Sample AQILast:")
    print(df['AQILast'].dropna().iloc[0])

    # Flatten AQILast
    aqi_data = pd.json_normalize(df['AQILast'])
    df = pd.concat([df, aqi_data], axis=1)

    pollutant_cols = [
        'AQI.aqi', 'AQI.color_id',
        'PM25.value', 'PM25.color_id',
        'PM10.value', 'PM10.color_id',
        'O3.value', 'NO2.value', 'CO.value'
    ]

    for col in pollutant_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            print(f"⚠️ Warning: Column '{col}' not found in DataFrame")

    if 'time' in df.columns and 'date' in df.columns:
        df['time'] = df['time'].mode()[0]
        df['date'] = df['date'].mode()[0]
        df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    else:
        print("❌ Missing 'time' or 'date' columns.")
        return pd.DataFrame()

    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df['day'] = df['timestamp'].dt.day
    df['hour'] = df['timestamp'].dt.hour

    # geometry and spatial join
    stations_gdf = gpd.GeoDataFrame(
        df,
        geometry=df.apply(lambda r: Point(r['long'], r['lat']), axis=1),
        crs='epsg:4326'
    )

    joined = gpd.sjoin(
        stations_gdf,
        districts_gdf[['dname', 'geometry']],
        how='left',
        predicate='within'
    )

    # del --เขต
    df['district'] = joined['dname'].str.replace("เขต", "", regex=False).str.strip()
    df = df[df['district'].notna()]

    # sort
    selected_cols = [
        'timestamp', 'year', 'month', 'day', 'hour',
        'stationID', 'nameTH', 'areaTH', 'district', 'lat', 'long'
    ] + pollutant_cols

    return df[selected_cols]


@task
def load_to_lakefs(df: pd.DataFrame, lakefs_s3_path: str, storage_options: dict):
    print(f"Saving to: {lakefs_s3_path}")
    print(f"Storage options: {storage_options}")

    df['timestamp'] = df['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')

    df.insert(0, 'index', range(1, len(df) + 1))

    df.to_parquet(
        lakefs_s3_path,
        storage_options=storage_options,
        partition_cols=['year', 'month', 'day', 'hour'],
        index=False
    )

    print("✅ Done saving to lakeFS.")


@flow(name='dust-concentration-pipeline', log_prints=True)
def main_flow():
    try:
        geojson_path = Path("/home/jovyan/work/bangkok_districts.geojson")
        print(f"🔍 Loading GeoJSON from: {geojson_path}")
        districts_gdf = gpd.read_file(geojson_path)

        if districts_gdf.crs is None:
            districts_gdf.set_crs(epsg=4326, inplace=True)
        else:
            districts_gdf = districts_gdf.to_crs(epsg=4326)
    except Exception as e:
        print(f"❌ Failed to load GeoJSON: {e}")
        return

    try:
        data = fetch_data()

        if not data:
            print("❌ No data fetched.")
            return

        df = data_processing(data, districts_gdf)

        if df.empty:
            print("❌ Processed DataFrame is empty. Skipping load.")
            return

        print(df.head())

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

        load_to_lakefs(df, lakefs_s3_path, storage_options)
    except Exception as e:
        print(f"❌ Flow failed: {e}")
        return  


if __name__ == "__main__":
    main_flow()