"""Bronze layer: land the raw dataset as-is, untouched.

Fetches from the data.gov.my Open API with retries, and caches the raw
response locally so the pipeline still works if the API is rate-limited.
"""
import json
import os
import time
import urllib.request

import duckdb

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "drug_arrests_dw.duckdb")
API_URL = "https://api.data.gov.my/data-catalogue/?id=drug_arrests_age&sort=-date"
CACHE_PATH = os.path.join(PROJECT_DIR, "scripts", ".drug_arrests_age_cache.json")


def fetch_json(url, retries=3, backoff=2.0):
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_error = e
            time.sleep(backoff * (attempt + 1))
    raise last_error


def load_data():
    if os.path.exists(CACHE_PATH):
        print("Using cached API response")
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    rows = fetch_json(API_URL)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f)
    return rows


def main():
    rows = load_data()
    if not os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f)
    con = duckdb.connect(DB_PATH)
    con.sql(f"""
        CREATE SCHEMA IF NOT EXISTS bronze;
        CREATE OR REPLACE TABLE bronze.drug_arrests_age_raw AS
        SELECT * FROM read_json_auto('{CACHE_PATH}');
    """)

    count = con.sql("SELECT COUNT(*) FROM bronze.drug_arrests_age_raw").fetchone()[0]
    columns = [c[0] for c in con.sql("DESCRIBE bronze.drug_arrests_age_raw").fetchall()]
    print(f"Loaded {count} rows into bronze.drug_arrests_age_raw")
    print(f"Columns: {columns}")


if __name__ == "__main__":
    main()
