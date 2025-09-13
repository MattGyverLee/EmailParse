#!/usr/bin/env python3
"""
Debug OAuth2 authentication string
"""

import sys
import os
import base64

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[DEBUG] OAuth2 Authentication Debug")
    print("=" * 50)
    
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
        if oauth._load_tokens():
            print(f"[TOKENS] Loaded existing tokens")
            print(f"[TOKENS] Access token: {oauth.access_token[:30]}...")
            print(f"[TOKENS] Refresh token: {'YES' if oauth.refresh_token else 'NO'}")
            
            # Check if token is valid
            is_valid = oauth._is_token_valid()
            print(f"[TOKENS] Token valid: {is_valid}")
            
            if not is_valid and oauth.refresh_token:
                print("[REFRESH] Refreshing access token...")
                refreshed = oauth._refresh_access_token()
                print(f"[REFRESH] Refresh successful: {refreshed}")
            
            # Create XOAUTH2 string
            user_email = gmail_config.get('user')
            print(f"[AUTH] Creating XOAUTH2 string for: {user_email}")
            
            auth_string = oauth.create_xoauth2_string(user_email)
            print(f"[AUTH] XOAUTH2 string length: {len(auth_string)}")
            print(f"[AUTH] XOAUTH2 string (first 50 chars): {auth_string[:50]}...")
            
            # Decode to see the actual content
            decoded = base64.b64decode(auth_string).decode('utf-8')
            print(f"[AUTH] Decoded content: {decoded[:100]}...")
            
            # Test basic IMAP connection without auth
            print(f"\n[IMAP] Testing basic IMAP connection...")
            from emailparse.gmail_client import GmailClient
            
            client = GmailClient(config)
            client.connect()
            print(f"[IMAP] Connected successfully")
            
            # Try manual authentication
            print(f"[IMAP] Attempting XOAUTH2 authentication...")
            
            try:
                result = client.connection.authenticate('XOAUTH2', lambda x: auth_string.encode())
                print(f"[IMAP] Auth result: {result}")
            except Exception as auth_error:
                print(f"[ERROR] Auth failed: {auth_error}")
                
                # Try the alternative format
                print(f"[RETRY] Trying alternative XOAUTH2 format...")
                alt_auth_string = f'user={user_email}\x01auth=Bearer {oauth.access_token}\x01\x01'
                alt_b64 = base64.b64encode(alt_auth_string.encode()).decode()
                
                try:
                    result = client.connection.authenticate('XOAUTH2', lambda x: alt_b64)
                    print(f"[RETRY] Alternative format result: {result}")
                except Exception as alt_error:
                    print(f"[RETRY] Alternative format also failed: {alt_error}")
            
            client.close()
            
        else:
            print("[ERROR] No tokens found or failed to load")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())