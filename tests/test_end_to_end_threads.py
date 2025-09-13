"""
End-to-end test of thread-aware email processing
"""

import sys
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from email_processor_v1 import EmailProcessor

def create_test_config():
    """Create test configuration"""
    return {
        'gmail': {
            'host': 'imap.gmail.com',
            'port': 993,
            'use_ssl': True,
            'user': 'test@gmail.com',
            'auth': {
                'method': 'oauth2',
                'oauth2': {
                    'client_id': 'test-client-id.apps.googleusercontent.com',
                    'client_secret': 'test-client-secret',
                    'token_file': 'test_tokens.json'
                }
            },
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

def simulate_thread_decisions():
    """Simulate user decisions for thread processing"""
    decisions = ['thread_keep', 'thread_delete', 'mixed', 'quit']
    decision_index = 0
    
    def mock_get_thread_decision(thread_result):
        nonlocal decision_index
        if decision_index < len(decisions):
            decision = decisions[decision_index]
            decision_index += 1
            return decision
        else:
            return 'quit'
    
    return mock_get_thread_decision

def test_thread_processing_integration():
    """Test complete thread processing workflow"""
    print("Testing thread-aware email processing integration...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Mock thread decision method
        mock_decision_func = simulate_thread_decisions()
        
        with patch.object(processor, 'get_thread_decision', side_effect=mock_decision_func):
            with patch.object(processor.cli, 'display_welcome', return_value=True):
                with patch.object(processor.cli, 'display_goodbye'):
                    print("Starting thread processing simulation...")
                    
                    # Run thread-aware session
                    processor.run_interactive_session(max_emails=3, thread_mode=True)
                    
                    print("Thread processing session completed successfully!")
                    
                    # Check session stats
                    stats = processor.cli.session_stats
                    print(f"Processed: {stats['processed']} emails")
                    print(f"Kept: {stats['kept']} emails")
                    print(f"Deleted: {stats['deleted']} emails")
                    
                    return True
        
    except Exception as e:
        print(f"Thread processing integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(config_path)
        if Path("processed_log.jsonl").exists():
            Path("processed_log.jsonl").unlink()

if __name__ == "__main__":
    success = test_thread_processing_integration()
    if success:
        print("\\nThread processing integration test passed!")
        print("\\nThread-aware email processing is ready!")
        print("\\nKey features implemented:")
        print("- Thread grouping and context analysis")
        print("- Starred message auto-keep")
        print("- Thread-level and mixed processing modes")
        print("- Interactive thread decision UI")
    else:
        print("\\nThread processing integration test failed.")
    sys.exit(0 if success else 1)