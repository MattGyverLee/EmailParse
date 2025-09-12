"""Main email processor for V1.0 - with markdown export mode"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

from .config import Config, get_config
from .gmail_client import GmailClient, GmailError
from .markdown_exporter import MarkdownExporter

logger = logging.getLogger(__name__)

class EmailProcessor:
    """Main email processor with markdown export capability"""
    
    def __init__(self, config: Optional[Config] = None, export_mode: bool = True):
        """
        Initialize email processor
        
        Args:
            config: Configuration object (will load default if None)
            export_mode: If True, export emails to markdown instead of processing
        """
        self.config = config or get_config()
        self.export_mode = export_mode
        self.gmail_client = None
        self.markdown_exporter = None
        
        # Initialize components
        if self.export_mode:
            self.markdown_exporter = MarkdownExporter()
        
        # Set up logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        app_config = self.config.get_app_config()
        log_level = app_config.get('log_level', 'INFO')
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def connect_gmail(self) -> bool:
        """
        Connect and authenticate with Gmail
        
        Returns:
            True if connection successful
            
        Raises:
            GmailError: If connection/authentication fails
        """
        try:
            self.gmail_client = GmailClient(self.config)
            
            # Connect
            if not self.gmail_client.connect():
                raise GmailError("Failed to connect to Gmail")
            
            # Authenticate
            if not self.gmail_client.authenticate():
                raise GmailError("Failed to authenticate with Gmail")
            
            logger.info("Successfully connected and authenticated with Gmail")
            return True
            
        except Exception as e:
            logger.error(f"Gmail connection failed: {e}")
            if self.gmail_client:
                self.gmail_client.close()
                self.gmail_client = None
            raise
    
    def process_batch(self, 
                     mailbox: str = "INBOX",
                     limit: int = None,
                     search_criteria: List[str] = None) -> Dict[str, Any]:
        """
        Process a batch of emails
        
        Args:
            mailbox: Mailbox to process (default: INBOX)
            limit: Maximum number of emails to process
            search_criteria: Email search criteria
            
        Returns:
            Processing results dictionary
            
        Raises:
            GmailError: If processing fails
        """
        if not self.gmail_client:
            raise GmailError("Must connect to Gmail first")
        
        # Get configuration
        processing_config = self.config.get_processing_config()
        if limit is None:
            limit = processing_config.get('batch_size', 10)
        
        results = {
            'mailbox': mailbox,
            'total_found': 0,
            'total_processed': 0,
            'emails': [],
            'export_file': None,
            'errors': []
        }
        
        try:
            # Select mailbox
            logger.info(f"Selecting mailbox: {mailbox}")
            self.gmail_client.select_mailbox(mailbox, readonly=True)
            
            # Search for emails
            logger.info(f"Searching for emails with criteria: {search_criteria or ['ALL']}")
            uids = self.gmail_client.search_emails(criteria=search_criteria, limit=limit)
            results['total_found'] = len(uids)
            
            if not uids:
                logger.info("No emails found matching criteria")
                return results
            
            # Fetch email details
            logger.info(f"Fetching details for {len(uids)} emails")
            emails = self.gmail_client.fetch_emails(uids)
            results['emails'] = emails
            results['total_processed'] = len(emails)
            
            # Export to markdown if in export mode
            if self.export_mode and emails:
                batch_name = f"{mailbox}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                export_file = self.markdown_exporter.export_batch(emails, batch_name)
                results['export_file'] = export_file
                logger.info(f"Exported {len(emails)} emails to {export_file}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error processing batch: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    def process_single_email(self, uid: int, mailbox: str = "INBOX") -> Dict[str, Any]:
        """
        Process a single email by UID
        
        Args:
            uid: Email UID
            mailbox: Mailbox containing the email
            
        Returns:
            Processing results dictionary
        """
        if not self.gmail_client:
            raise GmailError("Must connect to Gmail first")
        
        results = {
            'uid': uid,
            'mailbox': mailbox,
            'email': None,
            'export_file': None,
            'errors': []
        }
        
        try:
            # Select mailbox
            self.gmail_client.select_mailbox(mailbox, readonly=True)
            
            # Fetch single email
            emails = self.gmail_client.fetch_emails([uid])
            
            if emails:
                email_data = emails[0]
                results['email'] = email_data
                
                # Export to markdown if in export mode
                if self.export_mode:
                    export_file = self.markdown_exporter.export_single_email(email_data)
                    results['export_file'] = export_file
                    logger.info(f"Exported email UID {uid} to {export_file}")
            else:
                error_msg = f"Email with UID {uid} not found"
                logger.warning(error_msg)
                results['errors'].append(error_msg)
            
            return results
            
        except Exception as e:
            error_msg = f"Error processing email UID {uid}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    def list_mailboxes(self) -> List[str]:
        """
        List available mailboxes
        
        Returns:
            List of mailbox names
        """
        if not self.gmail_client:
            raise GmailError("Must connect to Gmail first")
        
        try:
            result = self.gmail_client.connection.list()
            if result[0] == 'OK':
                mailboxes = []
                for item in result[1]:
                    # Parse mailbox name from IMAP LIST response
                    # Format: (flags) "delimiter" "name"
                    parts = item.decode().split('"')
                    if len(parts) >= 3:
                        mailbox_name = parts[-2]  # Second-to-last quoted string
                        mailboxes.append(mailbox_name)
                
                logger.info(f"Found {len(mailboxes)} mailboxes")
                return sorted(mailboxes)
            else:
                raise GmailError(f"Failed to list mailboxes: {result[1]}")
                
        except Exception as e:
            logger.error(f"Error listing mailboxes: {e}")
            raise GmailError(f"Failed to list mailboxes: {e}")
    
    def get_mailbox_info(self, mailbox: str = "INBOX") -> Dict[str, Any]:
        """
        Get information about a mailbox
        
        Args:
            mailbox: Mailbox name
            
        Returns:
            Mailbox information dictionary
        """
        if not self.gmail_client:
            raise GmailError("Must connect to Gmail first")
        
        try:
            # Select mailbox to get message count
            result = self.gmail_client.connection.select(mailbox, readonly=True)
            
            if result[0] == 'OK':
                total_messages = int(result[1][0])
                
                # Get unread count
                unread_uids = self.gmail_client.search_emails(['UNSEEN'])
                unread_count = len(unread_uids)
                
                return {
                    'name': mailbox,
                    'total_messages': total_messages,
                    'unread_messages': unread_count,
                    'read_messages': total_messages - unread_count
                }
            else:
                raise GmailError(f"Failed to select mailbox {mailbox}: {result[1]}")
                
        except Exception as e:
            logger.error(f"Error getting mailbox info for {mailbox}: {e}")
            raise GmailError(f"Failed to get mailbox info: {e}")
    
    def close(self):
        """Close connections and cleanup"""
        if self.gmail_client:
            self.gmail_client.close()
            self.gmail_client = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EmailParse V1.0 - Email Processor")
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--mailbox', '-m', default='INBOX', help='Mailbox to process')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Number of emails to process')
    parser.add_argument('--list-mailboxes', action='store_true', help='List available mailboxes')
    parser.add_argument('--mailbox-info', help='Get info about specific mailbox')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config(args.config) if args.config else get_config()
        
        # Create processor in export mode
        processor = EmailProcessor(config, export_mode=True)
        
        # Connect to Gmail
        logger.info("Connecting to Gmail...")
        processor.connect_gmail()
        
        if args.list_mailboxes:
            # List mailboxes
            mailboxes = processor.list_mailboxes()
            print("\nAvailable mailboxes:")
            for mailbox in mailboxes:
                print(f"  - {mailbox}")
        
        elif args.mailbox_info:
            # Get mailbox info
            info = processor.get_mailbox_info(args.mailbox_info)
            print(f"\nMailbox: {info['name']}")
            print(f"  Total messages: {info['total_messages']}")
            print(f"  Unread messages: {info['unread_messages']}")
            print(f"  Read messages: {info['read_messages']}")
        
        else:
            # Process batch
            logger.info(f"Processing {args.limit} emails from {args.mailbox}")
            results = processor.process_batch(
                mailbox=args.mailbox,
                limit=args.limit
            )
            
            print(f"\nProcessing Results:")
            print(f"  Mailbox: {results['mailbox']}")
            print(f"  Emails found: {results['total_found']}")
            print(f"  Emails processed: {results['total_processed']}")
            
            if results['export_file']:
                print(f"  Exported to: {results['export_file']}")
            
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")
                for error in results['errors']:
                    print(f"    - {error}")
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        return 1
    
    finally:
        if 'processor' in locals():
            processor.close()
    
    return 0

if __name__ == '__main__':
    exit(main())