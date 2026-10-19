-- Every (application, comparable) pair that was knowable when the application was submitted.
-- The point-in-time rule lives here: a comparable must be DECIDED BEFORE the application was
-- SUBMITTED. tests/assert_comparables_point_in_time.sql checks it on every build.

select
    target.application_id,
    target.submitted_on,
    comp.application_id                                  as comparable_id,
    comp.decided_on                                      as comparable_decided_on,
    comp.is_approved                                     as comparable_is_approved,
    ST_Distance(target.geom_bng, comp.geom_bng)          as distance_m
from {{ ref('fct_applications') }} as target
inner join {{ ref('fct_applications') }} as comp
    on comp.decided_on < target.submitted_on
    and comp.is_approved is not null
    and comp.application_id <> target.application_id
    and ST_DWithin(target.geom_bng, comp.geom_bng, {{ var('comparable_radius_m') }})
