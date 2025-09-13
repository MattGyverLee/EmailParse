"""
Test thread-aware email processing
"""

import sys
import yaml
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from thread_processor import ThreadProcessor, ThreadMessage
from thread_analyzer import ThreadAnalyzer
from email_analyzer import EmailAnalyzer

def create_test_config():
    """Create test configuration"""
    return {
        'lmstudio': {
            'base_url': 'http://localhost:1234',
            'model': {'name': 'mistral', 'temperature': 0.3, 'max_tokens': 500}
        },
        'app': {
            'log_level': 'INFO'
        }
    }

def test_thread_grouping():
    """Test email grouping by threads"""
    print("Testing thread grouping...")
    
    config = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        analyzer = EmailAnalyzer(config)
        thread_processor = ThreadProcessor(analyzer.lm_client, analyzer.prompt_engine)
        
        # Create test emails with thread information
        test_emails = [
            {
                'id': 'msg_001',
                'subject': 'Project Discussion',
                'from': 'alice@company.com',
                'date': '2024-01-15T10:00:00',
                'body': 'Let\'s discuss the new project requirements.',
                'thread_id': 'thread_123',
                'is_starred': False,
                'labels': ['INBOX']
            },
            {
                'id': 'msg_002', 
                'subject': 'Re: Project Discussion',
                'from': 'bob@company.com',
                'date': '2024-01-15T11:00:00',
                'body': 'I agree with the timeline you proposed.',
                'thread_id': 'thread_123',
                'is_starred': True,  # This message is starred
                'labels': ['INBOX', 'STARRED']
            },
            {
                'id': 'msg_003',
                'subject': 'Flash Sale Announcement',
                'from': 'deals@store.com', 
                'date': '2024-01-15T12:00:00',
                'body': 'Get 50% off everything today only!',
                'thread_id': 'thread_456',
                'is_starred': False,
                'labels': ['INBOX']
            }
        ]
        
        # Test grouping
        thread_groups = thread_processor.group_emails_by_thread(test_emails)
        
        assert len(thread_groups) == 2, f"Expected 2 threads, got {len(thread_groups)}"
        assert 'thread_123' in thread_groups, "Missing thread_123"
        assert 'thread_456' in thread_groups, "Missing thread_456"
        assert len(thread_groups['thread_123']) == 2, "Thread 123 should have 2 messages"
        assert len(thread_groups['thread_456']) == 1, "Thread 456 should have 1 message"
        
        print("  Thread grouping: PASS")
        
        # Test starred message detection
        starred_thread_emails = thread_groups['thread_123']
        has_starred = any(thread_processor._is_message_starred(email) for email in starred_thread_emails)
        assert has_starred, "Should detect starred message in thread"
        print("  Starred detection: PASS")
        
        return True
        
    except Exception as e:
        print(f"  Thread grouping failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_thread_message_conversion():
    """Test conversion to ThreadMessage objects"""
    print("\\nTesting ThreadMessage conversion...")
    
    config = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        analyzer = EmailAnalyzer(config)
        thread_processor = ThreadProcessor(analyzer.lm_client, analyzer.prompt_engine)
        
        test_emails = [
            {
                'id': 'msg_001',
                'subject': 'Test Subject',
                'from': 'test@example.com',
                'date': '2024-01-15T10:00:00',
                'body': 'Test message body',
                'markdown': '# Test\\n\\nTest message',
                'is_starred': True,
                'labels': ['INBOX', 'STARRED']
            }
        ]
        
        thread_messages = thread_processor.convert_to_thread_messages(test_emails)
        
        assert len(thread_messages) == 1, "Should convert 1 email"
        
        msg = thread_messages[0]
        assert msg.message_id == 'msg_001'
        assert msg.subject == 'Test Subject'
        assert msg.sender == 'test@example.com'
        assert msg.is_starred == True
        assert 'STARRED' in msg.labels
        assert isinstance(msg.date, datetime)
        
        print("  ThreadMessage conversion: PASS")
        return True
        
    except Exception as e:
        print(f"  ThreadMessage conversion failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_starred_auto_keep():
    """Test auto-keep logic for starred messages"""
    print("\\nTesting starred message auto-keep...")
    
    config = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        analyzer = EmailAnalyzer(config)
        thread_analyzer = ThreadAnalyzer(analyzer.lm_client, analyzer.prompt_engine)
        
        # Create thread with starred message
        thread_messages = [
            ThreadMessage(
                message_id='msg_001',
                subject='Important Discussion',
                sender='boss@company.com',
                date=datetime.now(),
                body='This is important',
                markdown='# Important\\n\\nThis is important',
                is_starred=False,
                labels=['INBOX']
            ),
            ThreadMessage(
                message_id='msg_002',
                subject='Re: Important Discussion', 
                sender='me@company.com',
                date=datetime.now(),
                body='I agree',
                markdown='# Re: Important\\n\\nI agree',
                is_starred=True,  # This message is starred
                labels=['INBOX', 'STARRED']
            )
        ]
        
        # Analyze thread
        result = thread_analyzer.analyze_thread(thread_messages)
        
        # Should auto-keep due to starred message
        assert result.has_starred_messages == True, "Should detect starred messages"
        assert result.thread_recommendation == "KEEP_THREAD", "Should auto-keep starred thread"
        assert result.thread_confidence == 1.0, "Auto-keep should have 100% confidence"
        
        # All messages should be marked as KEEP
        for message_id, decision in result.message_decisions.items():
            assert decision.recommendation == "KEEP", f"Message {message_id} should be kept"
            assert "starred" in decision.reasoning.lower(), "Should mention starred in reasoning"
        
        print("  Starred auto-keep: PASS")
        return True
        
    except Exception as e:
        print(f"  Starred auto-keep failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def test_thread_context_analysis():
    """Test thread context analysis (requires LM Studio)"""
    print("\\nTesting thread context analysis...")
    
    config = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        analyzer = EmailAnalyzer(config)
        
        # Test connection first
        if not analyzer.lm_client.test_connection():
            print("  Skipping - LM Studio not available")
            return True
        
        thread_analyzer = ThreadAnalyzer(analyzer.lm_client, analyzer.prompt_engine)
        
        # Create a marketing thread (should be deleted)
        marketing_thread = [
            ThreadMessage(
                message_id='marketing_001',
                subject='Special Offer Just for You!',
                sender='deals@retailstore.com',
                date=datetime.now(),
                body='Limited time offer - 50% off everything!',
                markdown='# Special Offer\\n\\nLimited time offer - 50% off everything!',
                is_starred=False,
                labels=['INBOX']
            )
        ]
        
        result = thread_analyzer.analyze_thread(marketing_thread)
        
        # Should recommend deletion for marketing
        assert result.thread_recommendation in ["DELETE_THREAD", "MIXED"], "Marketing should be deleted or mixed"
        assert len(result.message_decisions) == 1, "Should have 1 message decision"
        
        print(f"  Marketing thread: {result.thread_recommendation} (confidence: {result.thread_confidence:.2f})")
        print("  Thread context analysis: PASS")
        return True
        
    except Exception as e:
        print(f"  Thread context analysis failed: {e}")
        return False
    finally:
        os.unlink(config_path)

def main():
    """Run all thread processing tests"""
    print("Thread-Aware Email Processing Tests")
    print("=" * 50)
    
    tests = [
        test_thread_grouping,
        test_thread_message_conversion,
        test_starred_auto_keep,
        test_thread_context_analysis
    ]
    
    passed = 0
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"Test {test_func.__name__} failed: {e}")
    
    print("\\n" + "=" * 50)
    print("THREAD PROCESSING TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("\\nAll thread processing tests passed!")
        print("\\nThread Processing Features:")
        print("- Emails grouped by thread ID")
        print("- Starred messages trigger auto-keep for entire thread")
        print("- Thread context analysis with LLM")
        print("- Individual and thread-level decisions")
        print("- Only tagging operations (no deletion)")
    else:
        print("\\nSome thread processing tests failed.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)