# EmailParse V1.0 Development Plan

## Project Overview
Interactive email processing system using Gmail API + Local Mistral (via LM Studio) + Human-in-the-loop decision making.

## Development Phases

### Phase 1: Foundation Setup (Days 1-2) ✅ COMPLETED
**Goal**: Basic project structure and environment setup

#### Tasks:
1. **Project Structure Setup**
   - Create Python virtual environment
   - Install base dependencies (imaplib, yaml, requests, rich for CLI)
   - Create folder structure
   - Initialize git repository

2. **Configuration System**
   - Create `config_v1.yaml` template
   - Build config loader with validation
   - Add environment variable support for credentials

3. **Basic Testing Framework**
   - Setup pytest structure
   - Create mock email fixtures
   - Add basic configuration tests

#### Tests & Validation:
- [x] Config loads correctly with valid YAML
- [x] Config validation catches missing required fields
- [x] Environment variables override config file values
- [x] Project structure follows planned layout

#### Deliverables:
- Working Python environment
- `config_v1.yaml` template
- `tests/` folder with basic tests
- Project folder structure

---

### Phase 2: Gmail API Client (Days 3-4) ✅ COMPLETED
**Goal**: Robust Gmail API connection with OAuth2 authentication

#### Tasks:
1. **Gmail API Connection**
   - Implement `gmail_client.py` with API connection handling
   - OAuth2 authentication with service credentials
   - Add connection retry logic and error handling
   - Implement batch request optimization

2. **Email Fetching Operations**
   - Fetch email batches using Gmail API
   - Parse email metadata (subject, from, date, size)
   - Extract email body content (text/plain and text/html)
   - Handle various email encodings and attachments
   - Export emails to markdown format

3. **Email Management Operations**
   - Create/ensure "Junk-Candidate" label exists
   - Apply labels to emails
   - Modify email labels and properties
   - Archive/unarchive emails

#### Tests & Validation:
- [x] Connect to Gmail with OAuth2 service credentials
- [x] Fetch batch of emails from inbox via API
- [x] Parse email content correctly (headers + body)
- [x] Export emails to markdown format
- [x] Create label if it doesn't exist
- [x] Apply labels to emails
- [x] Handle API rate limits and failures gracefully
- [x] Mock tests for all Gmail API operations

#### Test Script:
```python
# test_gmail_api_connection.py
def test_real_gmail_api_connection():
    """Integration test with real Gmail account"""
    client = GmailAPIClient(config)
    emails = client.fetch_emails(limit=5)
    assert len(emails) > 0
    # Test labeling first email
    client.add_label(emails[0]['id'], 'Test-Label')
    # Test markdown export
    markdown = client.export_to_markdown(emails[0])
    assert 'Subject:' in markdown
```

#### Deliverables:
- `gmail_client.py` with full Gmail API functionality
- Markdown export functionality
- Comprehensive test suite
- Integration test with real Gmail account

---

### Phase 3: LM Studio Integration (Days 5-6) ✅ COMPLETED
**Goal**: Local Mistral LLM integration via LM Studio API

#### Tasks:
1. **LM Studio API Client**
   - Implement `lmstudio_client.py` for API communication
   - Handle HTTP requests to local LM Studio server
   - Parse JSON responses and error handling
   - Add timeout and retry logic

2. **Prompt Engineering System**
   - Create `prompt_engine.py` for dynamic prompt management
   - Design base email analysis prompt template
   - Implement rule injection system for learned patterns
   - Add prompt versioning and history

3. **Email Analysis Pipeline**
   - Send email content to Mistral for analysis
   - Parse LLM response for keep/delete recommendation
   - Extract confidence scores and reasoning
   - Handle various response formats and errors

#### Tests & Validation:
- [x] Connect to LM Studio local API
- [x] Send test prompt and receive response
- [x] Parse recommendation from LLM response
- [x] Handle LM Studio server offline/error cases
- [x] Prompt template renders correctly with email data
- [x] Rule injection updates prompts dynamically
- [x] Mock tests for all LLM operations

#### Test Script:
```python
# test_lmstudio_integration.py
def test_real_lmstudio_analysis():
    """Integration test with actual LM Studio"""
    client = LMStudioClient(config)
    test_email = create_test_email_fixture()
    result = client.analyze_email(test_email)
    assert result['recommendation'] in ['KEEP', 'DELETE']
    assert 'reasoning' in result
```

#### Deliverables:
- `lmstudio_client.py` with API integration
- `prompt_engine.py` with dynamic prompts
- Test suite with LM Studio integration tests
- Sample prompt templates

---

### Phase 4: Interactive CLI Interface (Days 7-8) ✅ COMPLETED
**Goal**: User-friendly command-line interface for human-in-the-loop processing

#### Tasks:
1. **CLI Framework Setup**
   - Use Rich library for attractive terminal output
   - Implement email display formatting
   - Add interactive input handling
   - Create progress indicators and session info

2. **Email Display System**
   - Format email content for terminal display
   - Truncate long content appropriately
   - Highlight important information (subject, sender)
   - Show LLM analysis results clearly

3. **Decision Input System**
   - Handle keyboard input for user decisions
   - Validate input choices (A/R/S/U/Q)
   - Provide help text and command descriptions
   - Add confirmation for destructive actions

#### Tests & Validation:
- [x] CLI displays email content correctly
- [x] User input validation works for all options
- [x] Progress indicators update correctly
- [x] Email formatting handles various content types
- [x] Interactive session can be interrupted and resumed
- [x] Help text displays correctly
- [x] Confidence-based decision logic implemented
- [x] Auto-accept for high confidence recommendations
- [x] Enhanced feedback collection for low confidence cases

#### Test Script:
```python
# test_cli_interface.py - Using automated input simulation
def test_cli_email_display():
    """Test email formatting and display"""
    email = create_test_email_fixture()
    cli = InteractiveCLI()
    formatted = cli.format_email_display(email)
    assert "Subject:" in formatted
    assert "From:" in formatted
```

#### Deliverables:
- Interactive CLI with Rich formatting
- User input handling system
- Progress tracking and session management

---

### Phase 5: Processing Engine & State Management (Days 9-10) ✅ COMPLETED
**Goal**: Core processing logic with state persistence and resume capability

#### Tasks:
1. **Main Processing Engine**
   - Implement `email_processor_v1.py` main orchestrator
   - Coordinate Gmail, LM Studio, and CLI components
   - Handle processing flow and decision routing
   - Add error recovery and graceful shutdowns

2. **State Management System**
   - Create `processed_log.jsonl` logging system
   - Track processed email UIDs and decisions
   - Implement resume functionality from last position
   - Prevent duplicate processing across sessions

3. **Decision Handling**
   - Process user decisions (Accept/Reject/Skip/Update)
   - Execute IMAP operations based on decisions
   - Log decisions vs LLM recommendations
   - Handle undo capability for recent actions

#### Tests & Validation:
- [x] Process batch of emails end-to-end ✅ (Integration complete)
- [x] State saves correctly after each email (JSONL logging implemented)
- [x] Resume works from saved state ✅ (Tested)
- [x] Duplicate processing prevention works (Logic implemented and tested)
- [x] All user decision types execute correctly ✅ (Gmail integration working)
- [x] Error recovery doesn't lose progress ✅ (Tested)
- [x] Integration test: full processing session ✅ (End-to-end tests pass)
- [x] Confidence-based prompt update logic (Implemented and tested)
- [x] Smart decision tracking and statistics (Implemented and tested)
- [x] Undo capability for recent actions ✅ (NEW: Implemented and tested)
- [x] Graceful error handling and recovery ✅ (NEW: Implemented and tested)

#### Test Script:
```python
# test_processing_engine.py
def test_full_processing_session():
    """End-to-end processing test"""
    processor = EmailProcessor(config)
    # Process 3 test emails with mock responses
    results = processor.process_batch(limit=3, mock_mode=True)
    assert len(results) == 3
    # Test resume capability
    processor2 = EmailProcessor(config)
    remaining = processor2.get_remaining_emails()
    assert len(remaining) == 0  # All processed
```

#### Deliverables:
- Complete processing engine
- State persistence system
- Resume functionality
- Comprehensive end-to-end tests

---

### Phase 6: Prompt Learning System (Days 11-12) ✅ COMPLETED
**Goal**: Dynamic prompt updates based on user feedback

#### Tasks:
1. **Rule Learning Engine**
   - Detect patterns in user corrections
   - Generate new classification rules
   - Update prompt templates dynamically
   - Validate rule effectiveness

2. **Prompt Update Interface**
   - CLI interface for adding custom rules
   - Rule validation and conflict detection
   - Prompt preview before applying changes
   - Rule management (list, edit, delete rules)

3. **Learning Analytics**
   - Track accuracy improvements over time
   - Show user vs LLM agreement rates
   - Identify common misclassification patterns
   - Generate learning reports

#### Tests & Validation:
- [x] User feedback generates appropriate rules
- [x] Rules update prompts correctly
- [x] Rule conflicts are detected and handled
- [x] Accuracy metrics improve with learning
- [x] Rule management interface works
- [x] Learning persists across sessions
- [x] Confidence-based update decisions
- [x] Smart prompt versioning and history tracking

#### Test Script:
```python
# test_prompt_learning.py
def test_rule_learning():
    """Test dynamic rule generation"""
    engine = PromptEngine()
    # Simulate user correction pattern
    corrections = [
        ("newsletter@site.com", "DELETE", "User kept"),
        ("newsletter@site.com", "DELETE", "User kept")
    ]
    engine.learn_from_corrections(corrections)
    new_rule = engine.generate_rule(corrections)
    assert "newsletter@site.com" in new_rule
```

#### Deliverables:
- Prompt learning system
- Rule management interface
- Learning analytics dashboard
- Persistent rule storage

---

### Phase 7: Configuration & Documentation (Days 13-14) 🔄 IN PROGRESS
**Goal**: Complete setup documentation and configuration management

#### Tasks:
1. **Configuration System Enhancement**
   - Add configuration validation
   - Create setup wizard for first-time users
   - Add configuration templates for different use cases
   - Implement configuration backup/restore

2. **Documentation Creation**
   - Complete setup instructions
   - Gmail app password/OAuth2 setup guide
   - LM Studio configuration guide
   - Usage examples and troubleshooting

3. **Installation & Deployment**
   - Create requirements.txt
   - Add installation scripts
   - Create systemd service file (optional)
   - Add Docker containerization (optional)

#### Tests & Validation:
- [ ] Fresh installation works from documentation
- [ ] Configuration wizard completes successfully
- [ ] All configuration options documented
- [ ] Gmail setup instructions work correctly
- [ ] LM Studio setup instructions work correctly
- [ ] Troubleshooting guide covers common issues

#### Test Script:
```python
# test_full_setup.py
def test_fresh_installation():
    """Test complete setup from scratch"""
    # This would test the entire setup process
    # in a clean environment
    pass
```

#### Deliverables:
- Complete documentation
- Setup wizard
- Installation scripts
- User guide

---

### Phase 8: Integration Testing & Polish (Days 15-16) 📋 PENDING
**Goal**: Final testing, optimization, and user experience improvements

#### Tasks:
1. **Full Integration Testing**
   - End-to-end workflow testing
   - Performance testing with large email volumes
   - Error handling under various failure conditions
   - Memory usage and resource optimization

2. **User Experience Polish**
   - CLI interface improvements
   - Better error messages and help text
   - Progress indicators and timing estimates
   - Keyboard shortcuts and efficiency improvements

3. **Production Readiness**
   - Logging system for debugging
   - Configuration validation improvements
   - Backup and recovery procedures
   - Performance monitoring

#### Tests & Validation:
- [ ] Process 100+ emails successfully
- [ ] Handle all error conditions gracefully
- [ ] Memory usage stays within acceptable bounds
- [ ] User experience is smooth and intuitive
- [ ] All edge cases handled correctly
- [ ] Production deployment works

#### Final Integration Test:
```python
# test_production_readiness.py
def test_large_batch_processing():
    """Test with realistic email volumes"""
    processor = EmailProcessor(config)
    results = processor.process_batch(limit=100)
    # Verify performance, memory usage, etc.
```

#### Deliverables:
- Production-ready V1.0 system
- Complete test suite
- Performance benchmarks
- Deployment guide

---

## Current Status (Phase 6 Complete)

### ✅ COMPLETED PHASES (1-6)
- **Phase 1**: Foundation Setup - Project structure, config system, dependencies
- **Phase 2**: Gmail API Client - OAuth2 authentication, email fetching, markdown export
- **Phase 3**: LM Studio Integration - API client, prompt engine, email analysis pipeline
- **Phase 4**: Interactive CLI - Rich interface, human-in-the-loop feedback, confidence-based decisions
- **Phase 5**: Processing Engine - State management, Gmail integration, undo capability, end-to-end testing
- **Phase 6**: Prompt Learning - Dynamic updates, confidence-based learning, integration testing

### 🚀 READY FOR PRODUCTION
The core email processing system is **fully functional** and ready for production use:

**Complete Workflow:**
- ✅ Gmail API integration with authentication
- ✅ LM Studio email analysis with confidence-based decisions
- ✅ Interactive CLI with undo capability
- ✅ State persistence and resume functionality
- ✅ Smart prompt learning from user feedback
- ✅ End-to-end testing validated

**Usage:**
```bash
# Validate system setup
python email_processor_v1.py --validate

# Start processing emails  
python email_processor_v1.py --max-emails 10
```

### 🔄 IN PROGRESS
- **Phase 7**: Configuration & Documentation (50% complete)
  - Config system ✅ Complete
  - Setup documentation ❌ Pending
  - User guide ❌ Pending

### 📋 REMAINING WORK
- **Phase 7**: Complete documentation and setup guides
- **Phase 8**: Final integration testing and polish

### 🎯 KEY ACHIEVEMENTS
- **Confidence-based AI decisions**: Auto-accept high confidence, enhanced feedback for low confidence
- **Smart prompt learning**: Updates only when beneficial (disagreements + low confidence cases)
- **Production-ready state management**: JSONL logging, resume capability, duplicate prevention
- **Rich CLI experience**: Color-coded confidence levels, clear analysis display, session statistics
- **Undo capability**: Reverse recent actions, remove labels, restore email state
- **Robust error handling**: Graceful recovery from failures, comprehensive validation
- **End-to-end integration**: Complete workflow tested and validated

---

## Success Criteria

### Technical Requirements
- [x] Successfully connect to Gmail API (updated from IMAP)
- [x] Integrate with LM Studio/Mistral for analysis
- [x] Interactive human-in-the-loop processing
- [x] Email tagging and folder management
- [x] State persistence and resume capability
- [x] Dynamic prompt learning from user feedback
- [x] Confidence-based decision logic
- [x] Comprehensive error handling
- [ ] Complete test coverage (>80%)

### User Experience Requirements
- [x] Intuitive CLI interface with Rich formatting
- [x] Clear email content display with markdown support
- [x] Fast response time (<2s per email)
- [x] Reliable state management with JSONL logging
- [x] Auto-accept for high confidence decisions
- [x] Enhanced feedback collection for learning
- [ ] Easy setup and configuration
- [ ] Helpful documentation
- [x] Graceful error recovery

### Quality Assurance
- [x] Phases 1-6 have passing tests
- [x] LM Studio integration testing complete
- [x] Core functionality end-to-end tested
- [ ] Documentation covers all features
- [ ] Setup process validated by fresh installation
- [x] Performance meets requirements (tested with nous-hermes)
- [x] Error handling covers edge cases

## Risk Mitigation

### Technical Risks
- **Gmail API/IMAP changes**: Use standard IMAP protocols, test with multiple Gmail accounts
- **LM Studio compatibility**: Mock LM Studio for testing, graceful fallback for offline mode
- **Performance issues**: Implement batch processing, memory management, and progress saving

### Development Risks
- **Scope creep**: Strict adherence to V1.0 feature set, defer enhancements to V2.0
- **Integration complexity**: Comprehensive mocking and unit tests for each component
- **Time overruns**: Buffer days built into schedule, prioritize core functionality

## Next Steps

### Immediate (Phase 7 - Documentation)
1. **Create comprehensive setup guide**
   - Gmail API OAuth2 setup instructions
   - LM Studio installation and model loading
   - Configuration file setup walkthrough
   
2. **Write user documentation**
   - Usage guide with examples
   - Confidence-based workflow explanation
   - Troubleshooting common issues
   
3. **Create installation scripts**
   - Automated dependency installation
   - Configuration validation
   - First-run setup wizard

### Final Phase (Phase 8 - Polish)
1. **End-to-end integration testing**
   - Large batch processing (100+ emails)
   - Memory usage and performance validation
   - Error recovery scenarios
   
2. **User experience improvements**
   - Keyboard shortcuts
   - Better progress indicators
   - Performance optimizations

### Ready for Production Use
The system is **already functional** for daily email processing. Phases 7-8 focus on polish and documentation rather than core functionality.