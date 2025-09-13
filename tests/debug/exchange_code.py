#!/usr/bin/env python3
"""
Exchange authorization code for OAuth2 tokens
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[OAUTH] EmailParse OAuth2 Token Exchange")
    print("=" * 50)
    
    # Get authorization code from user
    auth_code = input("\nPaste your authorization code here: ").strip()
    
    if not auth_code:
        print("[ERROR] No authorization code provided")
        return 1
    
    print(f"[INFO] Received authorization code: {auth_code[:20]}...")
    
    try:
        from utils.config import Config
        from clients.gmail_oauth import GmailOAuth
        
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
        
        print(f"[SUCCESS] OAuth2 tokens obtained and saved to: {oauth.token_file}")
        print(f"[INFO] Access token: {oauth.access_token[:30]}...")
        print(f"[INFO] Refresh token: {'YES' if oauth.refresh_token else 'NO'}")
        
        # Now run the email fetch
        print(f"\n[FETCH] Now fetching emails...")
        
        from clients.gmail_client import GmailClient
        from utils.markdown_exporter import MarkdownExporter
        
        # Create Gmail client
        client = GmailClient(config)
        
        print("[CONNECT] Connecting to Gmail...")
        client.connect()
        
        print("[AUTH] Authenticating with OAuth2...")
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
            body_preview = email.get('body', '')[:100].replace('\n', ' ').replace('\r', '')
            print(f"Body: {body_preview}{'...' if len(body_preview) >= 100 else ''}")
        
        # Export to markdown
        print(f"\n[EXPORT] Exporting emails to markdown...")
        
        exporter = MarkdownExporter("email_exports")
        
        # Create batch export
        batch_file = exporter.export_batch(emails, "gmail_oauth_test")
        print(f"[SUCCESS] Emails exported to: {batch_file}")
        
        client.close()
        
        print(f"\n[COMPLETE] Successfully processed {len(emails)} emails!")
        print(f"[INFO] Check the 'email_exports' folder for markdown files")
        print(f"[INFO] OAuth2 tokens saved for future use")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())