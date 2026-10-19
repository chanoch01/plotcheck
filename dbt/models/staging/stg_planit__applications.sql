-- One clean row per application: renamed, typed, and located.
-- Field meanings: https://www.planit.org.uk/dictionary/

with source as (
    select * from {{ source('planit', 'planit_applications') }}
)

select
    name                                    as application_id,
    uid                                     as council_reference,
    area_name                               as council,
    address,
    postcode,
    description,
    app_type,
    app_state,
    app_size,
    cast(start_date as date)                as submitted_on,
    cast(decided_date as date)              as decided_on,
    cast(consulted_date as date)            as consultation_ends_on,
    other_fields__decision                  as decision_text,
    other_fields__status                    as status_text,
    other_fields__ward_name                 as ward,
    location_x                              as longitude,
    location_y                              as latitude,
    case
        when location_x is not null and location_y is not null
            then ST_SetSRID(ST_MakePoint(location_x, location_y), 4326)
    end                                     as geom,
    link                                    as planit_url,
    url                                     as council_url,
    cast(last_different as timestamp)       as source_changed_at,
    cast(last_scraped as timestamp)         as source_checked_at,
    cast(_fetched_at as timestamp)          as fetched_at,
    _source_query                           as source_query,
    _dlt_load_id                            as load_id
from source
