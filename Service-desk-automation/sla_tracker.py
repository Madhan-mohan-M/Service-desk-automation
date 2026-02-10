"""
SLA (Service Level Agreement) tracking for tickets.
Monitors response and resolution times, sends warnings on breach.
"""
from datetime import datetime, timedelta
from typing import List, Dict
import database
import config
from notifications import notifier


def calculate_sla_due(priority: str, created_at: str) -> Dict[str, str]:
    """Calculate SLA due times based on priority."""
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    except:
        created = datetime.utcnow()
    
    response_hours = config.SLA_RESPONSE_HOURS.get(priority, 24)
    resolution_hours = config.SLA_RESOLUTION_HOURS.get(priority, 72)
    
    return {
        'response_due': (created + timedelta(hours=response_hours)).isoformat(),
        'resolution_due': (created + timedelta(hours=resolution_hours)).isoformat()
    }


def check_sla_status(ticket: dict) -> Dict[str, any]:
    """
    Check SLA status for a ticket.
    Returns: {'response_ok': bool, 'resolution_ok': bool, 'time_to_breach': timedelta}
    """
    now = datetime.utcnow()
    priority = ticket.get('priority', 'Medium')
    created_at = ticket.get('created_at', now.isoformat())
    
    sla = calculate_sla_due(priority, created_at)
    
    try:
        response_due = datetime.fromisoformat(sla['response_due'].replace('Z', '+00:00'))
        resolution_due = datetime.fromisoformat(sla['resolution_due'].replace('Z', '+00:00'))
    except:
        response_due = now + timedelta(hours=24)
        resolution_due = now + timedelta(hours=72)
    
    status = ticket.get('status', 'Open')
    is_closed = status in ('Closed', 'Resolved')
    
    response_ok = is_closed or now < response_due
    resolution_ok = is_closed or now < resolution_due
    
    time_to_breach = resolution_due - now if not is_closed else timedelta(days=999)
    
    return {
        'response_ok': response_ok,
        'resolution_ok': resolution_ok,
        'response_due': sla['response_due'],
        'resolution_due': sla['resolution_due'],
        'time_to_breach': time_to_breach,
        'breached': not resolution_ok
    }


def get_tickets_near_breach(threshold_minutes: int = 30) -> List[dict]:
    """Find tickets that will breach SLA within the threshold."""
    tickets = database.list_tickets()
    at_risk = []
    
    for ticket in tickets:
        if ticket['status'] in ('Closed', 'Resolved'):
            continue
        
        sla_status = check_sla_status(ticket)
        if sla_status['time_to_breach'] < timedelta(minutes=threshold_minutes):
            ticket['sla_status'] = sla_status
            at_risk.append(ticket)
    
    return at_risk


def get_breached_tickets() -> List[dict]:
    """Find tickets that have already breached SLA."""
    tickets = database.list_tickets()
    breached = []
    
    for ticket in tickets:
        if ticket['status'] in ('Closed', 'Resolved'):
            continue
        
        sla_status = check_sla_status(ticket)
        if sla_status['breached']:
            ticket['sla_status'] = sla_status
            breached.append(ticket)
    
    return breached


def run_sla_check():
    """
    Scheduled job to check all open tickets for SLA status.
    Sends notifications for at-risk and breached tickets.
    """
    print("[SLA Check] Running SLA compliance check...")
    
    # Check tickets near breach (within 30 minutes)
    at_risk = get_tickets_near_breach(threshold_minutes=30)
    for ticket in at_risk:
        team_email = config.TEAM_ASSIGNMENTS.get(ticket['category'], 'helpdesk@example.com')
        notifier.send_sla_breach_warning(ticket, team_email)
        print(f"[SLA Warning] Ticket #{ticket['id']} approaching breach")
    
    # Check already breached
    breached = get_breached_tickets()
    for ticket in breached:
        print(f"[SLA BREACH] Ticket #{ticket['id']} has breached SLA!")
    
    print(f"[SLA Check] Complete. At-risk: {len(at_risk)}, Breached: {len(breached)}")
    return {'at_risk': len(at_risk), 'breached': len(breached)}


def get_sla_summary() -> Dict:
    """Get overall SLA compliance metrics."""
    tickets = database.list_tickets()
    
    total = len(tickets)
    compliant = 0
    breached = 0
    at_risk = 0
    
    for ticket in tickets:
        sla_status = check_sla_status(ticket)
        if sla_status['breached']:
            breached += 1
        elif sla_status['time_to_breach'] < timedelta(hours=1):
            at_risk += 1
        else:
            compliant += 1
    
    compliance_rate = (compliant / total * 100) if total > 0 else 100
    
    return {
        'total': total,
        'compliant': compliant,
        'at_risk': at_risk,
        'breached': breached,
        'compliance_rate': round(compliance_rate, 1)
    }
