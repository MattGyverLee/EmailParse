"""Interactive OAuth2 authentication for Gmail IMAP access"""

import os
import json
import time
import base64
import secrets
import hashlib
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional, Tuple
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GmailOAuthError(Exception):
    """OAuth authentication errors"""
    pass

class GmailOAuth:
    """Interactive OAuth2 authentication for Gmail"""
    
    def __init__(self, client_id: str = None, client_secret: str = None, token_file: str = None):
        """
        Initialize Gmail OAuth handler
        
        Args:
            client_id: OAuth client ID (will prompt if not provided)
            client_secret: OAuth client secret (will prompt if not provided) 
            token_file: Path to store/load tokens
        """
        # Default Gmail IMAP scopes
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',  # Read access
            'https://mail.google.com/'  # Full IMAP access (unfortunately needed for IMAP)
        ]
        
        # OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        # Use OOB flow for desktop applications
        self.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        
        # Credentials
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file or "gmail_tokens.json"
        
        # Current tokens
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
    
    def setup_oauth_client(self) -> Tuple[str, str]:
        """
        Interactive setup of OAuth client credentials
        
        Returns:
            Tuple of (client_id, client_secret)
        """
        print("\n[SETUP] Gmail OAuth Setup Required")
        print("=" * 50)
        print("\nTo use EmailParse with Gmail, you need to create OAuth credentials.")
        print("This is a one-time setup that allows secure access to your Gmail account.")
        print("\n[STEPS] Steps to create credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable the Gmail API")
        print("4. Go to Credentials > Create Credentials > OAuth 2.0 Client IDs")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file or copy the client ID and secret")
        
        print("\n" + "=" * 50)
        
        if not self.client_id:
            self.client_id = input("\n[INPUT] Enter your OAuth Client ID: ").strip()
            if not self.client_id:
                raise GmailOAuthError("Client ID is required")
        
        if not self.client_secret:
            self.client_secret = input("[INPUT] Enter your OAuth Client Secret: ").strip()
            if not self.client_secret:
                raise GmailOAuthError("Client Secret is required")
        
        # Save credentials for future use
        self._save_oauth_config()
        
        return self.client_id, self.client_secret
    
    def _save_oauth_config(self):
        """Save OAuth configuration to file"""
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        oauth_config = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        config_file = config_dir / "gmail_oauth.json"
        with open(config_file, 'w') as f:
            json.dump(oauth_config, f, indent=2)
        
        logger.info(f"OAuth configuration saved to {config_file}")
    
    def _load_oauth_config(self):
        """Load OAuth configuration from file"""
        config_file = Path("config/gmail_oauth.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.client_id = config.get('client_id')
                self.client_secret = config.get('client_secret')
                return True
        return False
    
    def authenticate(self, force_reauth: bool = False) -> str:
        """
        Complete OAuth authentication flow
        
        Args:
            force_reauth: Force new authentication even if tokens exist
            
        Returns:
            Access token for IMAP authentication
        """
        # Load existing OAuth config if available
        if not self.client_id or not self.client_secret:
            if not self._load_oauth_config():
                self.setup_oauth_client()
        
        # Try to load and refresh existing tokens
        if not force_reauth and self._load_tokens():
            if self._is_token_valid():
                return self.access_token
            elif self.refresh_token:
                if self._refresh_access_token():
                    return self.access_token
        
        # Perform new authentication flow
        print("\n[AUTH] Starting Gmail OAuth authentication...")
        print("Your browser will open to complete the login process.")
        
        # Start OAuth flow
        auth_code = self._get_authorization_code()
        self._exchange_code_for_tokens(auth_code)
        self._save_tokens()
        
        print("[SUCCESS] Authentication successful!")
        return self.access_token
    
    def _get_authorization_code(self) -> str:
        """Get authorization code via OOB (out-of-band) flow for desktop apps"""
        # Build authorization URL for OOB flow (no PKCE needed for OOB)
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent'  # Force consent screen for refresh token
        }
        
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(params)}"
        
        print(f"\n[BROWSER] Opening browser for authentication...")
        print(f"If the browser doesn't open automatically, visit:")
        print(f"{auth_url}\n")
        
        # Try to open browser
        try:
            webbrowser.open(auth_url)
        except Exception:
            print("[WARNING] Could not open browser automatically.")
        
        print("After authentication, you'll be shown an authorization code.")
        print("Copy the authorization code and paste it below:")
        
        # Get authorization code from user input
        while True:
            try:
                auth_code = input("\n[INPUT] Enter authorization code: ").strip()
                if auth_code:
                    return auth_code
                else:
                    print("[ERROR] Please enter a valid authorization code.")
            except (EOFError, KeyboardInterrupt):
                raise GmailOAuthError("Authentication cancelled by user")
    
    def _start_callback_server(self, code_verifier: str) -> str:
        """Start local server to handle OAuth callback"""
        import http.server
        import socketserver
        from urllib.parse import parse_qs
        import threading
        
        auth_code = None
        server_error = None
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code, server_error
                
                if self.path.startswith('/oauth/callback'):
                    try:
                        # Parse the authorization code from URL
                        query = urllib.parse.urlparse(self.path).query
                        params = parse_qs(query)
                        
                        if 'code' in params:
                            auth_code = params['code'][0]
                            response_html = """
                            <html><head><title>EmailParse Authentication</title></head>
                            <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
                                <h1 style="color: green;">[SUCCESS] Authentication Successful!</h1>
                                <p>You can now close this browser window and return to EmailParse.</p>
                                <p style="color: #666;">EmailParse is now authorized to access your Gmail account.</p>
                            </body></html>
                            """
                        elif 'error' in params:
                            error = params['error'][0]
                            server_error = f"OAuth error: {error}"
                            response_html = f"""
                            <html><head><title>EmailParse Authentication Error</title></head>
                            <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
                                <h1 style="color: red;">[ERROR] Authentication Failed</h1>
                                <p>Error: {error}</p>
                                <p>Please close this window and try again.</p>
                            </body></html>
                            """
                        else:
                            server_error = "No authorization code received"
                            response_html = """
                            <html><head><title>EmailParse Authentication Error</title></head>
                            <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
                                <h1 style="color: red;">[ERROR] Authentication Error</h1>
                                <p>No authorization code received. Please try again.</p>
                            </body></html>
                            """
                        
                        # Send response
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(response_html.encode('utf-8'))
                        
                    except Exception as e:
                        server_error = f"Callback error: {e}"
                        self.send_response(500)
                        self.end_headers()
                
                # Shutdown server after handling request
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            
            def log_message(self, format, *args):
                pass  # Suppress server logs
        
        # Start server
        port = 8080
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                with socketserver.TCPServer(("localhost", port), CallbackHandler) as httpd:
                    print(f"[WAITING] Waiting for authentication (listening on port {port})...")
                    httpd.timeout = 300  # 5 minute timeout
                    httpd.handle_request()
                    break
            except OSError as e:
                if "Address already in use" in str(e) and attempt < max_attempts - 1:
                    port += 1
                    continue
                else:
                    raise GmailOAuthError(f"Could not start callback server: {e}")
        
        if server_error:
            raise GmailOAuthError(server_error)
        
        if not auth_code:
            raise GmailOAuthError("Authentication timeout or cancelled")
        
        return auth_code
    
    def _exchange_code_for_tokens(self, auth_code: str):
        """Exchange authorization code for access and refresh tokens"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            tokens = response.json()
            
            self.access_token = tokens['access_token']
            self.refresh_token = tokens.get('refresh_token')  # May not always be present
            
            # Calculate expiration time
            expires_in = tokens.get('expires_in', 3600)
            self.expires_at = time.time() + expires_in
            
            if not self.refresh_token:
                logger.warning("No refresh token received - you may need to re-authenticate more frequently")
            
        except requests.RequestException as e:
            raise GmailOAuthError(f"Failed to exchange authorization code: {e}")
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens['access_token']
            
            # Update expiration time
            expires_in = tokens.get('expires_in', 3600)
            self.expires_at = time.time() + expires_in
            
            # Save updated tokens
            self._save_tokens()
            
            logger.info("Access token refreshed successfully")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if current access token is valid"""
        if not self.access_token or not self.expires_at:
            return False
        
        # Check if token expires in the next 5 minutes
        return time.time() < (self.expires_at - 300)
    
    def _load_tokens(self) -> bool:
        """Load tokens from file"""
        if not os.path.exists(self.token_file):
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
            
            self.access_token = tokens.get('access_token')
            self.refresh_token = tokens.get('refresh_token') 
            self.expires_at = tokens.get('expires_at')
            
            return bool(self.access_token)
            
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load tokens from {self.token_file}: {e}")
            return False
    
    def _save_tokens(self):
        """Save tokens to file"""
        tokens = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at,
            'created_at': time.time()
        }
        
        try:
            # Create directory if it doesn't exist
            token_dir = os.path.dirname(self.token_file)
            if token_dir:  # Only create directory if there's a directory path
                os.makedirs(token_dir, exist_ok=True)
            
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Set restrictive permissions on token file
            os.chmod(self.token_file, 0o600)
            
            logger.info(f"Tokens saved to {self.token_file}")
            
        except OSError as e:
            logger.error(f"Could not save tokens to {self.token_file}: {e}")
    
    def create_xoauth2_string(self, email: str) -> str:
        """
        Create XOAUTH2 string for IMAP authentication
        
        Args:
            email: Gmail email address
            
        Returns:
            Base64-encoded XOAUTH2 string for IMAP
        """
        if not self.access_token:
            raise GmailOAuthError("No access token available - authenticate first")
        
        # Ensure token is fresh
        if not self._is_token_valid():
            if self.refresh_token:
                if not self._refresh_access_token():
                    raise GmailOAuthError("Could not refresh access token - re-authentication required")
            else:
                raise GmailOAuthError("Access token expired and no refresh token available")
        
        # Create XOAUTH2 string (exact format for Gmail IMAP)
        auth_string = f'user={email}\x01auth=Bearer {self.access_token}\x01\x01'
        return base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    
    def revoke_tokens(self):
        """Revoke tokens and clean up"""
        if self.access_token:
            try:
                # Revoke the token
                revoke_url = "https://oauth2.googleapis.com/revoke"
                requests.post(revoke_url, data={'token': self.access_token}, timeout=10)
                logger.info("Tokens revoked successfully")
            except Exception as e:
                logger.warning(f"Could not revoke tokens: {e}")
        
        # Clear tokens
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        
        # Remove token file
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
                logger.info(f"Token file {self.token_file} removed")
            except OSError as e:
                logger.warning(f"Could not remove token file: {e}")

def interactive_gmail_setup() -> GmailOAuth:
    """Interactive setup for Gmail OAuth"""
    print("\n[SETUP] EmailParse Gmail Setup")
    print("=" * 40)
    
    oauth = GmailOAuth()
    
    try:
        # Authenticate
        oauth.authenticate()
        return oauth
        
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Setup cancelled by user")
        return None
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        return None

if __name__ == "__main__":
    # Command line interface for testing
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            oauth = interactive_gmail_setup()
            if oauth:
                print("\n[SUCCESS] Gmail OAuth setup complete!")
                print("You can now use EmailParse to access your Gmail account.")
        elif sys.argv[1] == "revoke":
            oauth = GmailOAuth()
            oauth._load_tokens()
            oauth.revoke_tokens()
            print("[SUCCESS] Gmail access revoked and tokens removed.")
        else:
            print("Usage:")
            print("  python gmail_oauth.py setup   - Set up Gmail OAuth")
            print("  python gmail_oauth.py revoke  - Revoke access and remove tokens")
    else:
        print("EmailParse Gmail OAuth Helper")
        print("Usage:")
        print("  python gmail_oauth.py setup   - Set up Gmail OAuth")
        print("  python gmail_oauth.py revoke  - Revoke access and remove tokens")