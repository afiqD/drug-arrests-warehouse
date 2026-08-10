"""View the actual data in each layer. Run:  python scripts/view_data.py"""
import os

import duckdb

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "drug_arrests_dw.duckdb")

con = duckdb.connect(DB_PATH)

def show(title, sql):
    print(f"\n=== {title} ===")
    print(con.sql(sql).fetchdf().to_markdown(index=False))

show("BRONZE — raw (5 sample rows)", """
    select * from bronze.drug_arrests_age_raw limit 5
""")

show("SILVER — cleaned staging (5 sample rows)", """
    select * from main_silver.stg_drug_arrests_age limit 5
""")

show("GOLD — fact_drug_arrests (5 sample rows)", """
    select * from main_gold.fact_drug_arrests limit 5
""")

show("GOLD — dim_age_group (count)", """
    select count(*) as age_groups from main_gold.dim_age_group
""")

show("GOLD — dim_sex (count)", """
    select count(*) as sexes from main_gold.dim_sex
""")

show("GOLD — dim_arrest_type (count)", """
    select count(*) as arrest_types from main_gold.dim_arrest_type
""")

show("Top age groups by total arrests (national, both sexes, overall)", """
    select f.age_group_key, sum(f.drug_arrest_count) as total_arrests
    from main_gold.fact_drug_arrests f
    where f.sex_key = 'both' and f.arrest_type_key = 'overall'
      and f.age_group_key not in ('all', 'no_information')
    group by f.age_group_key
    order by total_arrests desc
    limit 7
""")
