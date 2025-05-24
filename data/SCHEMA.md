# 📄 Dataset Schema: Bangkok Air Quality Data

This document defines the expected schema and data quality rules for the Bangkok Air Quality dataset used in this project.

## #️⃣ Expected Columns and Data Types

| Column        | Data Type | Description                         |
|:--------------|:----------|:------------------------------------|
| `timestamp`   | datetime  | Timestamp of the measurement        |
| `stationID`   | string    | Unique station identifier           |
| `nameTH`      | string    | Station name in Thai                |
| `areaTH`      | string    | Area name in Thai                   |
| `district`    | string    | District name                       |
| `lat`         | float     | Latitude of the station             |
| `long`        | float     | Longitude of the station            |
| `AQI.aqi`     | int       | Air Quality Index (AQI)             |
| `PM25.value`  | float     | PM2.5 concentration in µg/m³        |
| `year`        | int       | Year of the record                  |
| `month`       | int       | Month of the record                 |
| `day`         | int       | Day of the record                   |
| `hour`        | int       | Hour of the record (0–23)           |

## ⚙️ Data Quality Rules

- **Schema Compliance**: All columns above must be present with correct data types.
- **Minimum Records**: At least **1,000 records** must be available in the dataset.
- **Hourly Coverage**: For each `year/month/day`, all **24 hours** must be present.
- **Completeness**: All columns must have **≥ 90% non-null values**.
- **No Object Columns**: Dataset must not contain columns of type `object`.
- **No Duplicates**: No fully duplicated rows allowed.

## 🔢 Valid Value Ranges

- `hour`: Integer between `0` and `23`
- `AQI.aqi`: int ≥ `0`
- `PM25.value`: Float ≥ `0`
- `lat`: Valid latitude between `-90` and `90`
- `long`: Valid longitude between `-180` and `180`

## 📂 Example Folder Structure

<pre>
data/
└── data.parquet/
    └── year=2025/
        └── month=05/
            └── day=24/
                ├── hour=00/
                ├── hour=01/
                └── ...
</pre>

- Example file path: `data/data.parquet/year=2025/month=05/day=24/hour=10/xxxxx.parquet`

## ✍🏻 Notes

- All `.parquet` files must follow the partition structure: `year=YYYY/month=MM/day=DD/hour=HH/`
- Naming and data types must remain consistent for downstream processing (e.g., ARIMA forecast, visualization)