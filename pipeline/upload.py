import re
from pathlib import Path
import fsspec
from datetime import datetime


def upload_latest_data():
    # --- CONFIG ---
    local_base = Path("/home/jovyan/data/data.parquet")
    repo = "dust-concentration"
    branch = "main"
    lakefs_prefix = f"{repo}/{branch}/pm_data.parquet"

    storage_options = {
        "key": "access_key",
        "secret": "secret_key",
        "client_kwargs": {
            "endpoint_url": "http://lakefs-dev:8000/"
        }
    }

    fs = fsspec.filesystem("s3", **storage_options)

    # --- FIND LATEST DATE IN LOCAL ---
    def extract_date(p: Path):
        m = re.search(r"year=(\d+)/month=(\d+)/day=(\d+)", str(p))
        if m:
            return datetime(int(m[1]), int(m[2]), int(m[3]))
        return None

    all_day_dirs = [
        p for p in local_base.glob("year=*/month=*/day=*") 
        if p.is_dir() and extract_date(p) is not None
    ]

    if not all_day_dirs:
        print("❌ No local data found.")
        return

    latest_dir = max(all_day_dirs, key=extract_date)
    print(f"📁 Latest date directory: {latest_dir}")

    # --- REMOVE EXISTING FILES IN THAT PARTITION ---
    lakefs_partition_dir = f"{lakefs_prefix}/{latest_dir.relative_to(local_base).as_posix()}"
    if fs.exists(lakefs_partition_dir):
        print(f"🧹 Removing old files in: lakefs://{lakefs_partition_dir}")
        fs.rm(lakefs_partition_dir, recursive=True)

    # --- UPLOAD FILES ---
    uploaded = 0
    for parquet_file in latest_dir.rglob("*.parquet"):
        rel_path = parquet_file.relative_to(local_base)
        lakefs_path = f"{lakefs_prefix}/{rel_path.as_posix()}"

        fs.put(str(parquet_file), lakefs_path)
        print(f"✅ Uploaded: {parquet_file.name} → lakefs://{lakefs_path}")
        uploaded += 1

    if uploaded == 0:
        print("⚠️ No parquet files found in the latest date directory.")
    else:
        print(f"🎉 Upload complete. {uploaded} files uploaded.")


if __name__ == "__main__":
    upload_latest_data()