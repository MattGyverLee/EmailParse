#!/usr/bin/env python3
"""
Fetch and export emails using Gmail API (more reliable than IMAP)
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[EMAILPARSE] Starting email processing with Gmail API...")
    
    try:
        from emailparse.config import Config
        from emailparse.gmail_api_client import GmailAPIClient
        from emailparse.markdown_exporter import MarkdownExporter
        
        # Load config
        config = Config("config/config_v1.yaml")
        
        print("[AUTH] Authenticating with Gmail API...")
        client = GmailAPIClient(config)
        client.authenticate()
        
        # Get profile info
        print("[PROFILE] Getting Gmail profile...")
        profile = client.get_profile()
        print(f"[INFO] Account: {profile.get('emailAddress')}")
        print(f"[INFO] Total messages: {profile.get('messagesTotal'):,}")
        print(f"[INFO] Total threads: {profile.get('threadsTotal'):,}")
        
        print(f"\\n[SEARCH] Searching for 5 most recent emails...")
        message_ids = client.search_emails(limit=5)
        
        print(f"[FOUND] Found {len(message_ids)} emails to process")
        
        if not message_ids:
            print("[INFO] No emails found")
            return 0
        
        print("[FETCH] Fetching email details...")
        emails = client.fetch_emails(message_ids)
        
        print(f"[SUCCESS] Retrieved {len(emails)} emails!")
        
        # Display email summaries
        print(f"\\n{'='*60}")
        print("EMAIL SUMMARIES:")
        print('='*60)
        
        for i, email in enumerate(emails, 1):
            print(f"\\n--- Email {i} (ID: {email.get('uid', 'unknown')[:10]}...) ---")
            # Handle encoding issues for console display
            try:
                print(f"From: {email.get('from', 'Unknown')}")
                print(f"Subject: {email.get('subject', 'No subject')}")
            except UnicodeEncodeError:
                print(f"From: {email.get('from', 'Unknown').encode('ascii', errors='replace').decode('ascii')}")
                print(f"Subject: {email.get('subject', 'No subject').encode('ascii', errors='replace').decode('ascii')}")
            print(f"Date: {email.get('date', 'Unknown')}")
            print(f"Size: {email.get('size', 0):,} bytes")
            
            # Show labels (Gmail folders/labels)
            labels = email.get('labels', [])
            if labels:
                # Filter out system labels for cleaner display
                user_labels = [label for label in labels if not label.startswith('Label_')]
                if user_labels:
                    print(f"Labels: {', '.join(user_labels)}")
            
            body_preview = email.get('body', '')[:200].replace('\\n', ' ').replace('\\r', '')
            print(f"Preview: {body_preview}{'...' if len(body_preview) >= 200 else ''}")
        
        # Export to markdown
        print(f"\\n{'='*60}")
        print("EXPORTING TO MARKDOWN:")
        print('='*60)
        
        exporter = MarkdownExporter("email_exports")
        
        # Create batch export
        batch_file = exporter.export_batch(emails, "gmail_api_export")
        print(f"[BATCH] All emails: {batch_file}")
        
        # Create individual exports
        for i, email in enumerate(emails, 1):
            filename = f"email_{i}_{email.get('uid', 'unknown')[:10]}"
            individual_file = exporter.export_email(email, filename)
            print(f"[INDIVIDUAL] Email {i}: {individual_file}")
        
        # Create index
        index_file = exporter.create_index_file(emails, "Gmail API Export")
        print(f"[INDEX] Email index: {index_file}")
        
        print(f"\\n{'='*60}")
        print(f"[COMPLETE] Successfully processed {len(emails)} emails!")
        print(f"[FILES] Check the 'email_exports/' folder for markdown files")
        print(f"[SUCCESS] Gmail API authentication worked perfectly!")
        print('='*60)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Email processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())