with source as (
    select * from {{ source('bronze', 'drug_arrests_age_raw') }}
),

renamed as (
    select
        cast(date as date)          as arrest_date,
        age,
        sex,
        arrest_type,
        cast(drug_arrests as integer) as drug_arrest_count
    from source
    where drug_arrests is not null
)

select * from renamed
