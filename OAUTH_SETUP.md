# Gmail OAuth2 Setup for EmailParse

EmailParse uses **interactive OAuth2** authentication to securely access your Gmail account via IMAP, just like a proper email client.

## Why OAuth2?

Google deprecated app passwords for Gmail. OAuth2 provides:
- **More secure** authentication
- **Granular permissions** (read-only access)
- **Token refresh** for long-term use
- **Same process as email clients** like Thunderbird, Outlook

## Quick Start

1. **Copy the config template:**
```bash
cp config/config_v1.yaml.template config/config_v1.yaml
```

2. **Edit config_v1.yaml:**
```yaml
gmail:
  user: "your-email@gmail.com"  # Your Gmail address
  auth:
    method: "oauth2"
```

3. **Run EmailParse - it will guide you through OAuth setup:**
```bash
python src/emailparse/email_processor_v1.py --limit 5
```

That's it! The first time you run EmailParse, it will:
- Guide you through creating OAuth credentials 
- Open your browser for Gmail login
- Save tokens for future use

## Detailed OAuth Setup

If you want to prepare OAuth credentials in advance:

### Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. **Enable the Gmail API**:
   - Go to "APIs & Services" → "Library"  
   - Search for "Gmail API"
   - Click "Enable"

4. **Create OAuth credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose **"Desktop application"**
   - Name it "EmailParse" 
   - Click "Create"

5. **Note your credentials**:
   - Client ID (looks like: `123456-abc.apps.googleusercontent.com`)
   - Client Secret (looks like: `GOCSPX-abcd1234...`)

### Step 2: Configure EmailParse

Edit `config/config_v1.yaml`:

```yaml
gmail:
  host: "imap.gmail.com"
  port: 993
  use_ssl: true
  user: "your-email@gmail.com"
  
  auth:
    method: "oauth2"
    oauth2:
      client_id: "your-client-id.apps.googleusercontent.com"
      client_secret: "your-client-secret"
      token_file: "gmail_tokens.json"
```

### Step 3: First Run

```bash
python src/emailparse/email_processor_v1.py --limit 5
```

EmailParse will:
1. **Open your browser** to Gmail OAuth consent screen
2. **Ask for permissions** (read Gmail via IMAP)
3. **Save refresh tokens** to `gmail_tokens.json`
4. **Connect and process emails**

## How It Works

1. **First Run**: Interactive OAuth flow (browser opens)
2. **Subsequent Runs**: Uses saved refresh token automatically
3. **Token Refresh**: Handles expired tokens transparently
4. **IMAP Auth**: Uses OAuth2 tokens with Gmail IMAP (just like Thunderbird)

## Troubleshooting

### "OAuth setup required" Error
Run the manual setup:
```bash
python src/emailparse/gmail_oauth.py setup
```

### "Authentication failed" Error
- Check your Gmail address in config
- Verify OAuth credentials are correct
- Try re-authentication:
```bash
python src/emailparse/gmail_oauth.py revoke
python src/emailparse/email_processor_v1.py --limit 5
```

### "Browser didn't open" 
The console will show the OAuth URL - copy and paste it into your browser manually.

### "No refresh token received"
This happens if you've already granted permission before. To fix:
1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Remove EmailParse/your app
3. Run setup again - make sure to see the consent screen

## Security Notes

- **Tokens stored locally**: `gmail_tokens.json` contains your refresh token
- **Read-only access**: EmailParse requests minimal required permissions
- **No passwords**: Your Gmail password is never stored or transmitted
- **Revoke anytime**: Remove access at [Google Account Permissions](https://myaccount.google.com/permissions)

## Advanced: Manual Token Management

### Revoke Access
```bash
python src/emailparse/gmail_oauth.py revoke
```

### Re-authenticate
```bash
rm gmail_tokens.json
python src/emailparse/email_processor_v1.py --limit 5
```

### Check Token Status
The system automatically handles token refresh. If you want to verify:
```bash
python -c "
import json
with open('gmail_tokens.json') as f:
    tokens = json.load(f)
print('Token expires at:', tokens.get('expires_at'))
print('Has refresh token:', bool(tokens.get('refresh_token')))
"
```

## Comparison to Email Clients

EmailParse uses the **exact same OAuth2 flow** as:
- **Thunderbird** when adding Gmail accounts
- **Outlook** when connecting to Gmail  
- **Apple Mail** on macOS
- **Mobile email apps**

The only difference is that EmailParse exports your emails to markdown files instead of displaying them in an inbox interface.

## Files Created

After setup, you'll have:
- `config/gmail_oauth.json` - OAuth client credentials
- `gmail_tokens.json` - Access and refresh tokens (keep private!)
- `email_exports/` - Your exported emails in markdown format

## Ready to Use!

Once setup is complete, EmailParse will work just like any other email client, but instead of showing emails in an interface, it exports them to readable markdown files that you can review and process.