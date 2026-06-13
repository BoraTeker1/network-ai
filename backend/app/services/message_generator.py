"""Message generation service (stub).

Generates LinkedIn connection-request and follow-up drafts, plus contact
search suggestions (LinkedIn/Google search links — no scraping, no automation).
Every draft requires manual user approval. Implemented later.
"""


def generate_contact_search_links(job: dict) -> dict:
    """Build LinkedIn/Google search URLs to find relevant contacts."""
    raise NotImplementedError("message_generator.generate_contact_search_links not implemented yet")


def generate_message_draft(job: dict, profile: dict, message_type: str) -> str:
    """Draft a connection request or follow-up message for review."""
    raise NotImplementedError("message_generator.generate_message_draft not implemented yet")
