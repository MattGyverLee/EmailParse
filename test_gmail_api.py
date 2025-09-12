#!/usr/bin/env python3
"""
Test OAuth2 tokens with Gmail API (instead of IMAP) to verify tokens work
"""

import sys
import os
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("[TEST] Testing OAuth2 tokens with Gmail API...")
    
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
        
        print(f"[TOKENS] Access token: {oauth.access_token[:30]}...")
        
        # Test Gmail API access
        print("[API] Testing Gmail API access...")
        
        headers = {
            'Authorization': f'Bearer {oauth.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Try to get user profile
        profile_url = 'https://gmail.googleapis.com/gmail/v1/users/me/profile'
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            profile = response.json()
            print(f"[SUCCESS] Gmail API access works!")
            print(f"[PROFILE] Email: {profile.get('emailAddress')}")
            print(f"[PROFILE] Messages Total: {profile.get('messagesTotal')}")
            print(f"[PROFILE] Threads Total: {profile.get('threadsTotal')}")
            
            # Try to list a few messages
            messages_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5'
            msg_response = requests.get(messages_url, headers=headers, timeout=10)
            
            if msg_response.status_code == 200:
                messages = msg_response.json()
                print(f"[MESSAGES] Found {len(messages.get('messages', []))} messages")
                print("[SUCCESS] Gmail API authentication is working correctly!")
                print("\n[ISSUE] The problem is likely with IMAP XOAUTH2 format, not the tokens.")
            else:
                print(f"[WARNING] Could not list messages: {msg_response.status_code}")
        
        elif response.status_code == 401:
            print("[ERROR] Token is invalid or expired")
            print("[INFO] Try refreshing the token...")
            
            if oauth.refresh_token:
                success = oauth._refresh_access_token()
                if success:
                    oauth._save_tokens()
                    print("[SUCCESS] Token refreshed, try running again")
                else:
                    print("[ERROR] Token refresh failed")
            else:
                print("[ERROR] No refresh token available")
        
        else:
            print(f"[ERROR] Gmail API access failed: {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())