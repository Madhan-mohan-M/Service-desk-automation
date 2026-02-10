"""
Auto-assignment engine for routing tickets to appropriate teams.
Uses category-based rules from config.
"""
import config
from notifications import notifier


def assign_ticket(ticket: dict) -> str:
    """
    Determine the assigned team/person based on ticket category.
    Returns the assigned email address.
    """
    category = ticket.get('category', 'General')
    assigned_to = config.TEAM_ASSIGNMENTS.get(category, config.TEAM_ASSIGNMENTS.get('General', 'helpdesk@example.com'))
    return assigned_to


def process_assignment(ticket: dict) -> dict:
    """
    Full assignment workflow:
    1. Determine assigned team
    2. Send notification to requester
    3. If escalated, notify the team
    """
    assigned_to = assign_ticket(ticket)
    ticket['assigned_to'] = assigned_to
    
    # Send confirmation to the person who submitted the ticket
    notifier.send_ticket_created(ticket)
    
    # If auto-resolved, send resolution notice
    if ticket.get('status') == 'Closed':
        notifier.send_ticket_resolved(ticket)
    
    # If escalated (High priority), notify the assigned team
    elif ticket.get('status') == 'Escalated':
        notifier.send_ticket_escalated(ticket, assigned_to)
    
    return ticket


def get_team_workload() -> dict:
    """Get count of open tickets per team (for load balancing)."""
    import database
    tickets = database.list_tickets()
    
    workload = {}
    for team in config.TEAM_ASSIGNMENTS.values():
        workload[team] = 0
    
    for ticket in tickets:
        if ticket.get('status') not in ('Closed', 'Resolved'):
            assigned = ticket.get('assigned_to', '')
            if assigned in workload:
                workload[assigned] += 1
    
    return workload
