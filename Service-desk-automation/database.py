"""SQLite helpers for tickets."""
import sqlite3
import os
import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'service_desk.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        issue TEXT,
        category TEXT,
        priority TEXT,
        status TEXT,
        assigned_to TEXT,
        message_id TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    # Migration: add new columns if they don't exist
    try:
        cur.execute('ALTER TABLE tickets ADD COLUMN assigned_to TEXT')
    except:
        pass
    try:
        cur.execute('ALTER TABLE tickets ADD COLUMN message_id TEXT')
    except:
        pass
    try:
        cur.execute('ALTER TABLE tickets ADD COLUMN updated_at TEXT')
    except:
        pass
    conn.commit()
    conn.close()


def create_ticket(sender, issue, category, priority, status='New', assigned_to='', message_id=''):
    conn = get_conn()
    cur = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cur.execute('''INSERT INTO tickets (sender, issue, category, priority, status, assigned_to, message_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (sender, issue, category, priority, status, assigned_to, message_id, created_at, created_at))
    conn.commit()
    ticket_id = cur.lastrowid
    conn.close()
    return ticket_id


def update_ticket_assignment(ticket_id, assigned_to):
    conn = get_conn()
    cur = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    cur.execute('UPDATE tickets SET assigned_to = ?, updated_at = ? WHERE id = ?', (assigned_to, updated_at, ticket_id))
    conn.commit()
    conn.close()


def get_ticket_by_id(ticket_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_ticket_status(ticket_id, status):
    conn = get_conn()
    cur = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    cur.execute('UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?', (status, updated_at, ticket_id))
    conn.commit()
    conn.close()


def update_ticket_priority(ticket_id, priority):
    conn = get_conn()
    cur = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    cur.execute('UPDATE tickets SET priority = ?, updated_at = ? WHERE id = ?', (priority, updated_at, ticket_id))
    conn.commit()
    conn.close()


def list_tickets():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tickets ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM tickets')
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tickets WHERE status!='Closed'")
    open_tickets = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Closed'")
    closed = cur.fetchone()[0]
    conn.close()
    return {'total': total, 'open': open_tickets, 'resolved': closed}


def get_distributions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT priority, COUNT(*) as cnt FROM tickets GROUP BY priority')
    pri = {r[0]: r[1] for r in cur.fetchall()}
    cur.execute('SELECT category, COUNT(*) as cnt FROM tickets GROUP BY category')
    cat = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()
    return {'priority': pri, 'category': cat}
