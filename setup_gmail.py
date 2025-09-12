#!/usr/bin/env python3
"""
EmailParse Gmail Setup Tool

Interactive setup for Gmail OAuth2 authentication.
Run this to set up your Gmail credentials for EmailParse.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main setup function"""
    print("[SETUP] EmailParse Gmail Setup")
    print("=" * 40)
    print()
    print("This tool will help you set up Gmail access for EmailParse.")
    print("You'll need to:")
    print("1. Create OAuth credentials in Google Cloud Console (if you haven't already)")
    print("2. Authenticate with your Gmail account") 
    print("3. Test the connection")
    print()
    
    # Check if we have a config file
    config_template = Path("config/config_v1.yaml.template")
    config_file = Path("config/config_v1.yaml")
    
    if not config_file.exists():
        if config_template.exists():
            print("[INFO] Creating configuration file...")
            import shutil
            shutil.copy(config_template, config_file)
            print(f"[SUCCESS] Created {config_file} from template")
        else:
            print(f"[ERROR] Configuration template not found: {config_template}")
            return 1
    
    # Get user's Gmail address
    gmail_address = input("\n[INPUT] Enter your Gmail address: ").strip()
    if not gmail_address or '@' not in gmail_address:
        print("[ERROR] Please enter a valid Gmail address")
        return 1
    
    # Update config file with Gmail address
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['gmail']['user'] = gmail_address
        config['gmail']['auth']['method'] = 'oauth2'
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"[SUCCESS] Updated config with Gmail address: {gmail_address}")
        
    except Exception as e:
        print(f"[WARNING] Could not update config file: {e}")
        print("Please manually edit config/config_v1.yaml with your Gmail address")
    
    # Start OAuth setup
    print("\n[OAUTH] Starting OAuth2 setup...")
    print("This will open your browser to authenticate with Gmail.")
    
    try:
        from emailparse.gmail_oauth import interactive_gmail_setup
        
        oauth = interactive_gmail_setup()
        if not oauth:
            print("[ERROR] OAuth setup failed or was cancelled")
            return 1
        
        print("\n[TEST] Testing Gmail connection...")
        
        # Test the connection
        from emailparse.config import Config
        from emailparse.gmail_client import GmailClient
        
        config = Config(str(config_file))
        client = GmailClient(config)
        
        print("Connecting to Gmail...")
        client.connect()
        
        print("Authenticating...")
        client.authenticate()
        
        print("Selecting INBOX...")
        client.select_mailbox("INBOX")
        
        print("Testing email search...")
        uids = client.search_emails(limit=3)
        
        client.close()
        
        print(f"[SUCCESS] Success! Found {len(uids)} emails in your inbox")
        print("\n[COMPLETE] Gmail setup complete!")
        print("\nYou can now run EmailParse:")
        print("  python src/emailparse/email_processor_v1.py --limit 10")
        print("\nYour emails will be exported to the email_exports/ folder.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n[CANCELLED] Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        print("\nFor troubleshooting help, see OAUTH_SETUP.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())