-- Example queries against the gold layer (star schema).
-- Run: dbt compile  (or copy into DuckDB / dbt docs)

-- 1. National drug arrest trend by year (both sexes, all ages, overall type)
select
    f.arrest_date,
    f.drug_arrest_count as arrests
from {{ ref('fact_drug_arrests') }} f
where f.sex_key = 'both'
  and f.age_group_key = 'all'
  and f.arrest_type_key = 'overall'
order by f.arrest_date;

-- 2. Top age groups nationally (both sexes, overall type; excludes totals)
select
    a.age_group,
    sum(f.drug_arrest_count) as total_arrests
from {{ ref('fact_drug_arrests') }} f
join {{ ref('dim_age_group') }} a using (age_group_key)
where f.sex_key = 'both'
  and f.arrest_type_key = 'overall'
  and f.age_group_key not in ('all', 'no_information')
group by a.age_group
order by total_arrests desc;

-- 3. Male vs female nationally (all ages, overall type)
select
    s.sex,
    sum(f.drug_arrest_count) as total_arrests
from {{ ref('fact_drug_arrests') }} f
join {{ ref('dim_sex') }} s using (sex_key)
where f.age_group_key = 'all'
  and f.arrest_type_key = 'overall'
group by s.sex
order by total_arrests desc;

-- 4. By arrest type nationally (both sexes, all ages)
select
    t.arrest_type,
    sum(f.drug_arrest_count) as total_arrests
from {{ ref('fact_drug_arrests') }} f
join {{ ref('dim_arrest_type') }} t using (arrest_type_key)
where f.sex_key = 'both'
  and f.age_group_key = 'all'
group by t.arrest_type
order by total_arrests desc;

-- 5. Age profile for 2023, males (overall type)
select
    f.age_group_key as age_group,
    f.drug_arrest_count as arrests
from {{ ref('fact_drug_arrests') }} f
where f.arrest_date = '2023-01-01'
  and f.sex_key = 'male'
  and f.arrest_type_key = 'overall'
  and f.age_group_key != 'all'
order by f.drug_arrest_count desc;
