-- One row per application with leakage-safe neighbourhood features for the model (Week 4).

select
    app.application_id,
    app.council,
    app.submitted_on,
    app.is_approved,
    count(pairs.comparable_id)                         as n_prior_decided_nearby,
    avg(pairs.comparable_is_approved::int)             as prior_approval_rate_nearby,
    min(pairs.distance_m)                              as nearest_prior_m
from {{ ref('fct_applications') }} as app
left join {{ ref('int_comparable_pairs') }} as pairs
    on pairs.application_id = app.application_id
group by 1, 2, 3, 4
