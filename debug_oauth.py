#!/usr/bin/env python3
"""
Debug OAuth2 setup - helps identify configuration issues
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[DEBUG] EmailParse OAuth2 Debug")
    print("=" * 50)
    
    # Check config file
    from emailparse.config import Config
    
    try:
        config = Config("config/config_v1.yaml")
        gmail_config = config.get_gmail_config()
        auth_config = gmail_config.get('auth', {})
        oauth_config = auth_config.get('oauth2', {})
        
        print(f"[CONFIG] Gmail user: {gmail_config.get('user')}")
        print(f"[CONFIG] Auth method: {auth_config.get('method')}")
        print(f"[CONFIG] Client ID: {oauth_config.get('client_id', 'NOT SET')[:20]}...")
        print(f"[CONFIG] Client Secret: {'SET' if oauth_config.get('client_secret') else 'NOT SET'}")
        print(f"[CONFIG] Token file: {oauth_config.get('token_file', 'gmail_tokens.json')}")
        
    except Exception as e:
        print(f"[ERROR] Config error: {e}")
        return 1
    
    # Test OAuth setup
    print("\n[OAUTH] Testing OAuth2 configuration...")
    
    try:
        from emailparse.gmail_oauth import GmailOAuth
        
        oauth = GmailOAuth(
            client_id=oauth_config.get('client_id'),
            client_secret=oauth_config.get('client_secret'),
            token_file=oauth_config.get('token_file', 'gmail_tokens.json')
        )
        
        print(f"[OAUTH] Redirect URI: {oauth.redirect_uri}")
        print(f"[OAUTH] Token URL: {oauth.token_url}")
        print(f"[OAUTH] Auth URL: {oauth.auth_url}")
        
        print("\n[INSTRUCTIONS] Make sure your Google Cloud Console OAuth2 client has:")
        print(f"1. Type: Desktop application")
        print(f"2. Authorized redirect URI: {oauth.redirect_uri}")
        print(f"3. Scopes enabled: Gmail API")
        
        # Check if tokens exist
        token_file = Path(oauth_config.get('token_file', 'gmail_tokens.json'))
        if token_file.exists():
            print(f"\n[TOKENS] Found existing token file: {token_file}")
            import json
            try:
                with open(token_file, 'r') as f:
                    tokens = json.load(f)
                print(f"[TOKENS] Has access token: {'access_token' in tokens}")
                print(f"[TOKENS] Has refresh token: {'refresh_token' in tokens}")
                if 'expires_at' in tokens:
                    import time
                    expired = tokens['expires_at'] < time.time()
                    print(f"[TOKENS] Access token expired: {expired}")
            except Exception as e:
                print(f"[TOKENS] Error reading tokens: {e}")
        else:
            print(f"\n[TOKENS] No existing token file found")
            
        return 0
        
    except Exception as e:
        print(f"[ERROR] OAuth setup error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())