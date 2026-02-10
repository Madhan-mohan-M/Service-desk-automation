from flask import Flask, render_template, jsonify, request, redirect, url_for
from email_processor import parse_email_line, classify_issue
from auto_resolver import resolve_status
import database
import os
import hashlib
import config

# Import new automation modules
from graph_client import fetch_o365_emails, graph_client
from notifications import notifier
from scheduler import automation_scheduler
from sla_tracker import run_sla_check, get_sla_summary, check_sla_status
from assignment import assign_ticket, process_assignment

app = Flask(__name__, template_folder='templates', static_folder='static')

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
EMAILS_FILE = os.path.join(DATA_DIR, 'emails.txt')
PROCESSED_FILE = os.path.join(DATA_DIR, 'processed_emails.txt')


def email_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@app.route('/')
def dashboard():
    stats = database.get_stats()
    sla_summary = get_sla_summary()
    return render_template('dashboard.html', stats=stats, sla=sla_summary)


@app.route('/tickets')
def tickets():
    tickets = database.list_tickets()
    # Add SLA status to each ticket
    for t in tickets:
        t['sla'] = check_sla_status(t)
    return render_template('tickets.html', tickets=tickets)


@app.route('/analytics')
def analytics():
    dist = database.get_distributions()
    sla_summary = get_sla_summary()
    return render_template('analytics.html', dist=dist, sla=sla_summary)


@app.route('/process')
def process_emails():
    """
    Process emails from file (demo mode) or O365 Graph API.
    Creates tickets with auto-assignment and notifications.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PROCESSED_FILE):
        open(PROCESSED_FILE, 'w', encoding='utf-8').close()

    processed_hashes = set(line.strip() for line in open(PROCESSED_FILE, encoding='utf-8') if line.strip())
    created = []
    source = 'file'

    # Try O365 Graph API if configured and not in demo mode
    if graph_client.is_configured() and not config.DEMO_MODE:
        source = 'o365'
        emails = fetch_o365_emails()
        for email in emails:
            msg_id = email.get('id', '')
            h = email_hash(msg_id)
            if h in processed_hashes:
                continue

            summary = (email.get('subject', '') + '\n' + email.get('body', '')).lower()
            category, priority = classify_issue(summary)
            assigned_to = config.TEAM_ASSIGNMENTS.get(category, '')

            ticket_id = database.create_ticket(
                sender=email.get('sender', 'unknown'),
                issue=email.get('subject', '(no subject)'),
                category=category,
                priority=priority,
                status='New',
                assigned_to=assigned_to,
                message_id=msg_id
            )

            new_status = resolve_status(priority)
            database.update_ticket_status(ticket_id, new_status)

            # Process assignment and send notifications
            ticket = database.get_ticket_by_id(ticket_id)
            if ticket:
                process_assignment(ticket)

            created.append({'id': ticket_id, 'status': new_status, 'category': category})

            # Mark email as processed
            with open(PROCESSED_FILE, 'a', encoding='utf-8') as pf:
                pf.write(h + '\n')

            # Mark as read in O365
            graph_client.mark_as_read(msg_id)

    else:
        # File-based processing (demo mode)
        if not os.path.exists(EMAILS_FILE):
            return jsonify({'processed': 0, 'created': 0, 'message': 'No emails.txt found', 'source': source}), 200

        for raw in open(EMAILS_FILE, encoding='utf-8'):
            raw = raw.strip()
            if not raw:
                continue
            h = email_hash(raw)
            if h in processed_hashes:
                continue

            email = parse_email_line(raw)
            summary = (email.get('subject', '') + '\n' + email.get('body', '')).lower()
            category, priority = classify_issue(summary)
            assigned_to = config.TEAM_ASSIGNMENTS.get(category, '')

            ticket_id = database.create_ticket(
                sender=email.get('sender', 'unknown'),
                issue=email.get('subject', '(no subject)'),
                category=category,
                priority=priority,
                status='New',
                assigned_to=assigned_to
            )

            new_status = resolve_status(priority)
            database.update_ticket_status(ticket_id, new_status)

            # Process assignment and send notifications
            ticket = database.get_ticket_by_id(ticket_id)
            if ticket:
                process_assignment(ticket)

            created.append({'id': ticket_id, 'status': new_status, 'category': category})

            with open(PROCESSED_FILE, 'a', encoding='utf-8') as pf:
                pf.write(h + '\n')

    return jsonify({'processed': 'complete', 'created': len(created), 'source': source, 'tickets': created})


# ============ NEW API ROUTES ============

@app.route('/api/status')
def api_status():
    """Health check and automation status."""
    return jsonify({
        'status': 'running',
        'demo_mode': config.DEMO_MODE,
        'o365_configured': graph_client.is_configured(),
        'smtp_configured': notifier.is_configured(),
        'auto_process_enabled': config.AUTO_PROCESS_ENABLED,
        'scheduler_jobs': automation_scheduler.get_jobs_status()
    })


@app.route('/api/sla')
def api_sla():
    """Get SLA summary."""
    return jsonify(get_sla_summary())


@app.route('/api/sla/check')
def api_sla_check():
    """Trigger SLA check manually."""
    result = run_sla_check()
    return jsonify(result)


@app.route('/api/tickets')
def api_tickets():
    """Get all tickets as JSON."""
    tickets = database.list_tickets()
    for t in tickets:
        t['sla'] = {
            'response_ok': check_sla_status(t)['response_ok'],
            'resolution_ok': check_sla_status(t)['resolution_ok'],
            'breached': check_sla_status(t)['breached']
        }
    return jsonify(tickets)


@app.route('/api/ticket/<int:ticket_id>')
def api_ticket_detail(ticket_id):
    """Get single ticket details."""
    ticket = database.get_ticket_by_id(ticket_id)
    if ticket:
        ticket['sla'] = check_sla_status(ticket)
        return jsonify(ticket)
    return jsonify({'error': 'Ticket not found'}), 404


@app.route('/api/ticket/<int:ticket_id>/resolve', methods=['GET', 'POST'])
def api_resolve_ticket(ticket_id):
    """Manually resolve a ticket."""
    ticket = database.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    database.update_ticket_status(ticket_id, 'Closed')
    ticket['status'] = 'Closed'
    notifier.send_ticket_resolved(ticket)
    
    # If GET request (from browser link), redirect back to tickets page
    if request.method == 'GET':
        return redirect(url_for('tickets'))
    return jsonify({'success': True, 'ticket_id': ticket_id, 'status': 'Closed'})


@app.route('/api/ticket/<int:ticket_id>/escalate', methods=['GET', 'POST'])
def api_escalate_ticket(ticket_id):
    """Escalate a ticket to high priority."""
    ticket = database.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    database.update_ticket_status(ticket_id, 'Escalated')
    database.update_ticket_priority(ticket_id, 'High')
    ticket['status'] = 'Escalated'
    ticket['priority'] = 'High'
    
    team_email = config.TEAM_ASSIGNMENTS.get(ticket['category'], 'helpdesk@example.com')
    notifier.send_ticket_escalated(ticket, team_email)
    
    if request.method == 'GET':
        return redirect(url_for('tickets'))
    return jsonify({'success': True, 'ticket_id': ticket_id, 'status': 'Escalated'})


@app.route('/api/ticket/<int:ticket_id>/reopen', methods=['GET', 'POST'])
def api_reopen_ticket(ticket_id):
    """Reopen a closed ticket."""
    ticket = database.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    database.update_ticket_status(ticket_id, 'Open')
    
    if request.method == 'GET':
        return redirect(url_for('tickets'))
    return jsonify({'success': True, 'ticket_id': ticket_id, 'status': 'Open'})


@app.route('/api/ticket/<int:ticket_id>/assign', methods=['POST'])
def api_assign_ticket(ticket_id):
    """Assign ticket to a team/person."""
    ticket = database.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json() or {}
    assigned_to = data.get('assigned_to', '')
    
    if assigned_to:
        database.update_ticket_assignment(ticket_id, assigned_to)
        return jsonify({'success': True, 'ticket_id': ticket_id, 'assigned_to': assigned_to})
    return jsonify({'error': 'assigned_to required'}), 400


@app.route('/api/tickets/filter')
def api_tickets_filter():
    """Filter tickets by status, priority, or category."""
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    category = request.args.get('category', '')
    
    tickets = database.list_tickets()
    
    if status:
        tickets = [t for t in tickets if t['status'].lower() == status.lower()]
    if priority:
        tickets = [t for t in tickets if t['priority'].lower() == priority.lower()]
    if category:
        tickets = [t for t in tickets if t['category'].lower() == category.lower()]
    
    for t in tickets:
        t['sla'] = check_sla_status(t)
    
    return jsonify({'count': len(tickets), 'tickets': tickets})


@app.route('/api/tickets/search')
def api_tickets_search():
    """Search tickets by keyword in issue or sender."""
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify({'error': 'Query parameter q required'}), 400
    
    tickets = database.list_tickets()
    results = [t for t in tickets if q in t['issue'].lower() or q in t['sender'].lower()]
    
    return jsonify({'query': q, 'count': len(results), 'tickets': results})


@app.route('/api/ticket/create', methods=['POST'])
def api_create_ticket():
    """Manually create a ticket via API."""
    data = request.get_json() or {}
    
    sender = data.get('sender', 'manual@example.com')
    issue = data.get('issue', '')
    category = data.get('category', 'General')
    priority = data.get('priority', 'Medium')
    
    if not issue:
        return jsonify({'error': 'issue field required'}), 400
    
    assigned_to = config.TEAM_ASSIGNMENTS.get(category, '')
    
    ticket_id = database.create_ticket(
        sender=sender,
        issue=issue,
        category=category,
        priority=priority,
        status='New',
        assigned_to=assigned_to
    )
    
    new_status = resolve_status(priority)
    database.update_ticket_status(ticket_id, new_status)
    
    ticket = database.get_ticket_by_id(ticket_id)
    if ticket:
        process_assignment(ticket)
    
    return jsonify({'success': True, 'ticket_id': ticket_id, 'status': new_status})


@app.route('/api/stats')
def api_stats():
    """Get dashboard statistics."""
    stats = database.get_stats()
    dist = database.get_distributions()
    sla = get_sla_summary()
    
    return jsonify({
        'tickets': stats,
        'distributions': dist,
        'sla': sla
    })


@app.route('/api/teams')
def api_teams():
    """Get team assignments configuration."""
    return jsonify(config.TEAM_ASSIGNMENTS)


@app.route('/api/reset-processed', methods=['POST'])
def api_reset_processed():
    """Clear processed emails list to reprocess all emails."""
    try:
        open(PROCESSED_FILE, 'w', encoding='utf-8').close()
        return jsonify({'success': True, 'message': 'Processed emails list cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/emails/add', methods=['POST'])
def api_add_email():
    """Add a simulated email to emails.txt for testing."""
    data = request.get_json() or {}
    
    sender = data.get('sender', 'test@example.com')
    subject = data.get('subject', '')
    body = data.get('body', '')
    
    if not subject:
        return jsonify({'error': 'subject required'}), 400
    
    line = f"{sender}|{subject}|{body}\n"
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(EMAILS_FILE, 'a', encoding='utf-8') as f:
        f.write(line)
    
    return jsonify({'success': True, 'message': 'Email added', 'email': {'sender': sender, 'subject': subject, 'body': body}})


# ============ WEB PAGES ============

@app.route('/ticket/<int:ticket_id>')
def ticket_detail(ticket_id):
    """Ticket detail page."""
    ticket = database.get_ticket_by_id(ticket_id)
    if not ticket:
        return "Ticket not found", 404
    ticket['sla'] = check_sla_status(ticket)
    return render_template('ticket_detail.html', ticket=ticket)


@app.route('/settings')
def settings():
    """Settings and configuration page."""
    return render_template('settings.html', 
                           config=config,
                           teams=config.TEAM_ASSIGNMENTS,
                           sla_response=config.SLA_RESPONSE_HOURS,
                           sla_resolution=config.SLA_RESOLUTION_HOURS)


@app.route('/new-ticket')
def new_ticket_page():
    """Page to create a new ticket manually."""
    return render_template('new_ticket.html', teams=config.TEAM_ASSIGNMENTS)


if __name__ == '__main__':
    database.init_db()
    # Start background scheduler for automatic processing
    automation_scheduler.start(process_func=process_emails, sla_check_func=run_sla_check)
    app.run(debug=True, port=5000)
