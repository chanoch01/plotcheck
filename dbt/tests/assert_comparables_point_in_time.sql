-- Fails if any comparable was decided on or after the day its application was submitted.
select *
from {{ ref('int_comparable_pairs') }}
where comparable_decided_on >= submitted_on
