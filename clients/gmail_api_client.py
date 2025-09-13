#!/usr/bin/env python3
"""
Gmail API client for EmailParse - alternative to IMAP client
Uses Gmail API instead of IMAP for more reliable OAuth2 authentication
"""

import requests
import base64
import email
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GmailAPIError(Exception):
    """Gmail API error"""
    pass

class GmailAPIClient:
    """Gmail API client for fetching emails"""
    
    def __init__(self, config):
        """Initialize Gmail API client with configuration"""
        self.config = config
        self.gmail_config = config.get_gmail_config()
        self.access_token = None
        
    def authenticate(self) -> bool:
        """Authenticate using OAuth2 tokens"""
        try:
            from .gmail_oauth import GmailOAuth
            
            # Initialize OAuth with configuration
            auth_config = self.gmail_config.get('auth', {})
            oauth_config = auth_config.get('oauth2', {})
            
            oauth = GmailOAuth(
                client_id=oauth_config.get('client_id'),
                client_secret=oauth_config.get('client_secret'),
                token_file=oauth_config.get('token_file', 'gmail_tokens.json')
            )
            
            self.access_token = oauth.authenticate()
            logger.info("Gmail API authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Gmail API authentication failed: {e}")
            raise GmailAPIError(f"Authentication failed: {e}")
    
    def _make_request(self, url: str, params: Dict = None, method: str = 'GET', json: Dict = None) -> Dict:
        """Make authenticated request to Gmail API"""
        if not self.access_token:
            raise GmailAPIError("Not authenticated - call authenticate() first")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=json, timeout=30)
        else:
            raise GmailAPIError(f"Unsupported HTTP method: {method}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise GmailAPIError("Authentication expired - need to refresh tokens")
        else:
            raise GmailAPIError(f"API request failed: {response.status_code} - {response.text}")
    
    def search_emails(self, query: str = '', limit: int = 10) -> List[str]:
        """
        Search for emails and return message IDs
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            limit: Maximum number of emails to return
            
        Returns:
            List of message IDs
        """
        logger.info(f"Searching for emails with query: '{query}', limit: {limit}")
        
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
        params = {
            'maxResults': limit
        }
        
        if query:
            params['q'] = query
        
        try:
            result = self._make_request(url, params)
            messages = result.get('messages', [])
            message_ids = [msg['id'] for msg in messages]
            
            logger.info(f"Found {len(message_ids)} emails")
            return message_ids
            
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            raise GmailAPIError(f"Search failed: {e}")
    
    def fetch_email(self, message_id: str) -> Dict[str, Any]:
        """
        Fetch a single email by message ID
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing email data
        """
        url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}'
        params = {'format': 'full'}
        
        try:
            result = self._make_request(url, params)
            return self._parse_email_data(result)
            
        except Exception as e:
            logger.error(f"Failed to fetch email {message_id}: {e}")
            raise GmailAPIError(f"Fetch failed: {e}")
    
    def fetch_emails(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple emails by message IDs
        
        Args:
            message_ids: List of Gmail message IDs
            
        Returns:
            List of email dictionaries
        """
        logger.info(f"Fetching {len(message_ids)} emails")
        
        emails = []
        for i, msg_id in enumerate(message_ids, 1):
            try:
                logger.info(f"Fetching email {i}/{len(message_ids)}: {msg_id}")
                email_data = self.fetch_email(msg_id)
                emails.append(email_data)
            except Exception as e:
                logger.warning(f"Failed to fetch email {msg_id}: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(emails)} emails")
        return emails
    
    def _parse_email_data(self, gmail_message: Dict) -> Dict[str, Any]:
        """Parse Gmail API message data into standardized format"""
        try:
            payload = gmail_message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract headers
            header_dict = {}
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                header_dict[name] = value
            
            # Extract body
            body = self._extract_body(payload)
            
            # Parse date
            date_str = header_dict.get('date', '')
            try:
                if date_str:
                    # Parse RFC 2822 date format
                    date_obj = email.utils.parsedate_to_datetime(date_str)
                else:
                    date_obj = datetime.now()
            except:
                date_obj = datetime.now()
            
            # Create email dictionary
            email_data = {
                'uid': gmail_message.get('id'),
                'message_id': header_dict.get('message-id', ''),
                'subject': self._decode_header(header_dict.get('subject', 'No Subject')),
                'from': self._decode_header(header_dict.get('from', 'Unknown Sender')),
                'to': self._decode_header(header_dict.get('to', '')),
                'cc': self._decode_header(header_dict.get('cc', '')),
                'bcc': self._decode_header(header_dict.get('bcc', '')),
                'date': date_obj,
                'size': gmail_message.get('sizeEstimate', 0),
                'body': body,
                'headers': header_dict,
                'labels': gmail_message.get('labelIds', [])
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to parse email data: {e}")
            return {
                'uid': gmail_message.get('id', 'unknown'),
                'subject': 'Failed to parse email',
                'from': 'Unknown',
                'date': datetime.now(),
                'body': f'Error parsing email: {e}',
                'size': 0
            }
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from Gmail API payload"""
        try:
            body_parts = []
            
            # Check if this part has body data
            if 'body' in payload and 'data' in payload['body']:
                data = payload['body']['data']
                decoded = base64.urlsafe_b64decode(data + '=' * (4 - len(data) % 4))
                body_parts.append(decoded.decode('utf-8', errors='ignore'))
            
            # Check for multipart content
            if 'parts' in payload:
                for part in payload['parts']:
                    part_body = self._extract_body(part)
                    if part_body:
                        body_parts.append(part_body)
            
            combined_body = '\\n\\n'.join(body_parts)
            
            # Clean up HTML if present
            if '<html' in combined_body.lower() or '<body' in combined_body.lower():
                combined_body = self._strip_html(combined_body)
            
            return combined_body.strip()
            
        except Exception as e:
            logger.warning(f"Failed to extract email body: {e}")
            return "Could not extract email body"
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding, errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string
            
        except Exception:
            return str(header_value)
    
    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags from content"""
        try:
            from html2text import html2text
            return html2text(html_content)
        except ImportError:
            # Fallback: simple regex-based HTML stripping
            import re
            # Remove script and style elements
            html_content = re.sub(r'<(script|style)[^>]*>.*?</\\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            html_content = re.sub(r'<[^>]+>', '', html_content)
            # Clean up whitespace
            html_content = re.sub(r'\\s+', ' ', html_content)
            return html_content.strip()
    
    def get_profile(self) -> Dict:
        """Get Gmail profile information"""
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/profile'
        return self._make_request(url)
    
    def add_label(self, message_id: str, label_name: str) -> bool:
        """
        Add a label to an email message
        
        Args:
            message_id: Gmail message ID
            label_name: Name of the label to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First, get or create the label
            label_id = self._get_or_create_label(label_name)
            
            # Add the label to the message
            url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify'
            payload = {
                'addLabelIds': [label_id]
            }
            
            self._make_request(url, method='POST', json=payload)
            logger.info(f"Added label '{label_name}' to message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add label '{label_name}' to message {message_id}: {e}")
            return False
    
    def remove_label(self, message_id: str, label_name: str) -> bool:
        """
        Remove a label from an email message
        
        Args:
            message_id: Gmail message ID
            label_name: Name of the label to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the label ID
            label_id = self._get_label_id(label_name)
            if not label_id:
                logger.warning(f"Label '{label_name}' not found")
                return False
            
            # Remove the label from the message
            url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify'
            payload = {
                'removeLabelIds': [label_id]
            }
            
            self._make_request(url, method='POST', json=payload)
            logger.info(f"Removed label '{label_name}' from message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove label '{label_name}' from message {message_id}: {e}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID, creating the label if it doesn't exist"""
        # First try to get existing label
        label_id = self._get_label_id(label_name)
        if label_id:
            return label_id
        
        # Create new label
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/labels'
        payload = {
            'name': label_name,
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        }
        
        response = self._make_request(url, method='POST', json=payload)
        return response['id']
    
    def _get_label_id(self, label_name: str) -> Optional[str]:
        """Get the ID of a label by name"""
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/labels'
        response = self._make_request(url)
        
        for label in response.get('labels', []):
            if label.get('name') == label_name:
                return label.get('id')
        
        return None