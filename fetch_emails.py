#!/usr/bin/env python3
"""
Fetch and export emails using saved OAuth2 tokens
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[EMAILPARSE] Starting email processing with OAuth2...")
    
    try:
        from utils.config import Config
        from clients.gmail_client import GmailClient
        from utils.markdown_exporter import MarkdownExporter
        
        # Load config
        config = Config("config/config_v1.yaml")
        
        # Check if tokens exist
        token_file = Path("gmail_tokens.json")
        if token_file.exists():
            print("[INFO] Using saved OAuth2 tokens")
        else:
            print("[INFO] No saved tokens found. Will authenticate during connection.")
        
        # Create Gmail client
        client = GmailClient(config)
        
        print("[CONNECT] Connecting to Gmail IMAP...")
        client.connect()
        
        print("[AUTH] Authenticating with saved OAuth2 tokens...")
        client.authenticate()
        
        print("[MAILBOX] Selecting INBOX...")
        client.select_mailbox("INBOX")
        
        print("[SEARCH] Searching for recent emails (limit 5)...")
        uids = client.search_emails(limit=5)
        
        print(f"[FOUND] Found {len(uids)} emails to process")
        
        if not uids:
            print("[INFO] No emails found")
            client.close()
            return 0
        
        print("[FETCH] Fetching email details...")
        emails = client.fetch_emails(uids)
        
        print(f"[SUCCESS] Retrieved {len(emails)} emails!")
        
        # Display email info
        for i, email in enumerate(emails, 1):
            print(f"\n--- Email {i} ---")
            print(f"From: {email.get('from', 'Unknown')}")
            print(f"Subject: {email.get('subject', 'No subject')}")
            print(f"Date: {email.get('date', 'Unknown')}")
            print(f"Size: {email.get('size', 0)} bytes")
            body_preview = email.get('body', '')[:100].replace('\n', ' ').replace('\r', '')
            print(f"Body preview: {body_preview}{'...' if len(body_preview) >= 100 else ''}")
        
        # Export to markdown
        print(f"\n[EXPORT] Exporting emails to markdown...")
        
        exporter = MarkdownExporter("email_exports")
        
        # Create batch export
        batch_file = exporter.export_batch(emails, "gmail_batch_test")
        print(f"[SUCCESS] Emails exported to: {batch_file}")
        
        # Create individual exports
        for i, email in enumerate(emails, 1):
            filename = f"email_{i}_{email.get('uid', 'unknown')}"
            individual_file = exporter.export_email(email, filename)
            print(f"[EXPORT] Email {i} exported to: {individual_file}")
        
        # Create index
        index_file = exporter.create_index_file(emails, "Gmail Export Test")
        print(f"[INDEX] Created index file: {index_file}")
        
        client.close()
        
        print(f"\n[COMPLETE] Successfully processed {len(emails)} emails!")
        print(f"[INFO] Check the 'email_exports' folder for markdown files")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Email processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())