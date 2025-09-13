# EmailParse - AI-Powered Email Management System

[![Tests](https://img.shields.io/badge/tests-passing-green)](tests/)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **Thread-aware email processing with local AI analysis and human-in-the-loop decision making**

## 🚀 Quick Start

```bash
# 1. Set up Gmail access
python setup_gmail.py

# 2. Start interactive email processing 
python email_processor_v1.py

# 3. Optional: Verify system
python verify_uid_system.py
```

## 📋 Overview

EmailParse is an intelligent email management system that uses **local AI models** to analyze emails while keeping you in control of all decisions. It processes emails in **thread context**, automatically preserves **starred messages**, and only performs **tagging operations** (no deletion) for maximum safety.

### ✨ Key Features

- **🧠 Thread-Aware Processing**: Analyzes entire email conversations, not just individual messages
- **⭐ Smart Preservation**: Automatically keeps any thread containing starred messages  
- **🔒 Safe Operations**: Only tags emails for review - never deletes anything
- **🤖 Local AI**: Uses LM Studio with Mistral for private, offline email analysis
- **👥 Human-in-the-Loop**: Interactive review of all AI recommendations
- **🔄 Resume Processing**: Never processes the same email twice
- **📊 Rich Interface**: Beautiful CLI with progress tracking and detailed previews

## 🏗️ Architecture

```
📁 EmailParse/
├── 🚀 User Entry Points
│   ├── email_processor_v1.py      # Main application
│   ├── setup_gmail.py             # Gmail setup utility  
│   ├── fetch_emails.py            # Email fetching tool
│   └── verify_uid_system.py       # System verification
├── 🧠 Core Processing (core/)
│   ├── email_analyzer.py          # AI email analysis
│   ├── thread_analyzer.py         # Thread-aware analysis
│   └── thread_processor.py        # Thread grouping & processing
├── 🔌 External Clients (clients/)
│   ├── gmail_client.py             # Full IMAP client
│   ├── gmail_oauth.py              # OAuth2 authentication
│   ├── gmail_api_client.py         # Gmail API client
│   └── lmstudio_client.py          # LLM integration
├── 💻 User Interface (ui/)
│   └── interactive_cli.py          # Rich CLI interface
├── 🛠️ Utilities (utils/)
│   ├── config.py                   # Configuration management
│   ├── prompt_engine.py            # Prompt handling
│   └── markdown_exporter.py       # Email export functionality
└── 🧪 Tests (tests/)
    ├── unit/, integration/         # Comprehensive test suite
    └── debug/                      # Debug utilities
```

## 🎯 How It Works

### Thread-Aware Processing

EmailParse groups emails by conversation threads and analyzes them together for better context:

```
📧 Thread: "Project Discussion"
├── Message 1: "Let's discuss the requirements" 
├── Message 2: "I agree with the timeline" ⭐ (starred)
└── Message 3: "When do we start?"

🤖 Analysis: KEEP_THREAD (auto-keep due to starred message)
🏷️ Action: Tag all messages as important
```

### AI Analysis with Local Privacy

- **Local Processing**: All AI analysis happens on your machine via LM Studio
- **No Cloud Services**: Your emails never leave your computer
- **Context-Aware**: Considers thread history, participants, and message importance
- **Confidence Scoring**: Provides reasoning and confidence levels for all decisions

### Safe Operations

EmailParse **never deletes emails**. Instead it:
- ✅ Tags emails for your review
- ✅ Moves emails to folders you specify
- ✅ Tracks all decisions in detailed logs
- ❌ Never permanently removes anything

## 📦 Installation

### Prerequisites

- **Python 3.8+**
- **LM Studio** (for AI analysis) - [Download here](https://lmstudio.ai/)
- **Gmail Account** with app-specific password or OAuth2 setup

### Setup Steps

1. **Clone and Install**
   ```bash
   git clone https://github.com/your-repo/EmailParse.git
   cd EmailParse
   pip install -r requirements.txt
   ```

2. **Configure Gmail Access**
   ```bash
   python setup_gmail.py
   ```
   This will guide you through:
   - Setting up OAuth2 credentials
   - Configuring Gmail IMAP access
   - Testing the connection

3. **Start LM Studio**
   - Download and install [LM Studio](https://lmstudio.ai/)
   - Load a Mistral model
   - Start the local server (default: http://localhost:1234)

4. **Run EmailParse**
   ```bash
   python email_processor_v1.py
   ```

## 🎮 Usage

### Interactive Email Processing

The main interface provides rich, interactive email review:

```
🔍 EmailParse v1.0 - Thread Processing Mode

📊 Progress: 15/50 emails processed
🧵 Current Thread: "Meeting Follow-up" (3 messages)

┌─ Thread Analysis ─────────────────────────────────────────┐
│ Participants: alice@company.com, bob@company.com         │
│ Date Range: Jan 15-16, 2025                              │
│ Contains: ⭐ 1 starred message                            │
│                                                           │
│ 🤖 AI Recommendation: KEEP_THREAD                        │
│ 🎯 Confidence: 100% (auto-keep due to starred message)   │
│ 💭 Reasoning: Thread contains starred message from Bob   │
└───────────────────────────────────────────────────────────┘

Your decision:
[K] Keep entire thread    [D] Delete entire thread
[M] Mixed (review individual messages)   [Q] Quit
Choice: ▊
```

### Command Line Options

```bash
# Thread processing (default)
python email_processor_v1.py --thread-mode

# Individual email processing  
python email_processor_v1.py --individual-mode

# Limit number of emails
python email_processor_v1.py --max-emails 20

# Validate setup only
python email_processor_v1.py --validate
```

## ⚙️ Configuration

Configuration is managed in `config/config_v1.yaml`:

```yaml
gmail:
  host: imap.gmail.com
  port: 993
  use_ssl: true
  user: your-email@gmail.com
  auth:
    method: oauth2
    oauth2:
      client_id: your-client-id.apps.googleusercontent.com
      client_secret: your-client-secret
      token_file: gmail_tokens.json
  processing:
    batch_size: 10
    junk_folder: Junk-Candidate

lmstudio:
  base_url: http://localhost:1234
  model:
    name: mistral
    temperature: 0.3
    max_tokens: 500

app:
  log_level: INFO
  show_progress: true
```

## 🧪 Testing

EmailParse includes comprehensive tests:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v          # Unit tests
python -m pytest tests/integration/ -v   # Integration tests

# Run specific functionality tests
python tests/test_thread_processing.py    # Thread processing
python tests/test_end_to_end_threads.py   # End-to-end integration
```

## 🔧 Utilities

### System Verification
```bash
python verify_uid_system.py
```
Verifies UID tracking system prevents duplicate processing.

### Email Fetching
```bash
python fetch_emails.py        # IMAP-based fetching
python fetch_emails_api.py    # API-based fetching
```

### Gmail Setup
```bash
python setup_gmail.py
```
Interactive OAuth2 setup and connection testing.

## 🛡️ Security & Privacy

- **Local Processing**: All AI analysis happens on your machine
- **OAuth2 Security**: Secure authentication with automatic token refresh
- **No Data Sharing**: Your emails never leave your computer
- **Safe Operations**: No email deletion, only tagging and organization
- **Audit Trail**: Complete logging of all decisions and actions

## 📈 Features Implemented

### ✅ Core Features
- [x] Thread-aware email processing
- [x] Starred message auto-keep
- [x] Local AI analysis with LM Studio
- [x] Interactive human-in-the-loop interface
- [x] OAuth2 Gmail authentication
- [x] UID-based duplicate prevention
- [x] Rich CLI with progress tracking
- [x] Safe tagging-only operations
- [x] Comprehensive logging

### ✅ Advanced Features  
- [x] Thread context analysis
- [x] Confidence-based recommendations
- [x] Dynamic prompt updates
- [x] Markdown email export
- [x] Session resume capability
- [x] Batch and individual processing modes
- [x] Detailed audit trails

## 🗺️ Roadmap

See [DEVPLAN.md](DEVPLAN.md) for detailed development phases and upcoming features.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python -m pytest tests/ -v`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`) 
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/EmailParse/issues)
- **Documentation**: See files in the repository
- **Configuration Help**: Run `python setup_gmail.py` for guided setup

---

**EmailParse** - Take control of your inbox with AI-powered, privacy-first email management! 🚀