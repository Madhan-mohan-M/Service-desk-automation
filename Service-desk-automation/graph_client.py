"""
Microsoft Graph API client for reading Office 365 emails.
Requires Azure AD app registration with Mail.Read permission.
"""
import requests
from typing import List, Dict, Optional
import config


class GraphClient:
    """Client for Microsoft Graph API to read O365 mailbox."""
    
    TOKEN_URL = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    GRAPH_URL = 'https://graph.microsoft.com/v1.0'
    
    def __init__(self):
        self.client_id = config.GRAPH_CLIENT_ID
        self.client_secret = config.GRAPH_CLIENT_SECRET
        self.tenant_id = config.GRAPH_TENANT_ID
        self.user_email = config.GRAPH_USER_EMAIL
        self._token = None
    
    def _get_token(self) -> str:
        """Get OAuth2 access token using client credentials flow."""
        if self._token:
            return self._token
        
        url = self.TOKEN_URL.format(tenant=self.tenant_id)
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        self._token = resp.json()['access_token']
        return self._token
    
    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json'
        }
    
    def get_unread_emails(self, folder: str = 'Inbox', top: int = 50) -> List[Dict]:
        """
        Fetch unread emails from the specified folder.
        Returns list of dicts with: id, sender, subject, body, received_at
        """
        url = f"{self.GRAPH_URL}/users/{self.user_email}/mailFolders/{folder}/messages"
        params = {
            '$filter': 'isRead eq false',
            '$top': top,
            '$select': 'id,from,subject,body,receivedDateTime',
            '$orderby': 'receivedDateTime desc'
        }
        
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        
        emails = []
        for msg in resp.json().get('value', []):
            emails.append({
                'id': msg['id'],
                'sender': msg.get('from', {}).get('emailAddress', {}).get('address', 'unknown'),
                'subject': msg.get('subject', ''),
                'body': msg.get('body', {}).get('content', ''),
                'received_at': msg.get('receivedDateTime', '')
            })
        return emails
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read after processing."""
        url = f"{self.GRAPH_URL}/users/{self.user_email}/messages/{message_id}"
        data = {'isRead': True}
        
        resp = requests.patch(url, headers=self._headers(), json=data, timeout=30)
        return resp.status_code == 200
    
    def move_to_folder(self, message_id: str, destination_folder: str) -> bool:
        """Move processed email to a folder (e.g., 'Processed')."""
        url = f"{self.GRAPH_URL}/users/{self.user_email}/messages/{message_id}/move"
        data = {'destinationId': destination_folder}
        
        resp = requests.post(url, headers=self._headers(), json=data, timeout=30)
        return resp.status_code == 201
    
    def is_configured(self) -> bool:
        """Check if Graph API credentials are configured."""
        return all([self.client_id, self.client_secret, self.tenant_id, self.user_email])


# Singleton instance
graph_client = GraphClient()


def fetch_o365_emails() -> List[Dict]:
    """
    Fetch emails from O365 if configured, otherwise return empty list.
    This is the main entry point for the automation.
    """
    if not graph_client.is_configured():
        return []
    
    try:
        emails = graph_client.get_unread_emails()
        return emails
    except Exception as e:
        print(f"[Graph API Error] {e}")
        return []
