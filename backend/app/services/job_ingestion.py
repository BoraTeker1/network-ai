"""Job ingestion service (stub).

Pulls roles from the SimplifyJobs/New-Grad-Positions GitHub README,
parses them, and stores deduplicated jobs in SQLite. Implemented later.
"""


def ingest_jobs() -> dict:
    """Fetch + parse + dedupe jobs. Returns counts of ingested/skipped."""
    raise NotImplementedError("job_ingestion.ingest_jobs not implemented yet")
