"""Simple auto-resolution engine for tickets based on priority."""

def resolve_status(priority: str) -> str:
    p = (priority or '').lower()
    if p == 'low':
        return 'Closed'
    if p == 'medium':
        return 'Open'
    if p == 'high':
        return 'Escalated'
    return 'Open'
