with stg as (
    select * from {{ ref('stg_drug_arrests_age') }}
)

select distinct
    age as age_group_key,
    age as age_group
from stg
order by age_group
