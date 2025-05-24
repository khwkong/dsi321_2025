import pandas as pd
import fsspec
import os
import re
from collections import defaultdict


def save_data():
    storage_options = {
        "key": "access_key",
        "secret": "secret_key",
        "client_kwargs": {
            "endpoint_url": "http://lakefs-dev:8000/"
        }
    }

    fs = fsspec.filesystem("s3", **storage_options)

    repo = "dust-concentration"
    branch = "main"
    base_path = f"{repo}/{branch}/pm_data.parquet"

    try:
        all_files = fs.glob(f"{base_path}/**/*.parquet")
        if not all_files:
            print("No Data in LakeFS")
            return

        # --- year/month/day/hour ---
        file_map = defaultdict(set)
        pattern = re.compile(r"year=(\d+)/month=(\d+)/day=(\d+)/hour=(\d+)/")

        for file in all_files:
            match = pattern.search(file)
            if match:
                key = (match.group(1), match.group(2), match.group(3))  # year, month, day
                hour = int(match.group(4))
                file_map[key].add(hour)

        # --- just day that have 24 hours ---
        valid_files = [
            file for file in all_files
            if pattern.search(file) and
               len(file_map[(pattern.search(file).group(1),
                             pattern.search(file).group(2),
                             pattern.search(file).group(3))]) == 24
        ]

        if not valid_files:
            print("Can't find, Day that have 24 hours.")
            return

        # --- schema setting ---
        columns_used = [
            "timestamp", "stationID", "nameTH", "areaTH", "district",
            "lat", "long", "AQI.aqi", "PM25.value", "year", "month", "day", "hour"
        ]

        for file in valid_files:
            file_path = f"s3a://{file}"
            df = pd.read_parquet(file_path, storage_options=storage_options)
            df = df[columns_used]

            # --- set path ---
            relative_path = file.replace(f"{repo}/{branch}/pm_data.parquet/", "")

            # --- local path ---
            local_path = os.path.join("/home/jovyan/data/data.parquet", relative_path)
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)

            df.to_parquet(local_path, index=False)
            print(f"💾 saved {local_path}")

        print("✅ ALL done !")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    save_data()