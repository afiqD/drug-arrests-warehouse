with stg as (
    select * from {{ ref('stg_drug_arrests_age') }}
)

select
    age                          as age_group_key,
    sex                          as sex_key,
    arrest_type                  as arrest_type_key,
    arrest_date,
    drug_arrest_count
from stg
