"""Integration tests for Gmail client - requires real Gmail account"""

import pytest
import os
from pathlib import Path

from emailparse.config import Config
from emailparse.gmail_client import GmailClient, GmailError
from emailparse.email_processor_v1 import EmailProcessor

class TestGmailIntegration:
    """Integration tests with real Gmail account"""
    
    @pytest.fixture(scope="class")
    def gmail_config(self):
        """Load Gmail configuration for integration tests"""
        # Skip if no credentials configured
        config_file = "config/config_v1.yaml"
        if not os.path.exists(config_file):
            pytest.skip("No Gmail configuration found. Create config/config_v1.yaml to run integration tests.")
        
        try:
            config = Config(config_file)
            return config
        except Exception as e:
            pytest.skip(f"Failed to load Gmail configuration: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_gmail
    def test_gmail_connection(self, gmail_config):
        """Test connection to real Gmail account"""
        client = GmailClient(gmail_config)
        
        try:
            # Test connection
            assert client.connect() is True
            
            # Test authentication
            assert client.authenticate() is True
            
        except GmailError as e:
            pytest.fail(f"Gmail connection failed: {e}")
        finally:
            client.close()
    
    @pytest.mark.integration
    @pytest.mark.requires_gmail
    def test_gmail_mailbox_operations(self, gmail_config):
        """Test Gmail mailbox operations"""
        with GmailClient(gmail_config) as client:
            try:
                # Connect and authenticate
                client.connect()
                client.authenticate()
                
                # Test mailbox selection
                assert client.select_mailbox("INBOX") is True
                assert client.current_mailbox == "INBOX"
                
                # Test email search (limit to avoid overwhelming)
                uids = client.search_emails(limit=5)
                assert isinstance(uids, list)
                print(f"Found {len(uids)} emails in INBOX")
                
                if uids:
                    # Test email fetching
                    emails = client.fetch_emails(uids[:2])  # Just fetch 2 emails
                    assert len(emails) <= 2
                    
                    for email in emails:
                        assert 'uid' in email
                        assert 'subject' in email
                        assert 'from' in email
                        assert 'body' in email
                        print(f"Fetched: {email['subject'][:50]}...")
                
            except GmailError as e:
                pytest.fail(f"Gmail operations failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_gmail
    def test_email_processor_integration(self, gmail_config):
        """Test full email processor with Gmail"""
        processor = EmailProcessor(gmail_config, export_mode=True)
        
        try:
            # Connect to Gmail
            assert processor.connect_gmail() is True
            
            # Process a small batch
            results = processor.process_batch(limit=3)
            
            assert 'total_found' in results
            assert 'total_processed' in results
            assert 'emails' in results
            
            print(f"Processing results: Found {results['total_found']}, Processed {results['total_processed']}")
            
            if results['export_file']:
                assert os.path.exists(results['export_file'])
                print(f"Exported to: {results['export_file']}")
                
                # Check file content
                with open(results['export_file'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert "# Email Batch:" in content
                    assert "## Email Details" in content or "## Table of Contents" in content
            
        except Exception as e:
            pytest.fail(f"Email processor integration test failed: {e}")
        finally:
            processor.close()
    
    @pytest.mark.integration
    @pytest.mark.requires_gmail
    def test_mailbox_listing(self, gmail_config):
        """Test listing Gmail mailboxes"""
        processor = EmailProcessor(gmail_config)
        
        try:
            processor.connect_gmail()
            
            mailboxes = processor.list_mailboxes()
            assert isinstance(mailboxes, list)
            assert len(mailboxes) > 0
            assert "INBOX" in mailboxes
            
            print(f"Found mailboxes: {mailboxes}")
            
        except Exception as e:
            pytest.fail(f"Mailbox listing failed: {e}")
        finally:
            processor.close()
    
    @pytest.mark.integration
    @pytest.mark.requires_gmail
    def test_mailbox_info(self, gmail_config):
        """Test getting mailbox information"""
        processor = EmailProcessor(gmail_config)
        
        try:
            processor.connect_gmail()
            
            info = processor.get_mailbox_info("INBOX")
            
            assert 'name' in info
            assert 'total_messages' in info
            assert 'unread_messages' in info
            assert info['name'] == "INBOX"
            assert info['total_messages'] >= 0
            assert info['unread_messages'] >= 0
            
            print(f"INBOX info: {info}")
            
        except Exception as e:
            pytest.fail(f"Mailbox info test failed: {e}")
        finally:
            processor.close()

# Manual test functions for command-line testing
def test_connection_manual():
    """Manual test function for testing Gmail connection"""
    try:
        config = Config()
        client = GmailClient(config)
        
        print("Connecting to Gmail...")
        client.connect()
        
        print("Authenticating...")
        client.authenticate()
        
        print("Selecting INBOX...")
        client.select_mailbox("INBOX")
        
        print("Searching for emails...")
        uids = client.search_emails(limit=5)
        print(f"Found {len(uids)} emails")
        
        if uids:
            print("Fetching first email...")
            emails = client.fetch_emails([uids[0]])
            if emails:
                email = emails[0]
                print(f"Subject: {email['subject']}")
                print(f"From: {email['from']}")
                print(f"Date: {email['date_str']}")
                print(f"Body preview: {email['body'][:100]}...")
        
        client.close()
        print("✅ Gmail connection test successful!")
        
    except Exception as e:
        print(f"❌ Gmail connection test failed: {e}")

def test_processor_manual():
    """Manual test function for testing email processor"""
    try:
        config = Config()
        processor = EmailProcessor(config, export_mode=True)
        
        print("Connecting to Gmail...")
        processor.connect_gmail()
        
        print("Processing batch of 3 emails...")
        results = processor.process_batch(limit=3)
        
        print(f"Found: {results['total_found']} emails")
        print(f"Processed: {results['total_processed']} emails")
        
        if results['export_file']:
            print(f"Exported to: {results['export_file']}")
            print("✅ Check the email_exports/ folder for the markdown file!")
        
        processor.close()
        print("✅ Email processor test successful!")
        
    except Exception as e:
        print(f"❌ Email processor test failed: {e}")

if __name__ == "__main__":
    # Run manual tests
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "connection":
        test_connection_manual()
    elif len(sys.argv) > 1 and sys.argv[1] == "processor":
        test_processor_manual()
    else:
        print("Usage:")
        print("  python test_gmail_integration.py connection  - Test Gmail connection")
        print("  python test_gmail_integration.py processor   - Test email processor")
        print("  pytest test_gmail_integration.py -m requires_gmail  - Run integration tests")