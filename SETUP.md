# EmailParse V1.0 Setup Guide

This guide will help you set up EmailParse V1.0 to connect to your Gmail account and start processing emails with markdown export.

## Prerequisites

1. **Python 3.8+** installed
2. **Gmail account** with either:
   - App Password enabled (recommended for simplicity)
   - OAuth2 credentials (more secure, for advanced users)
3. **LM Studio** (for future phases, not needed for Phase 2)

## Step 1: Installation

1. Clone and set up the project:
```bash
cd EmailParse
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Verify installation:
```bash
python -m pytest tests/unit/ -v
```

## Step 2: Gmail Authentication Setup

EmailParse supports two authentication methods. Choose one:

### Option A: App Password (Recommended)

This is the simplest method for personal use.

#### Enable App Password:
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification**
3. Enable 2-Step Verification if not already enabled
4. Go to **App passwords** 
5. Create a new app password:
   - App: **Mail**
   - Device: **Other (Custom name)** → Enter "EmailParse"
6. Copy the 16-character app password (format: xxxx xxxx xxxx xxxx)

### Option B: OAuth2 (Advanced)

For enhanced security, especially in production environments.

#### Create OAuth2 Credentials:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Gmail API**
4. Create credentials:
   - Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
   - Application type: **Desktop application**
   - Name: "EmailParse Client"
5. Download the JSON file and note the `client_id` and `client_secret`

## Step 3: Configuration

1. Copy the configuration template:
```bash
cp config/config_v1.yaml.template config/config_v1.yaml
```

2. Edit `config/config_v1.yaml` with your details:

### For App Password Authentication:
```yaml
gmail:
  host: "imap.gmail.com"
  port: 993
  use_ssl: true
  user: "your-email@gmail.com"  # Your Gmail address
  
  auth:
    method: "app_password"
    app_password: "your-16-char-app-password"  # From Step 2A
  
  processing:
    batch_size: 10
    mailbox: "INBOX"
    junk_folder: "Junk-Candidate"

lmstudio:
  base_url: "http://localhost:1234"  # Not used in Phase 2
  api_key: ""
  timeout: 30
  model:
    name: "mistral"
    temperature: 0.3
    max_tokens: 500

app:
  log_level: "INFO"
  log_file: "logs/emailparse.log"
  resume_from_last: true
  confirm_before_action: true
  email_preview_length: 500
  show_progress: true
```

### For OAuth2 Authentication:
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
      refresh_token: "your-refresh-token"  # Obtained via OAuth flow
```

**Note**: OAuth2 refresh token generation is complex and will be fully implemented in Phase 2.0. For now, use App Password method.

## Step 4: Test Your Setup

1. **Test Gmail connection:**
```bash
python tests/integration/test_gmail_integration.py connection
```

2. **Test email processing:**
```bash
python tests/integration/test_gmail_integration.py processor
```

3. **Run the main processor:**
```bash
python src/emailparse/email_processor_v1.py --limit 5
```

## Step 5: Using EmailParse

### Basic Usage

Process 10 emails from INBOX and export to markdown:
```bash
cd src
python -m emailparse.email_processor_v1 --mailbox INBOX --limit 10
```

### Command Line Options

```bash
python -m emailparse.email_processor_v1 --help

Options:
  --config, -c      Configuration file path
  --mailbox, -m     Mailbox to process (default: INBOX)  
  --limit, -l       Number of emails to process (default: 10)
  --list-mailboxes  List available mailboxes
  --mailbox-info    Get info about specific mailbox
```

### Examples

```bash
# List all available mailboxes
python -m emailparse.email_processor_v1 --list-mailboxes

# Get information about INBOX
python -m emailparse.email_processor_v1 --mailbox-info INBOX

# Process 20 emails from a specific folder
python -m emailparse.email_processor_v1 --mailbox "Promotions" --limit 20

# Use custom configuration file
python -m emailparse.email_processor_v1 --config /path/to/custom_config.yaml
```

## Step 6: Review Results

EmailParse exports emails to the `email_exports/` directory:

- **Individual files**: `email_[uid]_[subject].md`
- **Batch files**: `[mailbox]_[timestamp].md` 
- **Index file**: `index.md` (lists all exports)

Example output structure:
```
email_exports/
├── index.md
├── INBOX_20250112_143022.md
├── INBOX_20250112_150045.md
└── Promotions_20250112_153015.md
```

Each markdown file contains:
- Email metadata (UID, sender, date, size)
- Full email content in code blocks
- Table of contents for batch files

## Environment Variables

You can override any configuration setting with environment variables:

```bash
# Override Gmail credentials
export EMAILPARSE_GMAIL_USER="different@gmail.com"
export EMAILPARSE_GMAIL_AUTH_APP_PASSWORD="different-password"

# Override processing settings  
export EMAILPARSE_GMAIL_PROCESSING_BATCH_SIZE="20"
export EMAILPARSE_APP_LOG_LEVEL="DEBUG"
```

## Troubleshooting

### Common Issues

1. **"Authentication failed"**
   - Verify your Gmail address is correct
   - Check that 2-Step Verification is enabled
   - Regenerate your app password
   - Ensure you're copying the app password without spaces

2. **"Configuration file not found"**
   - Make sure `config/config_v1.yaml` exists
   - Copy from `config/config_v1.yaml.template`
   - Check file permissions

3. **"No emails found"**
   - Try a different mailbox: `--list-mailboxes` to see available ones
   - Check if the mailbox has emails
   - Try without search criteria (processes all emails)

4. **"Connection timeout"**
   - Check your internet connection
   - Verify Gmail IMAP is enabled in your account
   - Try again (temporary network issues)

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export EMAILPARSE_APP_LOG_LEVEL="DEBUG"
python -m emailparse.email_processor_v1 --limit 5
```

### Test Configuration

Validate your configuration:
```bash
python -c "
from src.emailparse.config import Config
config = Config('config/config_v1.yaml')
print('✅ Configuration loaded successfully!')
print(f'Gmail user: {config.get_nested(\"gmail\", \"user\")}')
print(f'Auth method: {config.get_nested(\"gmail\", \"auth\", \"method\")}')
"
```

## Security Notes

1. **App Passwords**: Store securely, don't share or commit to version control
2. **Configuration Files**: Added to `.gitignore` to prevent accidental commits  
3. **Environment Variables**: Use for sensitive data in production
4. **Read-Only Mode**: Phase 2 only reads emails by default, no modifications

## Next Steps

Once Phase 2 is working:
- Review exported markdown files in `email_exports/`
- Use the data to understand your email patterns
- Prepare for Phase 2.0 with LLM integration and advanced features

## Support

- **Documentation**: Check `readme.md` and `DevPlan.md`
- **Issues**: Review error messages and logs
- **Testing**: Run `pytest tests/unit/` to verify installation