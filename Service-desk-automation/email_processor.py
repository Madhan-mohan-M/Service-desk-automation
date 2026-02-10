"""Rule-based email classification for Service Desk MVP."""
from typing import Tuple

KEYWORD_MAP = [
    (['password', 'reset', 'unlock'], ('Access Issue', 'Low')),
    (['vpn', 'connect', 'cannot connect', 'network'], ('Networking', 'Medium')),
    (['server down', 'down', 'outage', 'unreachable'], ('Infrastructure', 'High')),
    (['email', 'outlook', 'send', 'receive'], ('Email', 'Medium')),
    (['install', 'software', 'upgrade'], ('Software', 'Low')),
]


def parse_email_line(line: str) -> dict:
    """
    Expected line format: sender|subject|body
    Simple fallbacks are used if parts are missing.
    """
    parts = line.split('|')
    sender = parts[0].strip() if len(parts) > 0 else 'unknown'
    subject = parts[1].strip() if len(parts) > 1 else ''
    body = parts[2].strip() if len(parts) > 2 else ''
    return {'sender': sender, 'subject': subject, 'body': body}


def classify_issue(text: str) -> Tuple[str, str]:
    """Return (category, priority) based on simple keyword rules."""
    t = text.lower()
    for keywords, (cat, prio) in KEYWORD_MAP:
        for k in keywords:
            if k in t:
                return cat, prio
    return 'General', 'Medium'
