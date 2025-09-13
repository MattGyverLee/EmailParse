"""
Test UID tracking and duplicate prevention
"""

import sys
import yaml
import tempfile
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from email_processor_v1 import EmailProcessor
from email_analyzer import EmailAnalysisResult

def create_test_config():
    """Create a test configuration"""
    return {
        'gmail': {
            'processing': {
                'batch_size': 5,
                'junk_folder': 'Junk-Candidate'
            }
        },
        'lmstudio': {
            'base_url': 'http://localhost:1234',
            'model': {'name': 'mistral', 'temperature': 0.3, 'max_tokens': 500}
        },
        'app': {
            'log_level': 'INFO',
            'log_file': 'logs/test_emailparse.log'
        }
    }

def test_uid_tracking():
    """Test that UIDs are properly tracked and prevent duplicate processing"""
    print("Testing UID tracking and duplicate prevention...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Test 1: Check initial state
        print("\\n1. Testing initial state...")
        assert len(processor.processed_emails) == 0
        print("   Initial processed emails set is empty: PASS")
        
        # Test 2: Fetch emails and check UIDs
        print("\\n2. Testing email fetching and UID format...")
        emails = processor.fetch_unprocessed_emails(limit=3)
        
        assert len(emails) > 0, "Should fetch at least one email"
        print(f"   Fetched {len(emails)} emails")
        
        for i, email in enumerate(emails):
            email_id = email.get('id')
            assert email_id is not None, f"Email {i} missing ID"
            assert isinstance(email_id, str), f"Email {i} ID should be string"
            assert len(email_id) > 0, f"Email {i} ID should not be empty"
            print(f"   Email {i}: ID='{email_id}' (type: {type(email_id).__name__})")
        
        # Test 3: Log a processed email
        print("\\n3. Testing email processing and logging...")
        test_email = emails[0]
        test_email_id = test_email['id']
        
        # Create mock analysis
        mock_analysis = EmailAnalysisResult(
            email_id=test_email_id,
            recommendation="KEEP",
            category="Test",
            confidence=0.8,
            reasoning="Test email",
            key_factors=["Test"]
        )
        
        # Log the email as processed
        processor.log_processed_email(test_email_id, "keep", mock_analysis, "Test feedback")
        
        # Verify it's in the processed set
        assert test_email_id in processor.processed_emails
        print(f"   Email {test_email_id} added to processed set: PASS")
        
        # Test 4: Check log file format
        print("\\n4. Testing processed log file format...")
        log_file = Path(processor.processed_log_file)
        assert log_file.exists(), "Processed log file should exist"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read().strip()
            assert len(log_content) > 0, "Log file should not be empty"
            
            # Parse the log entry
            log_entry = json.loads(log_content)
            assert log_entry['email_id'] == test_email_id
            assert log_entry['decision'] == 'keep'
            assert 'timestamp' in log_entry
            assert 'ai_analysis' in log_entry
            
            print(f"   Log entry format valid: PASS")
            print(f"   Log entry: {json.dumps(log_entry, indent=2)}")
        
        # Test 5: Test duplicate prevention
        print("\\n5. Testing duplicate prevention...")
        
        # Fetch emails again - should exclude the processed one
        unprocessed_emails_2 = processor.fetch_unprocessed_emails(limit=5)
        
        # Should not include the processed email
        unprocessed_ids = [email.get('id') for email in unprocessed_emails_2]
        assert test_email_id not in unprocessed_ids
        print(f"   Processed email {test_email_id} excluded from new fetch: PASS")
        
        # Test 6: Test resume functionality
        print("\\n6. Testing resume functionality...")
        
        # Create new processor instance (simulates restart)
        processor2 = EmailProcessor(config_path)
        
        # Should load the processed email from log
        assert test_email_id in processor2.processed_emails
        print(f"   Processed email {test_email_id} restored after restart: PASS")
        
        # Fetch should still exclude the processed email
        unprocessed_emails_3 = processor2.fetch_unprocessed_emails(limit=5)
        unprocessed_ids_3 = [email.get('id') for email in unprocessed_emails_3]
        assert test_email_id not in unprocessed_ids_3
        print(f"   Duplicate prevention works after restart: PASS")
        
        # Test 7: Test with Gmail-style UIDs
        print("\\n7. Testing with realistic Gmail UIDs...")
        
        # Simulate Gmail-style message IDs
        gmail_style_ids = [
            "18c2a4e5f1234567",  # Real Gmail IDs are hex strings
            "18c2a4e5f7890abc", 
            "18c2a4e5fdef0123"
        ]
        
        for gmail_id in gmail_style_ids:
            processor2.log_processed_email(gmail_id, "delete", None, None)
            assert gmail_id in processor2.processed_emails
        
        print(f"   Gmail-style UIDs processed correctly: PASS")
        
        return True
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        os.unlink(config_path)
        if Path("processed_log.jsonl").exists():
            Path("processed_log.jsonl").unlink()

def test_uid_format_validation():
    """Test that we handle different UID formats correctly"""
    print("\\nTesting UID format validation...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Test various UID formats
        test_cases = [
            ("gmail_real", "18c2a4e5f1234567"),
            ("gmail_long", "18c2a4e5f1234567890abcdef"),
            ("mock_format", "mock_email_001"),
            ("numeric", "12345"),
            ("uuid_style", "550e8400-e29b-41d4-a716-446655440000"),
        ]
        
        for test_name, uid in test_cases:
            # Log the UID
            processor.log_processed_email(uid, "test", None, f"Test {test_name}")
            
            # Verify it's tracked
            assert uid in processor.processed_emails
            print(f"   {test_name}: '{uid}' - TRACKED")
        
        # Create new processor and verify all UIDs are restored
        processor2 = EmailProcessor(config_path)
        for test_name, uid in test_cases:
            assert uid in processor2.processed_emails
            print(f"   {test_name}: '{uid}' - RESTORED")
        
        print("   All UID formats handled correctly: PASS")
        return True
        
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
        
    finally:
        os.unlink(config_path)
        if Path("processed_log.jsonl").exists():
            Path("processed_log.jsonl").unlink()

def main():
    """Run UID tracking tests"""
    print("EmailParse UID Tracking Tests")
    print("=" * 50)
    
    tests = [
        test_uid_tracking,
        test_uid_format_validation
    ]
    
    passed = 0
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"Test failed: {e}")
    
    print("\\n" + "=" * 50)
    print("UID TRACKING TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("\\nAll UID tracking tests passed!")
        print("\\nUID Tracking Features Verified:")
        print("- Unique email IDs properly tracked")
        print("- Duplicate processing prevented")
        print("- State persists across restarts")
        print("- Multiple UID formats supported")
        print("- JSONL log format correct")
    else:
        print("\\nSome UID tracking tests failed.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)