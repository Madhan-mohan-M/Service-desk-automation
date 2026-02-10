"""
Configuration for Service Desk Automation.
For production, use environment variables instead of hardcoding.
"""
import os

# ============ Microsoft Graph API (O365) ============
# Register app at https://portal.azure.com > App registrations
GRAPH_CLIENT_ID = os.getenv('GRAPH_CLIENT_ID', '')
GRAPH_CLIENT_SECRET = os.getenv('GRAPH_CLIENT_SECRET', '')
GRAPH_TENANT_ID = os.getenv('GRAPH_TENANT_ID', '')
GRAPH_USER_EMAIL = os.getenv('GRAPH_USER_EMAIL', '')  # mailbox to monitor

# ============ SMTP Email Notifications ============
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.office365.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
NOTIFICATION_FROM = os.getenv('NOTIFICATION_FROM', 'servicedesk@example.com')

# ============ Automation Settings ============
POLL_INTERVAL_SECONDS = int(os.getenv('POLL_INTERVAL', '60'))  # how often to check emails
AUTO_PROCESS_ENABLED = os.getenv('AUTO_PROCESS', 'false').lower() == 'true'

# ============ SLA Settings (in hours) ============
SLA_RESPONSE_HOURS = {
    'High': 1,
    'Medium': 4,
    'Low': 24
}
SLA_RESOLUTION_HOURS = {
    'High': 4,
    'Medium': 24,
    'Low': 72
}

# ============ Team Assignment Rules ============
TEAM_ASSIGNMENTS = {
    'Access Issue': 'identity-team@example.com',
    'Infrastructure': 'infra-team@example.com',
    'Email': 'messaging-team@example.com',
    'Software': 'desktop-team@example.com',
    'Networking': 'network-team@example.com',
    'General': 'helpdesk@example.com'
}

# ============ Demo Mode ============
# When True, uses file-based email input instead of Graph API
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'
