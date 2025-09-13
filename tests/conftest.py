"""Test configuration and fixtures for EmailParse"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
import yaml

# Add project root to Python path for testing
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.config import Config

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests"""
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
                'batch_size': 10,
                'mailbox': 'INBOX',
                'junk_folder': 'Junk-Candidate'
            }
        },
        'lmstudio': {
            'base_url': 'http://localhost:1234',
            'timeout': 30,
            'model': {
                'name': 'mistral',
                'temperature': 0.3,
                'max_tokens': 500
            }
        },
        'app': {
            'log_level': 'INFO',
            'resume_from_last': True
        }
    }

@pytest.fixture
def sample_config_file(temp_dir, sample_config_data):
    """Create a sample config file for testing"""
    config_file = temp_dir / 'config_v1.yaml'
    with open(config_file, 'w') as f:
        yaml.safe_dump(sample_config_data, f)
    return config_file

@pytest.fixture
def mock_config(sample_config_data):
    """Mock configuration object"""
    config = Mock(spec=Config)
    config.data = sample_config_data
    config.get_nested = Mock(side_effect=lambda *keys, default=None: _get_nested_value(sample_config_data, keys, default))
    config.get_gmail_config = Mock(return_value=sample_config_data['gmail'])
    config.get_lmstudio_config = Mock(return_value=sample_config_data['lmstudio'])
    config.get_app_config = Mock(return_value=sample_config_data['app'])
    config.get_processing_config = Mock(return_value=sample_config_data['gmail']['processing'])
    config.to_dict = Mock(return_value=sample_config_data.copy())
    return config

def _get_nested_value(data, keys, default):
    """Helper function to get nested values from dict"""
    try:
        current = data
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

@pytest.fixture
def mock_email():
    """Sample email data for testing"""
    return {
        'uid': 12345,
        'subject': 'Test Email Subject',
        'from': ['sender@example.com'],
        'to': ['recipient@example.com'],
        'date': '2025-01-15 10:30:00',
        'size': 1024,
        'body': 'This is a test email body with some content for testing purposes.',
        'headers': {
            'Message-ID': '<test@example.com>',
            'Content-Type': 'text/plain'
        }
    }

@pytest.fixture
def sample_emails():
    """List of sample emails for batch testing"""
    emails = []
    for i in range(5):
        emails.append({
            'uid': 10000 + i,
            'subject': f'Test Email {i+1}',
            'from': [f'sender{i+1}@example.com'],
            'to': ['recipient@example.com'],
            'date': f'2025-01-{15+i:02d} 10:30:00',
            'size': 1024 + i * 100,
            'body': f'This is test email {i+1} body content.',
            'headers': {
                'Message-ID': f'<test{i+1}@example.com>',
                'Content-Type': 'text/plain'
            }
        })
    return emails

@pytest.fixture
def mock_imap_client():
    """Mock IMAP client for testing"""
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    mock_client.login.return_value = True
    mock_client.select_folder.return_value = True
    mock_client.fetch_emails.return_value = []
    mock_client.tag_email.return_value = True
    mock_client.move_email.return_value = True
    mock_client.close.return_value = True
    return mock_client

@pytest.fixture
def mock_lmstudio_client():
    """Mock LM Studio client for testing"""
    mock_client = MagicMock()
    mock_client.analyze_email.return_value = {
        'recommendation': 'KEEP',
        'confidence': 0.85,
        'reasoning': 'This appears to be a legitimate email based on sender and content.'
    }
    return mock_client

# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.requires_gmail = pytest.mark.requires_gmail
pytest.mark.requires_lmstudio = pytest.mark.requires_lmstudio