"""Gmail IMAP client with authentication and email operations"""

import imaplib
import ssl
import email
import email.policy
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
import base64
from datetime import datetime, timezone

from .config import Config

logger = logging.getLogger(__name__)

class GmailError(Exception):
    """Gmail client errors"""
    pass

class GmailClient:
    """Gmail IMAP client with authentication support"""
    
    def __init__(self, config: Config):
        """
        Initialize Gmail client
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.gmail_config = config.get_gmail_config()
        self.processing_config = config.get_processing_config()
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self.is_connected = False
        self.current_mailbox = None
        
    def connect(self, retries: int = 3) -> bool:
        """
        Connect to Gmail IMAP server
        
        Args:
            retries: Number of connection attempts
            
        Returns:
            True if connected successfully
            
        Raises:
            GmailError: If connection fails after all retries
        """
        host = self.gmail_config.get('host', 'imap.gmail.com')
        port = self.gmail_config.get('port', 993)
        use_ssl = self.gmail_config.get('use_ssl', True)
        
        last_error = None
        
        for attempt in range(retries):
            try:
                logger.info(f"Connecting to {host}:{port} (attempt {attempt + 1}/{retries})")
                
                if use_ssl:
                    # Create SSL context
                    ssl_context = ssl.create_default_context()
                    self.connection = imaplib.IMAP4_SSL(host, port, ssl_context=ssl_context)
                else:
                    self.connection = imaplib.IMAP4(host, port)
                
                self.is_connected = True
                logger.info("Connected to Gmail IMAP server successfully")
                return True
                
            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        raise GmailError(f"Failed to connect after {retries} attempts: {last_error}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail using interactive OAuth2
        
        Returns:
            True if authentication successful
            
        Raises:
            GmailError: If authentication fails
        """
        if not self.is_connected:
            raise GmailError("Must connect before authenticating")
        
        user = self.gmail_config.get('user')
        if not user:
            raise GmailError("Gmail user not specified in configuration")
        
        try:
            # Always use OAuth2 - app passwords are deprecated
            logger.info("Authenticating with OAuth2")
            
            # Import OAuth handler
            from .gmail_oauth import GmailOAuth
            
            # Initialize OAuth with any configured credentials
            auth_config = self.gmail_config.get('auth', {})
            oauth_config = auth_config.get('oauth2', {})
            
            oauth = GmailOAuth(
                client_id=oauth_config.get('client_id'),
                client_secret=oauth_config.get('client_secret'),
                token_file=oauth_config.get('token_file', 'gmail_tokens.json')
            )
            
            # Authenticate and get XOAUTH2 string
            access_token = oauth.authenticate()
            auth_string = oauth.create_xoauth2_string(user)
            
            # Authenticate with Gmail IMAP
            result = self.connection.authenticate('XOAUTH2', lambda x: auth_string.encode('utf-8'))
            
            if result[0] == 'OK':
                logger.info("OAuth2 authentication successful")
                return True
            else:
                raise GmailError(f"IMAP authentication failed: {result[1]}")
                
        except Exception as e:
            if "gmail_oauth" in str(e):
                raise GmailError(f"OAuth setup required: {e}")
            else:
                raise GmailError(f"Authentication error: {e}")
    
    
    def select_mailbox(self, mailbox: str = "INBOX", readonly: bool = True) -> bool:
        """
        Select a mailbox
        
        Args:
            mailbox: Mailbox name
            readonly: Open in read-only mode
            
        Returns:
            True if selection successful
            
        Raises:
            GmailError: If mailbox selection fails
        """
        if not self.is_connected:
            raise GmailError("Must be connected to select mailbox")
        
        try:
            if readonly:
                result = self.connection.select(mailbox, readonly=True)
            else:
                result = self.connection.select(mailbox)
            
            if result[0] == 'OK':
                self.current_mailbox = mailbox
                total_messages = int(result[1][0])
                logger.info(f"Selected mailbox '{mailbox}' with {total_messages} messages (readonly={readonly})")
                return True
            else:
                raise GmailError(f"Failed to select mailbox '{mailbox}': {result[1]}")
                
        except Exception as e:
            raise GmailError(f"Error selecting mailbox: {e}")
    
    def search_emails(self, criteria: List[str] = None, limit: int = None) -> List[int]:
        """
        Search for emails
        
        Args:
            criteria: Search criteria (e.g., ['UNSEEN', 'FROM', 'sender@example.com'])
            limit: Maximum number of UIDs to return
            
        Returns:
            List of email UIDs
            
        Raises:
            GmailError: If search fails
        """
        if not self.current_mailbox:
            raise GmailError("Must select mailbox before searching")
        
        if criteria is None:
            criteria = ['ALL']
        
        try:
            result = self.connection.uid('SEARCH', None, *criteria)
            
            if result[0] == 'OK':
                uid_list = result[1][0].decode().split() if result[1] and result[1][0] else []
                uids = [int(uid) for uid in uid_list]
                
                # Sort by UID (newest first) and apply limit
                uids.sort(reverse=True)
                if limit:
                    uids = uids[:limit]
                
                logger.info(f"Found {len(uids)} emails matching criteria: {' '.join(criteria)}")
                return uids
            else:
                raise GmailError(f"Search failed: {result[1]}")
                
        except Exception as e:
            raise GmailError(f"Error searching emails: {e}")
    
    def fetch_emails(self, uids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch email details for given UIDs
        
        Args:
            uids: List of email UIDs
            
        Returns:
            List of email dictionaries with parsed content
            
        Raises:
            GmailError: If fetch fails
        """
        if not uids:
            return []
        
        if not self.current_mailbox:
            raise GmailError("Must select mailbox before fetching")
        
        emails = []
        
        try:
            # Convert UIDs to comma-separated string
            uid_string = ','.join(str(uid) for uid in uids)
            
            # Fetch email data
            result = self.connection.uid('FETCH', uid_string, '(RFC822 FLAGS)')
            
            if result[0] != 'OK':
                raise GmailError(f"Fetch failed: {result[1]}")
            
            # Parse each email
            for i, item in enumerate(result[1]):
                if isinstance(item, tuple):
                    email_data = self._parse_email_data(uids[i // 2], item)
                    if email_data:
                        emails.append(email_data)
            
            logger.info(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            raise GmailError(f"Error fetching emails: {e}")
    
    def _parse_email_data(self, uid: int, raw_data: Tuple) -> Optional[Dict[str, Any]]:
        """
        Parse raw email data into structured dictionary
        
        Args:
            uid: Email UID
            raw_data: Raw email data from IMAP
            
        Returns:
            Parsed email dictionary or None if parsing fails
        """
        try:
            # Extract the raw email message
            raw_email = raw_data[1]
            if not raw_email:
                return None
            
            # Parse with email library
            msg = email.message_from_bytes(raw_email, policy=email.policy.default)
            
            # Extract basic headers
            subject = self._decode_header(msg.get('Subject', ''))
            from_header = self._decode_header(msg.get('From', ''))
            to_header = self._decode_header(msg.get('To', ''))
            date_header = msg.get('Date', '')
            message_id = msg.get('Message-ID', '')
            
            # Parse date
            parsed_date = None
            if date_header:
                try:
                    parsed_date = email.utils.parsedate_to_datetime(date_header)
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                except Exception:
                    parsed_date = datetime.now(timezone.utc)
            else:
                parsed_date = datetime.now(timezone.utc)
            
            # Extract body content
            body_text = self._extract_body(msg)
            
            # Calculate size
            email_size = len(raw_email)
            
            return {
                'uid': uid,
                'subject': subject,
                'from': from_header,
                'to': to_header,
                'date': parsed_date,
                'date_str': parsed_date.isoformat(),
                'message_id': message_id,
                'body': body_text,
                'size': email_size,
                'raw_size_mb': round(email_size / 1024 / 1024, 2),
                'headers': {
                    'Subject': subject,
                    'From': from_header,
                    'To': to_header,
                    'Date': date_header,
                    'Message-ID': message_id,
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse email UID {uid}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """
        Decode email header handling various encodings
        
        Args:
            header: Raw header string
            
        Returns:
            Decoded header string
        """
        if not header:
            return ""
        
        try:
            decoded_parts = email.header.decode_header(header)
            decoded_str = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_str += part.decode(encoding)
                    else:
                        decoded_str += part.decode('utf-8', errors='replace')
                else:
                    decoded_str += part
            
            return decoded_str.strip()
            
        except Exception as e:
            logger.warning(f"Failed to decode header '{header[:50]}...': {e}")
            return header
    
    def _extract_body(self, msg: email.message.EmailMessage) -> str:
        """
        Extract text body from email message
        
        Args:
            msg: Email message object
            
        Returns:
            Plain text body content
        """
        try:
            # Try to get plain text body first
            body = msg.get_body(preferencelist=('plain', 'html'))
            
            if body is None:
                # Fallback: walk through message parts
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain':
                        body = part
                        break
                    elif content_type == 'text/html' and body is None:
                        body = part
            
            if body is None:
                return "(No readable content)"
            
            # Get content
            content = body.get_content()
            
            if not content:
                return "(Empty content)"
            
            # If HTML, strip tags (basic)
            if body.get_content_type() == 'text/html':
                content = self._strip_html(content)
            
            # Clean up and limit length
            content = content.strip()
            if len(content) > 10000:  # Limit to prevent huge emails
                content = content[:10000] + "\n\n[... content truncated ...]"
            
            return content
            
        except Exception as e:
            logger.warning(f"Failed to extract body: {e}")
            return "(Failed to extract content)"
    
    def _strip_html(self, html_content: str) -> str:
        """
        Basic HTML tag stripping
        
        Args:
            html_content: HTML content
            
        Returns:
            Plain text content
        """
        try:
            # Very basic HTML stripping - in production we'd use BeautifulSoup
            import re
            # Remove script and style elements
            html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            html_content = re.sub(r'<[^>]+>', '', html_content)
            # Clean up whitespace
            html_content = re.sub(r'\s+', ' ', html_content)
            return html_content.strip()
        except Exception:
            return html_content
    
    def create_folder(self, folder_name: str) -> bool:
        """
        Create a folder/label in Gmail
        
        Args:
            folder_name: Name of folder to create
            
        Returns:
            True if folder created or already exists
            
        Raises:
            GmailError: If folder creation fails
        """
        if not self.is_connected:
            raise GmailError("Must be connected to create folder")
        
        try:
            result = self.connection.create(folder_name)
            if result[0] == 'OK':
                logger.info(f"Created folder '{folder_name}'")
                return True
            elif 'already exists' in result[1][0].decode().lower():
                logger.info(f"Folder '{folder_name}' already exists")
                return True
            else:
                raise GmailError(f"Failed to create folder '{folder_name}': {result[1]}")
                
        except Exception as e:
            if 'already exists' in str(e).lower():
                logger.info(f"Folder '{folder_name}' already exists")
                return True
            raise GmailError(f"Error creating folder: {e}")
    
    def close(self):
        """Close the IMAP connection"""
        try:
            if self.connection and self.is_connected:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from Gmail IMAP server")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
        finally:
            self.connection = None
            self.is_connected = False
            self.current_mailbox = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()