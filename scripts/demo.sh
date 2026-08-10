#!/bin/bash
# Live demo: rebuild the whole warehouse from scratch, end to end.
# Run from the drug-arrests-warehouse/ project root:
#   bash scripts/demo.sh   (activates venv automatically)
set -e
cd "$(dirname "$0")/.."

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# Fresh start: remove any existing database so the demo shows a full rebuild
rm -f drug_arrests_dw/drug_arrests_dw.duckdb*

echo ""
echo "════════════════════════════════════════════════════"
echo "  STEP 1/4 — BRONZE: land raw data from data.gov.my"
echo "════════════════════════════════════════════════════"
echo "\$ python drug_arrests_dw/scripts/ingest.py"
python drug_arrests_dw/scripts/ingest.py

echo ""
echo "════════════════════════════════════════════════════"
echo "  STEP 2/4 — SILVER + GOLD: run dbt transformations"
echo "════════════════════════════════════════════════════"
echo "\$ cd drug_arrests_dw && dbt run"
cd drug_arrests_dw
dbt run

echo ""
echo "════════════════════════════════════════════════════"
echo "  STEP 3/4 — Validate with dbt tests"
echo "════════════════════════════════════════════════════"
echo "\$ dbt test"
dbt test

echo ""
echo "════════════════════════════════════════════════════"
echo "  STEP 4/4 — Query the gold layer (star schema)"
echo "════════════════════════════════════════════════════"
cd ..
echo "\$ python -c \"import duckdb; ...\""
python -c "
import duckdb
con = duckdb.connect('drug_arrests_dw/drug_arrests_dw.duckdb')
print(con.sql('''
select
    f.age_group_key as age_group,
    sum(f.drug_arrest_count) as total_arrests
from main_gold.fact_drug_arrests f
where f.sex_key = 'both' and f.arrest_type_key = 'overall'
  and f.age_group_key not in ('all', 'no_information')
group by f.age_group_key
order by total_arrests desc
limit 7
''').fetchdf().to_markdown(index=False))"

echo ""
echo "✅ DEMO COMPLETE — bronze → silver → gold, end to end."
echo "   Next: dbt docs serve  (lineage graph in the browser)"
