# Email Processing with IMAP and Local LLM - Decision Summary

## Overview
This document summarizes the approach decided for cleaning up email using IMAP access with a local LLM, avoiding direct API access that email providers restrict.

## Project Phases

### Version 1.0 - Interactive Human-in-the-Loop (Core Implementation)
**Focus**: Gmail IMAP + Local Mistral + Interactive Processing
- Single Gmail account IMAP connection
- Mistral integration via LM Studio local API
- Human-in-the-loop email processing (one-by-one review)
- Dynamic LLM prompt updates based on user feedback
- Email tagging for manual cleanup
- Processing log to prevent duplicates

### Version 2.0 - Enhanced Automation (Future)
**Focus**: Multi-provider + TheBrain Integration + Batch Processing
- Multi-account support (5 Gmail + 1 Office 365)
- TheBrain API integration for valuable email collection
- Automated batch processing modes
- Advanced classification with multiple LLM strategies
- Full OAuth2 implementation for all providers

## Core Architecture

### Local IMAP Gateway Approach
- **LLM ⇄ Local Gateway ⇄ IMAP Server**
- Gateway exposes limited JSON endpoints (search, fetch, stage-move)
- LLM never sees credentials or direct IMAP access
- All operations READ-ONLY by default with human-in-the-loop for mutations

### Multi-Account Support
- **5 Gmail accounts + 1 Microsoft 365 account**
- Unified configuration via `config.yaml`
- Per-account authentication (OAuth2/app passwords)
- Centralized staging and execution

## Authentication Strategy

### Gmail Accounts
- **XOAUTH2** (preferred): OAuth2 with minimal Google API usage (token endpoints only)
- **App Passwords**: Fallback for accounts with 2FA enabled
- No Gmail API calls - pure IMAP with OAuth authentication

### Microsoft 365
- **Device Code Flow**: OAuth2 without client secrets
- IMAP access via `outlook.office365.com`
- Token refresh handled automatically

## Processing Pipeline

### 1. Classification System
**Rule-based heuristics:**
- **Junk patterns**: unsubscribe, promotions, newsletters, spam keywords
- **Keep signals**: invoices, receipts, confirmations, meeting minutes
- **Domain reputation**: trusted senders (Amazon, GitHub, Microsoft, etc.)

### 2. Action Staging
- **Junk**: Move to `Junk-Candidate` folder
- **Keep**: Flag messages and optionally send to TheBrain
- **Maybe**: Leave for manual review
- All actions staged in `staged_actions.jsonl` before execution

### 3. Duplicate Prevention
- **Processing Log**: Maintain `processed_emails.jsonl` with UID + account tracking
- **Skip Processed**: Check log before classification to avoid reprocessing
- **Persistent State**: Log survives between runs and prevents duplicate work

### 4. TheBrain Integration
- **REST API**: Create thoughts for important emails
- **Metadata**: Include sender, date, and email summary
- **Rate limiting**: Configurable max emails per account per run

## Safety Features

### Read-Only Default
- All IMAP sessions use READ-ONLY mode
- Mutations require separate human-approved step
- Staging files allow review before execution

### Network Isolation
- Gateway runs on localhost only
- LLM should be firewall-restricted from internet access
- Only gateway connects to IMAP servers

### Credential Security
- OAuth tokens stored locally, never in LLM context
- App passwords isolated in configuration files
- No credentials exposed to classification logic

## Key Benefits

1. **Provider Compliance**: No API access concerns - uses standard IMAP
2. **Local Control**: All processing happens locally
3. **Safety by Design**: Read-only with human confirmation for changes  
4. **Multi-Account**: Handles multiple email accounts in single pass
5. **Extensible**: Easy to add new classification rules or actions

## Implementation Files

- `config.yaml`: Multi-account configuration
- `oauth_gmail.py`: Gmail OAuth token management
- `oauth_m365.py`: Microsoft 365 device code flow
- `mail_gateway_multi.py`: Main gateway with classification
- `staged_actions.jsonl`: Action queue for human review
- `processed_emails.jsonl`: Log of processed emails to prevent duplicates

## Version 1.0 Implementation Details

### Core Components
- **IMAP Client**: Single Gmail account connection with app password/OAuth2
- **LM Studio Integration**: Local Mistral API calls for email analysis
- **Interactive CLI**: Human-in-the-loop interface for decision making
- **Prompt Engine**: Dynamic LLM prompt updates based on user feedback
- **Email Tagger**: IMAP folder/label management for cleanup staging
- **Processing Logger**: Duplicate prevention and decision tracking

### Human-in-the-Loop Processing
- **Chunk Processing**: Fetch configurable batch of emails (default: 10)
- **Single Email Analysis**: Present one email with full content
- **Mistral Analysis**: Send to LM Studio for keep/delete recommendation
- **Interactive Decision**: Accept/Reject/Skip with immediate IMAP tagging
- **Prompt Learning**: Update classification rules based on user corrections
- **Progress Tracking**: Resume from last processed email across sessions

### Version 2.0 Future Features

#### Multi-Account & Provider Support
- **Gmail Multi-Account**: Support for 5 Gmail accounts
- **Office 365 Integration**: Microsoft 365 IMAP with OAuth2
- **Unified Configuration**: Single config file for all accounts

#### TheBrain Integration
- **Valuable Email Collection**: Automatic thought creation for important emails
- **Metadata Preservation**: Sender, date, and content summary in TheBrain notes
- **Categorization**: Smart tagging and linking in TheBrain structure

#### Advanced Processing Modes
- **Batch Processing**: Fully automated classification and staging
- **Test Mode**: 10-email batches for validation
- **Production Mode**: Large-scale processing with human review

## Version 1.0 Usage Workflow

### Interactive Processing Session
1. **Initialize**: Connect to Gmail IMAP and LM Studio
2. **Fetch Chunk**: Retrieve batch of unprocessed emails (configurable size)
3. **Process Each Email**:
   - Display email content (subject, sender, date, body preview)
   - Send to Mistral via LM Studio API for keep/delete analysis
   - Show LLM recommendation with reasoning
   - Wait for human decision (Accept/Reject/Skip/Quit)
4. **Update System**:
   - Tag email in Gmail based on decision
   - Log decision vs recommendation for learning
   - Update LLM prompt if user provides correction rules
5. **Continue**: Move to next email or fetch new chunk
6. **Resume**: Save progress to resume later sessions

### Output Format (Version 1.0)
```
📧 Processing Email 3/10 from Inbox

Subject: "Weekly Newsletter - Tech Updates"
From: newsletter@techsite.com
Date: 2025-01-15 14:30 PM
Size: 15.2 KB

Content Preview:
"This week's top tech stories: AI breakthrough in..."

🤖 Mistral Analysis via LM Studio:
Recommendation: DELETE
Confidence: 75%
Reasoning: Newsletter format, weekly cadence, mass distribution pattern

Your decision:
[A] Accept - Tag as Junk-Candidate
[R] Reject - Keep in inbox  
[S] Skip - Leave unchanged
[U] Update prompt with rule
[Q] Quit session
Choice: _
```

### Version 1.0 File Structure
- `email_processor_v1.py` - Main interactive processor
- `gmail_client.py` - Gmail IMAP connection handler
- `lmstudio_client.py` - LM Studio API integration
- `prompt_engine.py` - Dynamic prompt management
- `config_v1.yaml` - Single Gmail account configuration
- `processed_log.jsonl` - Processing history and decisions
- `prompts/` - LLM prompt templates and learned rules

This approach provides the security and control needed while avoiding API restrictions from email providers.