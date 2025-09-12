# EmailParse V1.0 Development Plan

## Project Overview
Interactive email processing system using Gmail IMAP + Local Mistral (via LM Studio) + Human-in-the-loop decision making.

## Development Phases

### Phase 1: Foundation Setup (Days 1-2)
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
- [ ] Config loads correctly with valid YAML
- [ ] Config validation catches missing required fields
- [ ] Environment variables override config file values
- [ ] Project structure follows planned layout

#### Deliverables:
- Working Python environment
- `config_v1.yaml` template
- `tests/` folder with basic tests
- Project folder structure

---

### Phase 2: Gmail IMAP Client (Days 3-4)
**Goal**: Robust Gmail IMAP connection with authentication options

#### Tasks:
1. **Basic IMAP Connection**
   - Implement `gmail_client.py` with connection handling
   - Support both app password and OAuth2 authentication
   - Add connection retry logic and error handling
   - Implement read-only folder selection

2. **Email Fetching Operations**
   - Fetch email batches with configurable size
   - Parse email headers (subject, from, date, size)
   - Extract email body content (text/plain and text/html)
   - Handle various email encodings

3. **Email Management Operations**
   - Create/ensure "Junk-Candidate" folder exists
   - Tag emails with custom labels/flags
   - Move emails between folders
   - Mark emails as read/unread

#### Tests & Validation:
- [ ] Connect to Gmail with app password
- [ ] Connect to Gmail with OAuth2 (if configured)
- [ ] Fetch batch of emails from inbox
- [ ] Parse email content correctly (headers + body)
- [ ] Create folder if it doesn't exist
- [ ] Tag email with custom label
- [ ] Move email to different folder
- [ ] Handle connection failures gracefully
- [ ] Mock tests for all IMAP operations

#### Test Script:
```python
# test_gmail_connection.py
def test_real_gmail_connection():
    """Integration test with real Gmail account"""
    client = GmailClient(config)
    emails = client.fetch_emails(limit=5)
    assert len(emails) > 0
    # Test tagging first email
    client.tag_email(emails[0]['uid'], 'Test-Tag')
```

#### Deliverables:
- `gmail_client.py` with full IMAP functionality
- Comprehensive test suite
- Integration test with real Gmail account

---

### Phase 3: LM Studio Integration (Days 5-6)
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
- [ ] Connect to LM Studio local API
- [ ] Send test prompt and receive response
- [ ] Parse recommendation from LLM response
- [ ] Handle LM Studio server offline/error cases
- [ ] Prompt template renders correctly with email data
- [ ] Rule injection updates prompts dynamically
- [ ] Mock tests for all LLM operations

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

### Phase 4: Interactive CLI Interface (Days 7-8)
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
- [ ] CLI displays email content correctly
- [ ] User input validation works for all options
- [ ] Progress indicators update correctly
- [ ] Email formatting handles various content types
- [ ] Interactive session can be interrupted and resumed
- [ ] Help text displays correctly

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

### Phase 5: Processing Engine & State Management (Days 9-10)
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
- [ ] Process batch of emails end-to-end
- [ ] State saves correctly after each email
- [ ] Resume works from saved state
- [ ] Duplicate processing prevention works
- [ ] All user decision types execute correctly
- [ ] Error recovery doesn't lose progress
- [ ] Integration test: full processing session

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

### Phase 6: Prompt Learning System (Days 11-12)
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
- [ ] User feedback generates appropriate rules
- [ ] Rules update prompts correctly
- [ ] Rule conflicts are detected and handled
- [ ] Accuracy metrics improve with learning
- [ ] Rule management interface works
- [ ] Learning persists across sessions

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

### Phase 7: Configuration & Documentation (Days 13-14)
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

### Phase 8: Integration Testing & Polish (Days 15-16)
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

## Success Criteria

### Technical Requirements
- [ ] Successfully connect to Gmail IMAP
- [ ] Integrate with LM Studio/Mistral for analysis
- [ ] Interactive human-in-the-loop processing
- [ ] Email tagging and folder management
- [ ] State persistence and resume capability
- [ ] Dynamic prompt learning from user feedback
- [ ] Comprehensive error handling
- [ ] Complete test coverage (>80%)

### User Experience Requirements
- [ ] Intuitive CLI interface
- [ ] Clear email content display
- [ ] Fast response time (<2s per email)
- [ ] Reliable state management
- [ ] Easy setup and configuration
- [ ] Helpful documentation
- [ ] Graceful error recovery

### Quality Assurance
- [ ] All phases have passing tests
- [ ] End-to-end integration testing complete
- [ ] Documentation covers all features
- [ ] Setup process validated by fresh installation
- [ ] Performance meets requirements
- [ ] Error handling covers edge cases

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
1. Set up development environment and project structure
2. Begin Phase 1 implementation
3. Execute phases sequentially with testing validation
4. Conduct daily progress reviews
5. Maintain detailed test coverage throughout development