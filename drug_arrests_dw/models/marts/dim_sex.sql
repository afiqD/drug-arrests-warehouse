with stg as (
    select * from {{ ref('stg_drug_arrests_age') }}
)

select distinct
    sex as sex_key,
    sex
from stg
order by sex
