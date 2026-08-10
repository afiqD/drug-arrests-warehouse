# Drug Arrests Data Warehouse — Drug Arrests by Sex & Age

A mini data warehouse built with a medallion architecture (bronze → silver → gold), using **dbt-core** for transformation and **DuckDB** as the embedded warehouse engine. All tools are 100% free and open-source.

**Dataset:** [Drug Arrests by Sex & Age](https://data.gov.my) (data.gov.my / OpenDOSM), catalogue ID `drug_arrests_age` — a national public dataset released by the Government of Malaysia.

> 📄 **[Technical Summary](drug-arrests-technicalsummary.html)** — full project flow, stack, step-by-step setup & usage, troubleshooting, and a reusable playbook to rebuild this pipeline for any dataset.

## Why this dataset

Drug arrest statistics are directly domain-adjacent to the mandate of SPRM/BPRM (integrity and anti-corruption enforcement): law-enforcement agencies depend on consistent, cleaned, queryable data on drug arrests — by age group and sex — for operational reporting, profiling and policy analysis. This project demonstrates exactly that workflow — from government open data to a tested analytics warehouse.

## Architecture

```
┌─────────────┐     ┌────────────────────────────┐     ┌──────────────────────────────────┐
│  BRONZE     │     │  SILVER                    │     │  GOLD (star schema)              │
│  raw data   │ ──► │  staging / cleaned         │ ──► │  dim_age_group (9 groups)        │
│  as-is      │     │  stg_drug_arrests_age      │     │  dim_sex (3 groupings)           │
│  (Open API) │     │  (cast types,              │     │  dim_arrest_type (4 types)       │
│             │     │   rename columns)          │     │  fact_drug_arrests               │
│             │     │                            │     │  (age_group_key, sex_key,        │
│             │     │                            │     │   arrest_type_key, date, count)  │
└─────────────┘     └────────────────────────────┘     └──────────────────────────────────┘
```

- **Bronze** (`scripts/ingest.py` → schema `bronze`): the raw API response is landed untouched. No transformation.
- **Silver** (`models/staging` → schema `silver`): staging view with only type casting and column renaming — no business logic.
- **Gold** (`models/marts` → schema `gold`): a proper star schema — three dimension tables and one fact table keyed by surrogate keys.

## Tech stack

| Layer | Tool |
|---|---|
| Data source | data.gov.my Open API (`data-catalogue?id=drug_arrests_age`, no auth needed) |
| Storage + compute | DuckDB |
| Transformation | dbt-core + dbt-duckdb |
| Version control | Git + GitHub |

## How to run

```bash
python3 -m venv venv && source venv/bin/activate
pip install dbt-core dbt-duckdb duckdb pandas flask

# 1. Bronze: land raw data
python drug_arrests_dw/scripts/ingest.py

# 2. Silver + Gold: build models
cd drug_arrests_dw
dbt run

# 3. Validate with data tests
dbt test

# 4. Generate and serve lineage docs
dbt docs generate
dbt docs serve

# 5. (Optional) Open the web UI to query and view the data
cd ..
python drug_arrests_dw/scripts/app.py   # then open http://localhost:5000
```

`dbt docs serve` opens a browser with an auto-generated lineage graph of the whole pipeline. The web UI (`scripts/app.py`) lets you run any SQL against the DuckDB warehouse and see the results in the browser — it opens pre-loaded with a live query showing the top age groups by arrests.

## Sample insights (real data, 2019–2023)

Queried from the gold layer (`fact_drug_arrests` + dimensions):

### National drug arrests by year (both sexes, all ages, overall type)

| Year | Arrests |
|---|---:|
| 2019 | 47,952 |
| 2020 | 46,895 |
| 2021 | 44,787 |
| 2022 | 163,697 (3.6× jump) |
| 2023 | 179,799 |

### Top age groups nationally (2019–2023)

| Age group | Total arrests |
|---|---:|
| 14–18 | 284,802 |
| >41 | 213,457 |
| 35–40 | 152,084 |
| 30–34 | 133,635 |
| 25–29 | 98,160 |
| 19–24 | 79,081 |
| <13 | 184 |

### Male vs female (national)

| Sex | Total arrests |
|---|---:|
| male | 331,079 |
| female | 152,051 |

Males account for roughly **2.2×** the female drug arrests nationally.

### By arrest type (national)

| Arrest type | Total arrests |
|---|---:|
| overall | 483,130 |
| urine_positive | 316,857 |
| posses | 270,144 |
| supply | 106,611 |

## Data quality caveat

- The dataset records **annual counts** (dated 1 January each year), 2019–2023.
- `sex = 'both'` is the total across sexes; `age = 'all'` is the total across age groups; `arrest_type = 'overall'` is the total across types. Analyses should filter appropriately to avoid double counting.
- `age = 'no_information'` holds arrests where the age was not recorded.
- The 2022–2023 figures are roughly 3.6× higher than 2019–2021 — likely a methodological or reporting change, not an actual arrest surge; worth noting before drawing conclusions.

## Repo layout

```
drug-arrests-warehouse/
├── drug_arrests_dw/                  # dbt project
│   ├── scripts/ingest.py             # bronze ingest
│   ├── models/
│   │   ├── staging/                  # silver layer
│   │   │   ├── stg_drug_arrests_age.sql
│   │   │   └── sources.yml
│   │   └── marts/                    # gold layer
│   │       ├── dim_age_group.sql
│   │       ├── dim_sex.sql
│   │       ├── dim_arrest_type.sql
│   │       ├── fact_drug_arrests.sql
│   │       └── schema.yml            # tests + docs
│   └── dbt_project.yml
├── scripts/demo.sh                   # one-command rebuild (interview demo)
└── venv/                             # not committed
```
