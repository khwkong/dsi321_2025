#import fsspec
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from prefect import flow, task
from statsmodels.tsa.arima.model import ARIMA


# ---- Config ----
FORECAST_HOURS = 6

OUTLIER_STATIONS = ['สำนักงานเขตบางคอแหลม (Mobile)', 'การเคหะชุมชนห้วยขวาง ']

LAKEFS_PATH_IN = "s3a://dust-concentration/main/pm_data.parquet"
LAKEFS_PATH_OUT = "s3a://dust-concentration/main/forecast/forecast.parquet"

STORAGE_OPTIONS = {
    "key": "access_key",
    "secret": "secret_key",
    "client_kwargs": {"endpoint_url": "http://lakefs-dev:8000/"}
}


@task
def read_lakefs_data() -> pd.DataFrame:
    print(f"📥 Loading data from: {LAKEFS_PATH_IN}")
    return pd.read_parquet(LAKEFS_PATH_IN, storage_options=STORAGE_OPTIONS)


@task
def forecast_pm25_aqi(df: pd.DataFrame) -> pd.DataFrame:
    print(f"🔎 Forecasting PM2.5 and AQI for all stations...")

    df = df[~df['nameTH'].isin(OUTLIER_STATIONS)]
    df = df[['timestamp', 'nameTH', 'PM25.value', 'AQI.aqi']].dropna()
    df['load_time'] = datetime.now()

    forecasts = []

    for station in df['nameTH'].unique():
        station_df = df[df['nameTH'] == station].sort_values(['timestamp', 'load_time'])
        station_df = station_df.drop_duplicates(subset="timestamp", keep="last")

        if station_df.shape[0] < 24:
            print(f"⚠️ Skipping {station}: not enough data")
            continue

        station_df = station_df.set_index("timestamp").asfreq('h')

        try:
            pm_model = ARIMA(station_df["PM25.value"], order=(1, 0, 1))
            pm_fit = pm_model.fit()
            pm_forecast = pm_fit.forecast(steps=FORECAST_HOURS)

            aqi_model = ARIMA(station_df["AQI.aqi"], order=(1, 0, 1))
            aqi_fit = aqi_model.fit()
            aqi_forecast = aqi_fit.forecast(steps=FORECAST_HOURS)

        except Exception as e:
            print(f"❌ Forecast failed for {station}: {e}")
            continue

        forecast_times = [station_df.index[-1] + timedelta(hours=i + 1) for i in range(FORECAST_HOURS)]
        result = pd.DataFrame({
            'timestamp': forecast_times,
            'nameTH': station,
            'AQI_forecast': np.round(aqi_forecast.values).astype(int),
            'PM25_forecast': pm_forecast.values,
        })

        forecasts.append(result)

    if forecasts:
        forecast_df = pd.concat(forecasts).reset_index(drop=True)
        forecast_df['nameTH'] = forecast_df['nameTH'].astype('string')
        forecast_df.insert(0, 'index', range(1, len(forecast_df) + 1))
        forecast_df = forecast_df[['index', 'timestamp', 'nameTH', 'AQI_forecast', 'PM25_forecast']]
    else:
        forecast_df = pd.DataFrame(columns=['index', 'timestamp', 'nameTH', 'AQI_forecast', 'PM25_forecast'])

    return forecast_df


#@task
#def delete_old_forecast():
#    fs = fsspec.filesystem('s3', **STORAGE_OPTIONS)
#    if fs.exists(LAKEFS_PATH_OUT):
#        print(f"🧹 Deleting old forecast at: {LAKEFS_PATH_OUT}")
#        fs.rm(LAKEFS_PATH_OUT, recursive=True)


@task
def save_to_lakefs(df: pd.DataFrame):
    print(f"💾 Saving forecast to: {LAKEFS_PATH_OUT}")
    df.to_parquet(
        LAKEFS_PATH_OUT,
        storage_options=STORAGE_OPTIONS,
        index=False
    )


@flow(name="forecast-aqi-and-pm25", log_prints=True)
def forecast_both_pipeline():
    df = read_lakefs_data()
    forecast_df = forecast_pm25_aqi(df)
    #delete_old_forecast()
    save_to_lakefs(forecast_df)


if __name__ == "__main__":
    forecast_both_pipeline()