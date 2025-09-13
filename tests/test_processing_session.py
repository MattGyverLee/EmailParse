"""
Test a simulated email processing session
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
    """Create a test configuration"""
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
            'log_file': 'logs/test_emailparse.log',
            'email_preview_length': 200
        }
    }

def simulate_user_decisions():
    """Simulate user making decisions"""
    # Return a sequence of decisions: keep, delete, skip, quit
    decisions = ['keep', 'delete', 'skip', 'quit']
    decision_index = 0
    
    def mock_get_user_decision(analysis=None):
        nonlocal decision_index
        if decision_index < len(decisions):
            decision = decisions[decision_index]
            decision_index += 1
            
            # Return format: (decision, feedback, should_update_prompt)
            if decision == 'delete' and analysis and analysis.recommendation == 'KEEP':
                # User disagrees with AI - provide feedback
                return decision, "This is clearly spam", True
            else:
                # User agrees or no strong feedback
                return decision, None, False
        else:
            return 'quit', None, False
    
    return mock_get_user_decision

def test_processing_session():
    """Test a complete processing session"""
    print("Testing complete email processing session...")
    
    config_data = create_test_config()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        processor = EmailProcessor(config_path)
        
        # Mock the CLI user decision method
        mock_decision_func = simulate_user_decisions()
        
        with patch.object(processor.cli, 'get_user_decision', side_effect=mock_decision_func):
            with patch.object(processor.cli, 'display_email'):  # Skip email display
                with patch.object(processor.cli, 'display_welcome', return_value=True):
                    with patch.object(processor.cli, 'display_goodbye'):
                        print("Starting simulated processing session...")
                        
                        # Run processing session
                        processor.run_interactive_session(max_emails=3)
                        
                        print("✓ Processing session completed successfully")
                        
                        # Check session stats
                        stats = processor.cli.session_stats
                        print(f"✓ Processed {stats['processed']} emails")
                        print(f"✓ Kept {stats['kept']} emails")
                        print(f"✓ Deleted {stats['deleted']} emails")
                        
                        # Verify state was saved
                        assert len(processor.processed_emails) > 0
                        print("✓ Email processing state saved")
                        
                        return True
        
    except Exception as e:
        print(f"✗ Processing session failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(config_path)
        # Clean up log file
        if Path("processed_log.jsonl").exists():
            Path("processed_log.jsonl").unlink()

if __name__ == "__main__":
    success = test_processing_session()
    if success:
        print("\\n🎉 Complete processing session test passed!")
        print("Phase 5 is fully complete and functional!")
    else:
        print("\\n❌ Processing session test failed.")
    sys.exit(0 if success else 1)