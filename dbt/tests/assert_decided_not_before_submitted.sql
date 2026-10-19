-- Council registers sometimes contain impossible dates. Warn rather than fail, and list them:
-- these rows are the start of the quarantine table planned for Week 2.
{{ config(severity='warn') }}

select application_id, council, submitted_on, decided_on
from {{ ref('stg_planit__applications') }}
where decided_on < submitted_on
