"""
End-to-End Integration Test for EmailParse V1.0
Tests the complete workflow from email fetching to processing
"""

import sys
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from email_processor_v1 import EmailProcessor
from email_analyzer import EmailAnalysisResult

def create_test_config():
    """Create a test configuration"""
    return {
        'gmail': {
            'host': 'imap.gmail.com',
            'port': 993,
            'use_ssl': True,
            'user': 'test@gmail.com',
            'auth': {'method': 'oauth2'},
            'processing': {
                'batch_size': 3,
                'mailbox': 'INBOX',
                'junk_folder': 'Junk-Candidate'
            }
        },
        'lmstudio': {
            'base_url': 'http://localhost:1234',
            'api_key': '',
            'timeout': 30,
            'model': {
                'name': 'mistral',
                'temperature': 0.3,
                'max_tokens': 500
            }
        },
        'app': {
            'log_level': 'INFO',
            'log_file': 'logs/test_emailparse.log',
            'resume_from_last': True,
            'confirm_before_action': True,
            'email_preview_length': 500,
            'show_progress': True
        }
    }

def test_processor_initialization():
    """Test that the email processor initializes correctly"""
    print("Testing processor initialization...")
    
    # Create temporary config file
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        print("✓ Processor initialization successful")
        
        # Test components are initialized
        assert processor.gmail_client is not None
        assert processor.analyzer is not None
        assert processor.cli is not None
        print("✓ All components initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Processor initialization failed: {e}")
        return False
    finally:
        # Clean up
        os.unlink(config_path)

def test_email_fetching():
    """Test email fetching functionality"""
    print("\\nTesting email fetching...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Test fetching emails (should get mock emails)
        emails = processor.fetch_unprocessed_emails(limit=3)
        
        assert len(emails) > 0, "Should fetch at least one email"
        print(f"✓ Fetched {len(emails)} emails")
        
        # Validate email format
        for email in emails:
            assert 'id' in email
            assert 'subject' in email
            assert 'from' in email
            assert 'markdown' in email
            print(f"✓ Email {email['id']} has correct format")
        
        return True
        
    except Exception as e:
        print(f"✗ Email fetching failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_email_analysis():
    """Test email analysis with LM Studio"""
    print("\\nTesting email analysis...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Get a test email
        emails = processor.fetch_unprocessed_emails(limit=1)
        if not emails:
            print("✗ No emails available for analysis")
            return False
        
        test_email = emails[0]
        
        # Analyze the email
        analysis = processor.analyzer.analyze_email(test_email)
        
        if analysis:
            print(f"✓ Email analysis successful")
            print(f"  Recommendation: {analysis.recommendation}")
            print(f"  Confidence: {analysis.confidence:.2f}")
            print(f"  Category: {analysis.category}")
            
            # Validate analysis result
            assert analysis.recommendation in ['KEEP', 'JUNK-CANDIDATE']
            assert 0.0 <= analysis.confidence <= 1.0
            assert analysis.reasoning is not None
            print("✓ Analysis result validation passed")
            
            return True
        else:
            print("✗ Email analysis returned None")
            return False
        
    except Exception as e:
        print(f"✗ Email analysis failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_state_management():
    """Test state persistence and resume functionality"""
    print("\\nTesting state management...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        # Create processor and process an email
        processor = EmailProcessor(config_path)
        
        # Mock an email processing action
        test_email_id = "test_state_email_001"
        test_analysis = EmailAnalysisResult(
            email_id=test_email_id,
            recommendation="JUNK-CANDIDATE",
            category="Test",
            confidence=0.8,
            reasoning="Test analysis",
            key_factors=["Test factor"]
        )
        
        # Log a processed email
        processor.log_processed_email(test_email_id, "delete", test_analysis)
        print("✓ Email logged to state")
        
        # Check if email is in processed set
        assert test_email_id in processor.processed_emails
        print("✓ Email added to processed set")
        
        # Create new processor instance (simulate restart)
        processor2 = EmailProcessor(config_path)
        
        # Check if state was restored
        assert test_email_id in processor2.processed_emails
        print("✓ State restored after restart")
        
        return True
        
    except Exception as e:
        print(f"✗ State management test failed: {e}")
        return False
    finally:
        os.unlink(config_path)
        # Clean up log file
        if Path("processed_log.jsonl").exists():
            Path("processed_log.jsonl").unlink()

def test_undo_functionality():
    """Test undo capability"""
    print("\\nTesting undo functionality...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Create test email data
        test_email = {
            'id': 'test_undo_email_001',
            'subject': 'Test Email',
            'from': 'test@example.com',
            'date': '2024-01-15',
            'markdown': '# Test Email\\n\\nTest content'
        }
        
        # Execute a delete action
        processor.execute_decision(test_email, "delete")
        print("✓ Delete action executed")
        
        # Check that action was recorded
        recent_actions = processor.get_recent_actions()
        assert len(recent_actions) > 0
        assert recent_actions[-1]['email_id'] == 'test_undo_email_001'
        assert recent_actions[-1]['decision'] == 'delete'
        print("✓ Action recorded for undo")
        
        # Test undo
        undo_success = processor.undo_last_action()
        assert undo_success, "Undo should succeed"
        print("✓ Undo action successful")
        
        # Check that action was removed
        recent_actions_after = processor.get_recent_actions()
        if recent_actions_after:
            assert recent_actions_after[-1]['email_id'] != 'test_undo_email_001'
        print("✓ Action removed from history")
        
        return True
        
    except Exception as e:
        print(f"✗ Undo functionality test failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_error_recovery():
    """Test error recovery mechanisms"""
    print("\\nTesting error recovery...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Test handling of invalid email data
        invalid_email = {'id': 'invalid_email', 'invalid': 'data'}
        
        try:
            # This should not crash the processor
            result = processor.process_single_email(invalid_email)
            print("✓ Processor handled invalid email gracefully")
        except Exception as e:
            print(f"✗ Processor crashed on invalid email: {e}")
            return False
        
        # Test system validation
        issues = processor.validate_setup()
        print(f"✓ System validation completed (found {len(issues)} issues)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error recovery test failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def run_all_tests():
    """Run all end-to-end tests"""
    print("EmailParse V1.0 - End-to-End Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Processor Initialization", test_processor_initialization),
        ("Email Fetching", test_email_fetching),
        ("Email Analysis", test_email_analysis),
        ("State Management", test_state_management),
        ("Undo Functionality", test_undo_functionality),
        ("Error Recovery", test_error_recovery)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\\n[TEST] {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                print(f"[PASS] {test_name}")
                passed += 1
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
    
    print("\\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\\n🎉 All tests passed! Phase 5 is complete and ready for production.")
        print("\\nNext steps:")
        print("1. Run: python email_processor_v1.py --validate")
        print("2. Run: python email_processor_v1.py --max-emails 5")
    else:
        print(f"\\n⚠️ {total-passed} tests failed. Please review and fix issues.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)