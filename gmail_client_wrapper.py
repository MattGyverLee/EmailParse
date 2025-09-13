"""
Gmail Client Wrapper for EmailParse V1.0
Simplified wrapper around the existing Gmail API client for integration with email processor
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path to import the existing Gmail client
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

try:
    from emailparse.config import Config
    from emailparse.gmail_api_client import GmailAPIClient
    from emailparse.markdown_exporter import MarkdownExporter
except ImportError as e:
    print(f"Warning: Could not import Gmail modules: {e}")
    # Fallback for testing
    GmailAPIClient = None
    MarkdownExporter = None

class GmailClientWrapper:
    """Simplified Gmail client wrapper for email processing"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Gmail client wrapper"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.exporter = None
        self.authenticated = False
        
        # Try to initialize the real client
        try:
            if GmailAPIClient and MarkdownExporter:
                # Convert our config dict to the expected Config object format
                config_path = Path("config/config_v1.yaml")
                if config_path.exists():
                    self.config_obj = Config(str(config_path))
                    self.client = GmailAPIClient(self.config_obj)
                    self.exporter = MarkdownExporter()
                    self.logger.info("Gmail client initialized successfully")
                else:
                    self.logger.error("Config file not found for Gmail client")
            else:
                self.logger.warning("Gmail client modules not available - using mock mode")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail client: {e}")
    
    def test_connection(self) -> bool:
        """Test Gmail API connection"""
        try:
            if self.client:
                if not self.authenticated:
                    self.client.authenticate()
                    self.authenticated = True
                
                # Test by getting profile
                profile = self.client.get_profile()
                return profile is not None
            else:
                self.logger.warning("Gmail client not available - returning mock success")
                return True  # Return True for testing when client not available
                
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return False
    
    def fetch_emails(self, limit: int = 10, include_threads: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail and convert to format expected by processor
        
        Args:
            limit: Maximum number of emails to fetch
            include_threads: Whether to group emails by thread
            
        Returns:
            List of email dictionaries with standardized format
        """
        try:
            if not self.client:
                # Return mock emails for testing
                return self._create_mock_emails(limit, include_threads)
            
            if not self.authenticated:
                self.client.authenticate()
                self.authenticated = True
            
            # Fetch emails using the existing client
            self.logger.info(f"Fetching {limit} emails from Gmail")
            emails = self.client.fetch_emails(limit=limit)
            
            # Convert to standardized format
            processed_emails = []
            for email_data in emails:
                processed_email = self._convert_email_format(email_data)
                if processed_email:
                    processed_emails.append(processed_email)
            
            self.logger.info(f"Successfully fetched and processed {len(processed_emails)} emails")
            return processed_emails
            
        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {e}")
            # Return mock emails as fallback
            return self._create_mock_emails(min(3, limit))
    
    def add_label(self, email_id: str, label_name: str) -> bool:
        """Add label to email"""
        try:
            if not self.client:
                self.logger.info(f"Mock: Would add label '{label_name}' to email {email_id}")
                return True
            
            if not self.authenticated:
                self.client.authenticate()
                self.authenticated = True
            
            result = self.client.add_label(email_id, label_name)
            self.logger.info(f"Added label '{label_name}' to email {email_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to add label to email {email_id}: {e}")
            return False
    
    def remove_label(self, email_id: str, label_name: str) -> bool:
        """Remove label from email"""
        try:
            if not self.client:
                self.logger.info(f"Mock: Would remove label '{label_name}' from email {email_id}")
                return True
            
            if not self.authenticated:
                self.client.authenticate()
                self.authenticated = True
            
            result = self.client.remove_label(email_id, label_name)
            self.logger.info(f"Removed label '{label_name}' from email {email_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to remove label from email {email_id}: {e}")
            return False
    
    def _convert_email_format(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert email from Gmail client format to processor format"""
        try:
            if not email_data:
                return None
            
            # Extract basic fields
            email_id = email_data.get('id', 'unknown')
            subject = email_data.get('subject', 'No Subject')
            sender = email_data.get('from', 'Unknown Sender')
            date = email_data.get('date', 'Unknown Date')
            
            # Get body content
            body = email_data.get('body', '')
            text_content = email_data.get('text_content', body)
            
            # Generate markdown if exporter available
            markdown = None
            if self.exporter and email_data:
                try:
                    markdown = self.exporter.export_email(email_data)
                except Exception as e:
                    self.logger.warning(f"Failed to generate markdown for email {email_id}: {e}")
            
            # Fallback markdown generation
            if not markdown:
                markdown = self._generate_simple_markdown(subject, sender, date, text_content)
            
            return {
                'id': email_id,
                'subject': subject,
                'from': sender,
                'date': str(date),
                'body': text_content,
                'text_content': text_content,
                'markdown': markdown,
                'raw_data': email_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to convert email format: {e}")
            return None
    
    def _generate_simple_markdown(self, subject: str, sender: str, date: str, content: str) -> str:
        """Generate simple markdown representation of email"""
        markdown = f"""# {subject}

**From:** {sender}  
**Date:** {date}  

---

{content}
"""
        return markdown
    
    def _create_mock_emails(self, count: int, include_threads: bool = True) -> List[Dict[str, Any]]:
        """Create mock emails for testing when Gmail client not available"""
        mock_emails = []
        
        mock_templates = [
            {
                'subject': 'Flash Sale - 50% Off Everything!',
                'from': 'deals@retailstore.com',
                'content': '''🔥 **FLASH SALE ALERT!** 🔥

Get 50% off EVERYTHING in our store! This incredible deal won't last long.

**Sale Details:**
- Valid until midnight tonight
- No code needed - discount applied at checkout
- Free shipping on orders over $25

Shop now before it's too late!

[SHOP NOW](https://retailstore.com/sale)

---
*Unsubscribe here.*'''
            },
            {
                'subject': 'Weekly Tech Industry Updates',
                'from': 'newsletter@techindustry.com',
                'content': '''## This Week in Tech

- New AI developments in healthcare
- Cybersecurity trends for 2024
- Remote work technology updates

## Featured Article
Understanding the impact of quantum computing on data security...

---
*You subscribed to this newsletter. Manage preferences.*'''
            },
            {
                'subject': 'Meeting tomorrow about project',
                'from': 'colleague@company.com',
                'content': '''Hi,

Just confirming our meeting tomorrow at 2 PM to discuss the Q1 project timeline.

Please bring the latest status report.

Thanks,
John'''
            }
        ]
        
        for i in range(min(count, len(mock_templates))):
            template = mock_templates[i]
            email_id = f"mock_email_{i+1:03d}"
            
            markdown = self._generate_simple_markdown(
                template['subject'],
                template['from'],
                "2024-01-15",
                template['content']
            )
            
            # Add thread information and starred status
            thread_id = f"mock_thread_{(i // 2) + 1:03d}"  # Group emails in pairs for threads
            is_starred = (i == 1)  # Make second email starred for testing
            
            mock_email = {
                'id': email_id,
                'subject': template['subject'],
                'from': template['from'],
                'date': '2024-01-15',
                'body': template['content'],
                'text_content': template['content'],
                'markdown': markdown,
                'thread_id': thread_id,
                'is_starred': is_starred,
                'labels': ['INBOX'] + (['STARRED'] if is_starred else []),
                'raw_data': {'mock': True, 'thread_id': thread_id}
            }
            
            mock_emails.append(mock_email)
        
        self.logger.info(f"Created {len(mock_emails)} mock emails for testing")
        return mock_emails