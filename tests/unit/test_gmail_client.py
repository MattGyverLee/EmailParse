"""Tests for Gmail IMAP client"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import imaplib
from datetime import datetime, timezone

from clients.gmail_client import GmailClient, GmailError
from utils.config import Config

class TestGmailClient:
    """Test Gmail IMAP client functionality"""
    
    @pytest.mark.unit
    def test_init(self, mock_config):
        """Test GmailClient initialization"""
        client = GmailClient(mock_config)
        
        assert client.config == mock_config
        assert client.connection is None
        assert client.is_connected is False
        assert client.current_mailbox is None
    
    @pytest.mark.unit
    @patch('clients.gmail_client.imaplib.IMAP4_SSL')
    def test_connect_success(self, mock_imap_ssl, mock_config):
        """Test successful Gmail connection"""
        mock_conn = MagicMock()
        mock_imap_ssl.return_value = mock_conn
        
        client = GmailClient(mock_config)
        result = client.connect()
        
        assert result is True
        assert client.is_connected is True
        assert client.connection == mock_conn
        mock_imap_ssl.assert_called_once()
    
    @pytest.mark.unit
    @patch('clients.gmail_client.imaplib.IMAP4_SSL')
    def test_connect_failure_with_retries(self, mock_imap_ssl, mock_config):
        """Test connection failure with retries"""
        mock_imap_ssl.side_effect = Exception("Connection failed")
        
        client = GmailClient(mock_config)
        
        with pytest.raises(GmailError, match="Failed to connect after 3 attempts"):
            client.connect(retries=3)
        
        # Should have tried 3 times
        assert mock_imap_ssl.call_count == 3
        assert client.is_connected is False
    
    @pytest.mark.unit
    def test_authenticate_oauth2_requires_setup(self, mock_config):
        """Test OAuth2 authentication requires interactive setup"""
        client = GmailClient(mock_config)
        client.connection = MagicMock()
        client.is_connected = True
        
        # Mock OAuth2 to raise an error (simulating setup failure)
        with patch('clients.gmail_oauth.GmailOAuth') as mock_oauth_class:
            mock_oauth = mock_oauth_class.return_value
            mock_oauth.authenticate.side_effect = Exception("OAuth2 setup required")
            
            with pytest.raises(GmailError):
                client.authenticate()
    
    @pytest.mark.unit
    def test_authenticate_not_connected(self, mock_config):
        """Test authentication when not connected"""
        client = GmailClient(mock_config)
        
        with pytest.raises(GmailError, match="Must connect before authenticating"):
            client.authenticate()
    
    @pytest.mark.unit
    def test_select_mailbox_success(self, mock_config):
        """Test successful mailbox selection"""
        mock_conn = MagicMock()
        mock_conn.select.return_value = ('OK', [b'100'])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        
        result = client.select_mailbox("INBOX")
        
        assert result is True
        assert client.current_mailbox == "INBOX"
        mock_conn.select.assert_called_once_with("INBOX", readonly=True)
    
    @pytest.mark.unit
    def test_select_mailbox_failure(self, mock_config):
        """Test mailbox selection failure"""
        mock_conn = MagicMock()
        mock_conn.select.return_value = ('NO', [b'Mailbox not found'])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        
        with pytest.raises(GmailError, match="Failed to select mailbox"):
            client.select_mailbox("NONEXISTENT")
    
    @pytest.mark.unit
    def test_search_emails_success(self, mock_config):
        """Test successful email search"""
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ('OK', [b'100 101 102'])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.current_mailbox = "INBOX"
        
        uids = client.search_emails(['UNSEEN'], limit=2)
        
        assert uids == [102, 101]  # Should be sorted newest first and limited
        mock_conn.uid.assert_called_once_with('SEARCH', None, 'UNSEEN')
    
    @pytest.mark.unit
    def test_search_emails_no_mailbox_selected(self, mock_config):
        """Test email search without mailbox selected"""
        client = GmailClient(mock_config)
        
        with pytest.raises(GmailError, match="Must select mailbox before searching"):
            client.search_emails()
    
    @pytest.mark.unit
    def test_search_emails_empty_result(self, mock_config):
        """Test email search with no results"""
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ('OK', [b''])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.current_mailbox = "INBOX"
        
        uids = client.search_emails()
        
        assert uids == []
    
    @pytest.mark.unit
    def test_fetch_emails_success(self, mock_config):
        """Test successful email fetching"""
        # Mock raw email data
        raw_email = (
            b'Date: Mon, 15 Jan 2025 10:30:00 +0000\r\n'
            b'From: sender@example.com\r\n'
            b'To: recipient@example.com\r\n'
            b'Subject: Test Subject\r\n'
            b'Message-ID: <test@example.com>\r\n'
            b'\r\n'
            b'This is the email body content.'
        )
        
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ('OK', [
            (b'123 (UID 123 RFC822 {200}', raw_email),
            b')'
        ])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.current_mailbox = "INBOX"
        
        emails = client.fetch_emails([123])
        
        assert len(emails) == 1
        email = emails[0]
        assert email['uid'] == 123
        assert email['subject'] == 'Test Subject'
        assert email['from'] == 'sender@example.com'
        assert 'This is the email body content' in email['body']
    
    @pytest.mark.unit
    def test_fetch_emails_empty_list(self, mock_config):
        """Test fetching emails with empty UID list"""
        client = GmailClient(mock_config)
        
        emails = client.fetch_emails([])
        
        assert emails == []
    
    @pytest.mark.unit
    def test_decode_header_utf8(self, mock_config):
        """Test header decoding with UTF-8"""
        client = GmailClient(mock_config)
        
        # Test normal header
        result = client._decode_header("Test Subject")
        assert result == "Test Subject"
        
        # Test empty header
        result = client._decode_header("")
        assert result == ""
        
        # Test None header
        result = client._decode_header(None)
        assert result == ""
    
    @pytest.mark.unit
    def test_extract_body_plain_text(self, mock_config):
        """Test body extraction from plain text email"""
        import email
        
        # Create test email message
        msg_str = (
            "Date: Mon, 15 Jan 2025 10:30:00 +0000\r\n"
            "From: sender@example.com\r\n"
            "Subject: Test\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "This is plain text content."
        )
        
        msg = email.message_from_string(msg_str, policy=email.policy.default)
        
        client = GmailClient(mock_config)
        body = client._extract_body(msg)
        
        assert "This is plain text content" in body
    
    @pytest.mark.unit
    def test_extract_body_html(self, mock_config):
        """Test body extraction from HTML email"""
        import email
        
        # Create test HTML email
        msg_str = (
            "Date: Mon, 15 Jan 2025 10:30:00 +0000\r\n"
            "From: sender@example.com\r\n"
            "Subject: Test\r\n"
            "Content-Type: text/html\r\n"
            "\r\n"
            "<html><body><p>This is <b>HTML</b> content.</p></body></html>"
        )
        
        msg = email.message_from_string(msg_str, policy=email.policy.default)
        
        client = GmailClient(mock_config)
        body = client._extract_body(msg)
        
        # Should have HTML tags stripped
        assert "This is HTML content" in body
        assert "<b>" not in body
        assert "<p>" not in body
    
    @pytest.mark.unit
    def test_strip_html(self, mock_config):
        """Test HTML stripping functionality"""
        client = GmailClient(mock_config)
        
        html_content = "<html><body><p>Hello <b>world</b>!</p><script>alert('bad');</script></body></html>"
        result = client._strip_html(html_content)
        
        assert "Hello world!" in result
        assert "<p>" not in result
        assert "<b>" not in result
        assert "alert('bad')" not in result  # Script should be removed
    
    @pytest.mark.unit
    def test_create_folder_success(self, mock_config):
        """Test successful folder creation"""
        mock_conn = MagicMock()
        mock_conn.create.return_value = ('OK', [b'CREATE completed'])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        
        result = client.create_folder("Test-Folder")
        
        assert result is True
        mock_conn.create.assert_called_once_with("Test-Folder")
    
    @pytest.mark.unit
    def test_create_folder_already_exists(self, mock_config):
        """Test folder creation when folder already exists"""
        mock_conn = MagicMock()
        mock_conn.create.return_value = ('NO', [b'Folder already exists'])
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        
        result = client.create_folder("Existing-Folder")
        
        assert result is True  # Should still return True for existing folders
    
    @pytest.mark.unit
    def test_create_folder_not_connected(self, mock_config):
        """Test folder creation when not connected"""
        client = GmailClient(mock_config)
        
        with pytest.raises(GmailError, match="Must be connected to create folder"):
            client.create_folder("Test-Folder")
    
    @pytest.mark.unit
    def test_close_connection(self, mock_config):
        """Test connection closing"""
        mock_conn = MagicMock()
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        client.current_mailbox = "INBOX"
        
        client.close()
        
        assert client.connection is None
        assert client.is_connected is False
        assert client.current_mailbox is None
        mock_conn.close.assert_called_once()
        mock_conn.logout.assert_called_once()
    
    @pytest.mark.unit
    def test_close_connection_with_error(self, mock_config):
        """Test connection closing with error (should not raise)"""
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Close error")
        
        client = GmailClient(mock_config)
        client.connection = mock_conn
        client.is_connected = True
        
        # Should not raise exception
        client.close()
        
        assert client.connection is None
        assert client.is_connected is False
    
    @pytest.mark.unit
    def test_context_manager(self, mock_config):
        """Test context manager functionality"""
        with patch.object(GmailClient, 'close') as mock_close:
            with GmailClient(mock_config) as client:
                assert isinstance(client, GmailClient)
            
            mock_close.assert_called_once()
    
    @pytest.mark.unit
    def test_oauth2_string_creation(self, mock_config):
        """Test OAuth2 authentication string creation via GmailOAuth"""
        from clients.gmail_oauth import GmailOAuth
        import time
        
        oauth = GmailOAuth()
        oauth.access_token = "access_token_123"  # Set token directly for testing
        oauth.expires_at = time.time() + 3600    # Set token to be valid for 1 hour
        auth_string = oauth.create_xoauth2_string("test@gmail.com")
        
        # Should be base64 encoded
        import base64
        decoded = base64.b64decode(auth_string).decode()
        assert "user=test@gmail.com" in decoded
        assert "auth=Bearer access_token_123" in decoded
    
    @pytest.mark.unit
    def test_parse_email_data_success(self, mock_config):
        """Test successful email data parsing"""
        # Create a realistic raw email
        raw_email = (
            b'Date: Mon, 15 Jan 2025 10:30:00 +0000\r\n'
            b'From: sender@example.com\r\n'
            b'To: recipient@example.com\r\n'
            b'Subject: Test Subject\r\n'
            b'Message-ID: <test123@example.com>\r\n'
            b'Content-Type: text/plain\r\n'
            b'\r\n'
            b'This is the email body content.\r\n'
            b'Multiple lines of text.\r\n'
        )
        
        client = GmailClient(mock_config)
        result = client._parse_email_data(12345, (b'response', raw_email))
        
        assert result is not None
        assert result['uid'] == 12345
        assert result['subject'] == 'Test Subject'
        assert result['from'] == 'sender@example.com'
        assert result['to'] == 'recipient@example.com'
        assert result['message_id'] == '<test123@example.com>'
        assert 'This is the email body content' in result['body']
        assert result['size'] == len(raw_email)
        assert isinstance(result['date'], datetime)
    
    @pytest.mark.unit
    def test_parse_email_data_failure(self, mock_config):
        """Test email data parsing with invalid data"""
        client = GmailClient(mock_config)
        
        # Test with None data
        result = client._parse_email_data(12345, (b'response', None))
        assert result is None
        
        # Test with corrupted email data that will fail email parsing
        result = client._parse_email_data(12345, (b'response', b'\xff\xfe'))  # Invalid bytes
        # The email library is quite forgiving, so we might still get a result
        # but it should handle the error gracefully

class TestGmailClientIntegration:
    """Integration-style tests for Gmail client"""
    
    @pytest.mark.unit
    def test_full_email_processing_flow(self, mock_config):
        """Test the full email processing flow with mocked IMAP"""
        # Create a more complete mock email
        raw_email = (
            b'Date: Mon, 15 Jan 2025 10:30:00 +0000\r\n'
            b'From: "Test Sender" <sender@example.com>\r\n'
            b'To: recipient@example.com\r\n'
            b'Subject: =?UTF-8?B?VGVzdCBTdWJqZWN0IPCfk4c=?=\r\n'  # "Test Subject 📇" in base64
            b'Message-ID: <test123@example.com>\r\n'
            b'Content-Type: text/plain; charset=utf-8\r\n'
            b'\r\n'
            b'This is a test email with UTF-8 content.\r\n'
            b'Line 2 of the email body.\r\n'
        )
        
        mock_conn = MagicMock()
        # Mock successful connection and auth
        mock_conn.login.return_value = ('OK', ['Success'])
        # Mock mailbox selection
        mock_conn.select.return_value = ('OK', [b'50'])
        # Mock search results
        mock_conn.uid.side_effect = [
            ('OK', [b'100 101 102']),  # Search results
            ('OK', [  # Fetch results
                (b'100 (UID 100 RFC822 {' + str(len(raw_email)).encode() + b'}', raw_email),
                b')'
            ])
        ]
        
        with patch('clients.gmail_client.imaplib.IMAP4_SSL', return_value=mock_conn), \
             patch('clients.gmail_oauth.GmailOAuth') as mock_oauth_class:
            
            # Mock OAuth2 authentication
            mock_oauth = mock_oauth_class.return_value
            mock_oauth.authenticate.return_value = 'fake_access_token'
            mock_oauth.create_xoauth2_string.return_value = b'fake_xoauth2_string'
            mock_conn.authenticate.return_value = ('OK', [b'Authentication successful'])
            
            client = GmailClient(mock_config)
            
            # Full flow: connect, auth, select, search, fetch
            assert client.connect() is True
            assert client.authenticate() is True
            assert client.select_mailbox("INBOX") is True
            
            uids = client.search_emails(['UNSEEN'], limit=1)
            assert len(uids) == 1
            assert uids[0] == 102  # Newest first
            
            emails = client.fetch_emails([100])  # Fetch different UID for testing
            assert len(emails) == 1
            
            email = emails[0]
            assert email['uid'] == 100
            assert "Test Subject" in email['subject']  # UTF-8 decoded
            assert 'Test Sender' in email['from']
            assert 'sender@example.com' in email['from']
            assert "test email with UTF-8" in email['body']
            
            client.close()