{{
    config(
        post_hook=[
            "create index if not exists {{ this.name }}_geom_bng_gix on {{ this }} using gist (geom_bng)"
        ]
    )
}}

-- Applications with an outcome flag, decision time, and a metric (British National Grid)
-- geometry so distance filters can use a spatial index.

select
    *,
    case
        when app_state in ('Permitted', 'Conditions') then true
        when app_state = 'Rejected' then false
    end                                         as is_approved,  -- null: withdrawn, undecided, other
    case
        when decided_on is not null then decided_on - submitted_on
    end                                         as decision_days,
    ST_Transform(geom, 27700)                   as geom_bng
from {{ ref('stg_planit__applications') }}
