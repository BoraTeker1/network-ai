"""Job matching service (stub).

Ranks stored jobs against a saved user profile and produces JobMatch rows
with a score and human-readable reasons. Implemented later. No LLM calls yet.
"""


def rank_jobs(profile_id: int) -> list:
    """Score jobs for a profile and return ordered matches."""
    raise NotImplementedError("matcher.rank_jobs not implemented yet")
