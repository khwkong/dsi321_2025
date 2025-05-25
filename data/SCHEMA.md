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

## ⚙️ Data Quality Rules

- **Schema Compliance**: All columns above must be present with correct data types.
- **Minimum Records**: At least **1,000 records** must be available in the dataset.
- **Hourly Coverage**: Each calendar day (inferred from `timestamp`) must include **24 hourly records** (hours 0–23).
- **Completeness**: All columns must have **≥ 90% non-null values**.
- **No Object Columns**: Dataset must not contain columns of type `object`.
- **No Duplicates**: No fully duplicated rows allowed.

## 🔢 Valid Value Ranges

- `AQI.aqi`: int ≥ `0`
- `PM25.value`: float ≥ `0`
- `lat`: valid latitude between `-90` and `90`
- `long`: valid longitude between `-180` and `180`

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
- `timestamp` will be parsed to extract time-based features as needed (e.g., for completeness checks).
- Naming and data types must remain consistent for downstream processing (e.g., ARIMA forecast, visualization)