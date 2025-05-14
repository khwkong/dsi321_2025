# Project DSI321: Real-Time Data Pipeline with Visualization  
## Bangkok Air Quality Dashboard with Streamlit, Prefect & LakeFS

![Created at](https://img.shields.io/github/created-at/khwkong/dsi321_2025)
![Last Commit](https://img.shields.io/github/last-commit/khwkong/dsi321_2025)

### 🔎 Project Overview

This project is part of the **DSI321: Big Data Infrastructure** course. The course emphasizes applying modern data engineering tools to solve real-world problems through the development of end-to-end data pipelines.

This project focuses on **air quality monitoring in Bangkok**, with an emphasis on tracking **PM2.5** levels and the **Air Quality Index (AQI)** in near real-time. The system is designed to be automated, scalable, and reproducible—leveraging tools such as Prefect, Streamlit, LakeFS, and Docker to ingest, process, and visualize air quality data across various districts in Bangkok.

#### 🧩 Core Components

- **Real-Time Data Ingestion from LakeFS**  
  Air quality data (PM2.5 and AQI) is stored in a version-controlled Parquet format using LakeFS. This ensures reproducibility and complete tracking of data updates.

- **Scheduled Processing with Prefect**  
  A Prefect flow runs hourly to retrieve the latest data from LakeFS. This keeps the system continuously updated and maintains data freshness for visualization.

- **Interactive Visualization via Streamlit**  
  The dashboard features:
  - A color-coded interactive map showing AQI levels by district
  - Time-series charts for AQI trends over recent hours
  - A dropdown to select specific districts

- **Data Version Control with LakeFS**  
  LakeFS provides Git-like version control for data, enabling rollback, reproducibility, and auditability—crucial for time-sensitive environmental monitoring.

- **Reproducible Deployment with Docker**  
  All components (Streamlit, Prefect, LakeFS) are containerized for easy setup, consistent environments, and fast deployment.