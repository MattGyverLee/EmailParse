#!/usr/bin/env python3
"""
Exchange authorization code for OAuth2 tokens and fetch emails
Usage: python run_oauth.py "YOUR_AUTH_CODE_HERE"
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_oauth.py \"YOUR_AUTH_CODE_HERE\"")
        return 1
    
    auth_code = sys.argv[1].strip()
    
    print("[OAUTH] EmailParse OAuth2 Token Exchange & Email Fetch")
    print("=" * 60)
    print(f"[INFO] Using authorization code: {auth_code[:20]}...")
    
    try:
        from emailparse.config import Config
        from emailparse.gmail_oauth import GmailOAuth
        
        # Load config
        config = Config("config/config_v1.yaml")
        gmail_config = config.get_gmail_config()
        auth_config = gmail_config.get('auth', {})
        oauth_config = auth_config.get('oauth2', {})
        
        # Create OAuth handler
        oauth = GmailOAuth(
            client_id=oauth_config.get('client_id'),
            client_secret=oauth_config.get('client_secret'),
            token_file=oauth_config.get('token_file', 'gmail_tokens.json')
        )
        
        print("[EXCHANGE] Exchanging authorization code for tokens...")
        
        # Exchange the authorization code for tokens
        oauth._exchange_code_for_tokens(auth_code)
        oauth._save_tokens()
        
        print(f"[SUCCESS] OAuth2 tokens obtained and saved!")
        print(f"[INFO] Access token: {oauth.access_token[:30]}...")
        print(f"[INFO] Refresh token: {'YES' if oauth.refresh_token else 'NO'}")
        
        # Now fetch emails
        print(f"\n[GMAIL] Connecting to Gmail and fetching emails...")
        
        from emailparse.gmail_client import GmailClient
        from emailparse.markdown_exporter import MarkdownExporter
        
        # Create Gmail client
        client = GmailClient(config)
        
        print("[CONNECT] Connecting to Gmail IMAP...")
        client.connect()
        
        print("[AUTH] Authenticating with OAuth2 tokens...")
        client.authenticate()
        
        print("[MAILBOX] Selecting INBOX...")
        client.select_mailbox("INBOX")
        
        print("[SEARCH] Searching for 5 most recent emails...")
        uids = client.search_emails(limit=5)
        
        print(f"[FOUND] Found {len(uids)} emails")
        
        if not uids:
            print("[INFO] No emails found in INBOX")
            client.close()
            return 0
        
        print("[FETCH] Fetching email details...")
        emails = client.fetch_emails(uids)
        
        print(f"[SUCCESS] Retrieved {len(emails)} emails!")
        
        # Display email summaries
        print(f"\n{'='*60}")
        print("EMAIL SUMMARIES:")
        print('='*60)
        
        for i, email in enumerate(emails, 1):
            print(f"\n--- Email {i} (UID: {email.get('uid')}) ---")
            print(f"From: {email.get('from', 'Unknown')}")
            print(f"Subject: {email.get('subject', 'No subject')}")
            print(f"Date: {email.get('date', 'Unknown')}")
            print(f"Size: {email.get('size', 0)} bytes")
            body_preview = email.get('body', '')[:150].replace('\n', ' ').replace('\r', '')
            print(f"Preview: {body_preview}{'...' if len(body_preview) >= 150 else ''}")
        
        # Export to markdown
        print(f"\n{'='*60}")
        print("EXPORTING TO MARKDOWN:")
        print('='*60)
        
        exporter = MarkdownExporter("email_exports")
        
        # Create batch export
        batch_file = exporter.export_batch(emails, "oauth_test_batch")
        print(f"[BATCH] All emails: {batch_file}")
        
        # Create individual exports
        for i, email in enumerate(emails, 1):
            filename = f"email_{i}_{email.get('uid', 'unknown')}"
            individual_file = exporter.export_email(email, filename)
            print(f"[INDIVIDUAL] Email {i}: {individual_file}")
        
        # Create index
        index_file = exporter.create_index_file(emails, "OAuth Test Export")
        print(f"[INDEX] Email index: {index_file}")
        
        client.close()
        
        print(f"\n{'='*60}")
        print(f"[COMPLETE] Successfully processed {len(emails)} emails!")
        print(f"[FILES] Check the 'email_exports/' folder for markdown files")
        print(f"[TOKENS] OAuth2 tokens saved to 'gmail_tokens.json' for future use")
        print('='*60)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())