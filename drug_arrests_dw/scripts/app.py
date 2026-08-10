"""Local web UI to query the DuckDB warehouse and view data.

Run:  python scripts/app.py   ->  http://localhost:5000
"""
import json
import os
import re

import duckdb
from flask import Flask, jsonify, render_template_string, request

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "drug_arrests_dw.duckdb")

app = Flask(__name__)

EXAMPLE_QUERIES = [
    {"name": "Bronze - raw sample", "sql": "select * from bronze.drug_arrests_age_raw limit 10"},
    {"name": "Silver - cleaned sample", "sql": "select * from main_silver.stg_drug_arrests_age limit 10"},
    {"name": "Gold - fact sample", "sql": "select * from main_gold.fact_drug_arrests limit 10"},
    {"name": "National trend by year", "sql": """
select f.arrest_date, f.drug_arrest_count as arrests
from main_gold.fact_drug_arrests f
where f.sex_key = 'both' and f.age_group_key = 'all' and f.arrest_type_key = 'overall'
order by f.arrest_date"""},
    {"name": "Top age groups (national)", "sql": """
select a.age_group, sum(f.drug_arrest_count) as total_arrests
from main_gold.fact_drug_arrests f
join main_gold.dim_age_group a using (age_group_key)
where f.sex_key = 'both' and f.arrest_type_key = 'overall'
  and f.age_group_key not in ('all', 'no_information')
group by a.age_group order by total_arrests desc"""},
    {"name": "Male vs female (national)", "sql": """
select f.sex_key as sex, sum(f.drug_arrest_count) as total_arrests
from main_gold.fact_drug_arrests f
where f.age_group_key = 'all' and f.arrest_type_key = 'overall'
group by f.sex_key order by total_arrests desc"""},
    {"name": "By arrest type (national)", "sql": """
select t.arrest_type, sum(f.drug_arrest_count) as total_arrests
from main_gold.fact_drug_arrests f
join main_gold.dim_arrest_type t using (arrest_type_key)
where f.sex_key = 'both' and f.age_group_key = 'all'
group by t.arrest_type order by total_arrests desc"""},
    {"name": "Age profile 2023 (male)", "sql": """
select f.age_group_key as age_group, f.drug_arrest_count as arrests
from main_gold.fact_drug_arrests f
where f.arrest_date = '2023-01-01' and f.sex_key = 'male' and f.arrest_type_key = 'overall'
  and f.age_group_key != 'all'
order by f.drug_arrest_count desc"""},
]

PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Drug Arrests Warehouse - DuckDB Query</title>
<style>
  body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
  .header { padding: 18px 24px; background: #1e293b; border-bottom: 1px solid #334155; }
  .header h1 { margin: 0; font-size: 20px; }
  .header p { margin: 4px 0 0; color: #94a3b8; font-size: 13px; }
  .wrap { padding: 20px 24px; display: flex; gap: 16px; align-items: flex-start; }
  .col-left { flex: 0 0 300px; }
  .col-right { flex: 1; min-width: 0; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px; margin-bottom: 16px; }
  .card h2 { margin: 0 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: .05em; color: #7dd3fc; }
  .chip { display: block; width: 100%; text-align: left; background: #0f172a; color: #cbd5e1; border: 1px solid #334155;
          border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 13px; cursor: pointer; }
  .chip:hover { border-color: #38bdf8; color: #e0f2fe; }
  textarea { width: 100%; box-sizing: border-box; min-height: 130px; background: #0f172a; color: #a5f3fc;
             border: 1px solid #334155; border-radius: 8px; padding: 12px; font-family: "SF Mono", Menlo, monospace;
             font-size: 13px; resize: vertical; }
  .btn { background: #0ea5e9; color: #0c1a2a; border: none; border-radius: 8px; padding: 10px 22px;
         font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 10px; }
  .btn:hover { background: #38bdf8; }
  .status { font-size: 12px; color: #94a3b8; margin-top: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  th { background: #334155; color: #e2e8f0; text-align: left; padding: 8px 10px; position: sticky; top: 0; }
  td { padding: 6px 10px; border-top: 1px solid #1e293b; font-family: Menlo, monospace; }
  tr:nth-child(even) { background: #16223a; }
  .tablebox { max-height: 60vh; overflow: auto; border-radius: 8px; border: 1px solid #334155; }
  .err { color: #fda4af; font-family: Menlo, monospace; font-size: 12.5px; white-space: pre-wrap; }
  a { color: #7dd3fc; }
</style>
</head>
<body>
<div class="header">
  <h1>Drug Arrests Warehouse &mdash; DuckDB + dbt</h1>
  <p>Query the gold/silver/bronze layers directly. dbt Jinja is supported: {% raw %}<code>{{ source('bronze', 'drug_arrests_age_raw') }}</code> and <code>{{ ref('fact_drug_arrests') }}</code>{% endraw %}.</p>
</div>
<div class="wrap">
  <div class="col-left">
    <div class="card">
      <h2>Custom query</h2>
      <textarea id="custom" placeholder="select * from bronze.drug_arrests_age_raw limit 5" style="min-height:90px"></textarea>
      <button class="btn" style="width:100%;margin-top:8px" onclick="runCustom()">Run custom query</button>
    </div>
    <div class="card">
      <h2>Example queries</h2>
      <div id="examples"></div>
    </div>
    <div class="card">
      <h2>Tables</h2>
      <div id="tables"></div>
    </div>
  </div>
  <div class="col-right">
    <div class="card">
      <h2>SQL</h2>
      <textarea id="sql">{{ default_sql }}</textarea>
      <button class="btn" onclick="run()">Run query</button>
      <div class="status" id="status"></div>
    </div>
    <div class="card">
      <h2>Result</h2>
      <div class="tablebox" id="result"></div>
    </div>
  </div>
</div>
<script>
window.addEventListener('load', run);
const examples = {{ examples | tojson }};
const exBox = document.getElementById('examples');
examples.forEach(e => {
  const b = document.createElement('button');
  b.className = 'chip';
  b.textContent = e.name;
  b.onclick = () => { document.getElementById('sql').value = e.sql; run(); };
  exBox.appendChild(b);
});

function fmt(v) {
  if (v === null || v === undefined) return '<i style="color:#64748b">NULL</i>';
  if (typeof v === 'number') return v.toLocaleString();
  return String(v).replace(/</g, '&lt;');
}

async function runCustom() {
  const sql = document.getElementById('custom').value.trim();
  if (!sql) {
    const out = document.getElementById('result');
    out.innerHTML = '<div class="err">Type a query first.</div>';
    return;
  }
  document.getElementById('sql').value = sql;
  await run();
}

async function run() {
  const sql = document.getElementById('sql').value.trim();
  const out = document.getElementById('result');
  const status = document.getElementById('status');
  if (!sql) return;
  status.textContent = 'Running...';
  out.innerHTML = '';
  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql })
    });
    const data = await res.json();
    if (data.error) {
      out.innerHTML = '<div class="err">' + fmt(data.error) + '</div>';
      status.textContent = 'Error';
      return;
    }
    const cols = data.columns;
    const rows = data.rows;
    let html = '<table><thead><tr>' + cols.map(c => '<th>' + fmt(c) + '</th>').join('') + '</tr></thead><tbody>';
    html += rows.map(r => '<tr>' + r.map(c => '<td>' + fmt(c) + '</td>').join('') + '</tr>').join('');
    html += '</tbody></table>';
    out.innerHTML = html;
    status.textContent = data.rows.length + ' rows returned in ' + data.ms + ' ms';
  } catch (e) {
    out.innerHTML = '<div class="err">' + fmt(e.message) + '</div>';
    status.textContent = 'Request failed';
  }
}

async function listTables() {
  const res = await fetch('/api/tables');
  const data = await res.json();
  document.getElementById('tables').innerHTML = data.tables
    .map(t => '<div class="chip" style="cursor:default;opacity:.85">' + fmt(t) + '</div>').join('');
}

listTables();
</script>
</body>
</html>
"""

DEFAULT_SQL = """
select a.age_group, sum(f.drug_arrest_count) as total_arrests
from main_gold.fact_drug_arrests f
join main_gold.dim_age_group a using (age_group_key)
where f.sex_key = 'both' and f.arrest_type_key = 'overall'
  and f.age_group_key not in ('all', 'no_information')
group by a.age_group
order by total_arrests desc
limit 7
"""


def get_con():
    return duckdb.connect(DB_PATH, read_only=True)


@app.route("/")
def index():
    return render_template_string(PAGE, examples=EXAMPLE_QUERIES, default_sql=DEFAULT_SQL)


@app.route("/api/tables")
def api_tables():
    con = get_con()
    try:
        rows = con.sql(
            "select table_schema, table_name from information_schema.tables "
            "where table_schema in ('bronze', 'main_silver', 'main_gold') order by 1, 2"
        ).fetchall()
        tables = [f"{s}.{t}" for s, t in rows]
    finally:
        con.close()
    return jsonify(tables=tables)


def render_jinja_lite(sql):
    """Translate the dbt Jinja used in this project into plain DuckDB SQL."""
    sql = re.sub(
        r"\{\{\s*source\(\s*['\"]([\w.]+)['\"]\s*,\s*['\"]([\w.]+)['\"]\s*\)\s*\}\}",
        r"\1.\2",
        sql,
    )
    ref_map = {
        "stg_drug_arrests_age": "main_silver.stg_drug_arrests_age",
        "dim_age_group": "main_gold.dim_age_group",
        "dim_sex": "main_gold.dim_sex",
        "dim_arrest_type": "main_gold.dim_arrest_type",
        "fact_drug_arrests": "main_gold.fact_drug_arrests",
    }
    sql = re.sub(
        r"\{\{\s*ref\(\s*['\"]([\w.]+)['\"]\s*\)\s*\}\}",
        lambda m: ref_map.get(m.group(1), m.group(1)),
        sql,
    )
    sql = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", sql, flags=re.DOTALL)
    return sql


@app.route("/api/query", methods=["POST"])
def api_query():
    sql = request.get_json().get("sql", "").strip()
    if not sql:
        return jsonify(error="Empty query")
    sql = render_jinja_lite(sql)
    if not sql.lower().lstrip().startswith(("select", "with", "show", "describe", "pragma", "explain")):
        return jsonify(error="Read-only mode: only SELECT/WITH/SHOW/DESCRIBE queries are allowed")
    con = get_con()
    try:
        df = con.sql(sql).fetchdf()
        payload = json.loads(df.to_json(orient="split", date_format="iso"))
        return jsonify(columns=payload["columns"], rows=payload["data"], ms=0, error=None)
    except Exception as e:  # noqa: BLE001
        return jsonify(error=str(e))
    finally:
        con.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
