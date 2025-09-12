#!/usr/bin/env python3
"""
Force refresh access token and test Gmail connection
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[REFRESH] Force refreshing OAuth2 access token...")
    
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
        
        # Load existing tokens
        if not oauth._load_tokens():
            print("[ERROR] No tokens found")
            return 1
        
        print(f"[TOKENS] Current access token: {oauth.access_token[:30]}...")
        print(f"[TOKENS] Token valid: {oauth._is_token_valid()}")
        
        # Force refresh
        if oauth.refresh_token:
            print("[REFRESH] Forcing token refresh...")
            success = oauth._refresh_access_token()
            print(f"[REFRESH] Refresh successful: {success}")
            
            if success:
                oauth._save_tokens()
                print(f"[TOKENS] New access token: {oauth.access_token[:30]}...")
                
                # Now test Gmail connection
                print(f"\n[GMAIL] Testing Gmail connection with fresh token...")
                
                from emailparse.gmail_client import GmailClient
                
                client = GmailClient(config)
                
                try:
                    print("[CONNECT] Connecting to Gmail...")
                    client.connect()
                    
                    print("[AUTH] Authenticating...")
                    client.authenticate()
                    
                    print("[SUCCESS] Authentication successful!")
                    
                    print("[MAILBOX] Selecting INBOX...")
                    client.select_mailbox("INBOX")
                    
                    print("[SEARCH] Searching for emails...")
                    uids = client.search_emails(limit=3)
                    
                    print(f"[FOUND] Found {len(uids)} emails")
                    
                    client.close()
                    print("[COMPLETE] Gmail test successful!")
                    
                except Exception as e:
                    print(f"[ERROR] Gmail test failed: {e}")
                    if client.connection:
                        try:
                            client.close()
                        except:
                            pass
                    return 1
            else:
                print("[ERROR] Token refresh failed")
                return 1
        else:
            print("[ERROR] No refresh token available")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())