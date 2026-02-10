"""
Email notification service for sending ticket updates.
Supports SMTP (O365, Gmail, etc.) for sending confirmations and alerts.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import config


class NotificationService:
    """Send email notifications for ticket events."""
    
    def __init__(self):
        self.server = config.SMTP_SERVER
        self.port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.from_addr = config.NOTIFICATION_FROM
    
    def is_configured(self) -> bool:
        return all([self.server, self.username, self.password])
    
    def send_email(self, to: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        """Send an email notification."""
        if not self.is_configured():
            print("[Notification] SMTP not configured, skipping email")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_addr
            msg['To'] = to
            
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            msg.attach(MIMEText(body_html, 'html'))
            
            with smtplib.SMTP(self.server, self.port) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.send_message(msg)
            
            print(f"[Notification] Email sent to {to}")
            return True
        except Exception as e:
            print(f"[Notification Error] {e}")
            return False
    
    def send_ticket_created(self, ticket: dict) -> bool:
        """Send confirmation when a ticket is created."""
        subject = f"Ticket #{ticket['id']} Created: {ticket['issue']}"
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Your Service Desk Ticket Has Been Created</h2>
            <table style="border-collapse: collapse;">
                <tr><td><strong>Ticket ID:</strong></td><td>#{ticket['id']}</td></tr>
                <tr><td><strong>Issue:</strong></td><td>{ticket['issue']}</td></tr>
                <tr><td><strong>Category:</strong></td><td>{ticket['category']}</td></tr>
                <tr><td><strong>Priority:</strong></td><td>{ticket['priority']}</td></tr>
                <tr><td><strong>Status:</strong></td><td>{ticket['status']}</td></tr>
            </table>
            <p>We will respond within the SLA timeframe for {ticket['priority']} priority tickets.</p>
            <p>Thank you,<br>IT Service Desk</p>
        </body>
        </html>
        """
        return self.send_email(ticket['sender'], subject, body_html)
    
    def send_ticket_resolved(self, ticket: dict) -> bool:
        """Send notification when a ticket is auto-resolved."""
        subject = f"Ticket #{ticket['id']} Resolved"
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Your Ticket Has Been Resolved</h2>
            <p>Ticket <strong>#{ticket['id']}</strong> regarding "<em>{ticket['issue']}</em>" 
            has been automatically resolved.</p>
            <p>If you still need assistance, please reply to this email or submit a new request.</p>
            <p>Thank you,<br>IT Service Desk</p>
        </body>
        </html>
        """
        return self.send_email(ticket['sender'], subject, body_html)
    
    def send_ticket_escalated(self, ticket: dict, team_email: str) -> bool:
        """Notify the assigned team about an escalated ticket."""
        subject = f"[ESCALATED] Ticket #{ticket['id']}: {ticket['issue']}"
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">High Priority Ticket Escalated</h2>
            <table style="border-collapse: collapse;">
                <tr><td><strong>Ticket ID:</strong></td><td>#{ticket['id']}</td></tr>
                <tr><td><strong>From:</strong></td><td>{ticket['sender']}</td></tr>
                <tr><td><strong>Issue:</strong></td><td>{ticket['issue']}</td></tr>
                <tr><td><strong>Category:</strong></td><td>{ticket['category']}</td></tr>
            </table>
            <p><strong>Action Required:</strong> Please respond within SLA.</p>
        </body>
        </html>
        """
        return self.send_email(team_email, subject, body_html)
    
    def send_sla_breach_warning(self, ticket: dict, team_email: str) -> bool:
        """Warn team about impending SLA breach."""
        subject = f"[SLA WARNING] Ticket #{ticket['id']} approaching breach"
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ff9800;">SLA Breach Warning</h2>
            <p>Ticket <strong>#{ticket['id']}</strong> is approaching SLA breach.</p>
            <p>Please take immediate action.</p>
        </body>
        </html>
        """
        return self.send_email(team_email, subject, body_html)


# Singleton instance
notifier = NotificationService()
