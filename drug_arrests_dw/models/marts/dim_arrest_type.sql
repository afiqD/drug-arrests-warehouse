with stg as (
    select * from {{ ref('stg_drug_arrests_age') }}
)

select distinct
    arrest_type as arrest_type_key,
    arrest_type
from stg
order by arrest_type
