"""Tests for configuration management"""

import pytest
import os
import yaml
from unittest.mock import patch, mock_open
from pathlib import Path

from emailparse.config import Config, ConfigError, load_config, get_config, reload_config

class TestConfig:
    """Test cases for Config class"""

    @pytest.mark.unit
    def test_config_loads_from_file(self, sample_config_file):
        """Test that configuration loads correctly from file"""
        config = Config(str(sample_config_file))
        
        assert config.get_nested('gmail', 'user') == 'test@gmail.com'
        assert config.get_nested('gmail', 'port') == 993
        assert config.get_nested('lmstudio', 'base_url') == 'http://localhost:1234'

    @pytest.mark.unit
    def test_config_validation_success(self, sample_config_file):
        """Test that valid configuration passes validation"""
        # Should not raise any exception
        config = Config(str(sample_config_file))
        assert config is not None

    @pytest.mark.unit
    def test_config_validation_missing_required_field(self, temp_dir):
        """Test that missing required fields cause validation error"""
        # Create config without required gmail.user field
        invalid_config = {
            'gmail': {
                'host': 'imap.gmail.com',
                'auth': {'method': 'app_password', 'app_password': 'test123'}
            },
            'lmstudio': {'base_url': 'http://localhost:1234'}
        }
        
        config_file = temp_dir / 'invalid_config.yaml'
        with open(config_file, 'w') as f:
            yaml.safe_dump(invalid_config, f)
        
        with pytest.raises(ConfigError, match="Missing required configuration: gmail.user"):
            Config(str(config_file))

    @pytest.mark.unit
    def test_config_validation_invalid_auth_method(self, temp_dir):
        """Test that invalid auth method causes validation error"""
        invalid_config = {
            'gmail': {
                'user': 'test@gmail.com',
                'auth': {'method': 'invalid_method'}
            },
            'lmstudio': {'base_url': 'http://localhost:1234'}
        }
        
        config_file = temp_dir / 'invalid_auth_config.yaml'
        with open(config_file, 'w') as f:
            yaml.safe_dump(invalid_config, f)
        
        with pytest.raises(ConfigError, match="Invalid auth method"):
            Config(str(config_file))

    @pytest.mark.unit
    def test_config_validation_missing_app_password(self, temp_dir):
        """Test that app_password method without password fails validation"""
        invalid_config = {
            'gmail': {
                'user': 'test@gmail.com',
                'auth': {'method': 'app_password'}  # Missing app_password
            },
            'lmstudio': {'base_url': 'http://localhost:1234'}
        }
        
        config_file = temp_dir / 'missing_password_config.yaml'
        with open(config_file, 'w') as f:
            yaml.safe_dump(invalid_config, f)
        
        with pytest.raises(ConfigError, match="App password required"):
            Config(str(config_file))

    @pytest.mark.unit
    def test_config_validation_oauth2_missing_fields(self, temp_dir):
        """Test that OAuth2 method without required fields fails validation"""
        invalid_config = {
            'gmail': {
                'user': 'test@gmail.com',
                'auth': {
                    'method': 'oauth2',
                    'oauth2': {'client_id': 'test'}  # Missing client_secret and refresh_token
                }
            },
            'lmstudio': {'base_url': 'http://localhost:1234'}
        }
        
        config_file = temp_dir / 'incomplete_oauth_config.yaml'
        with open(config_file, 'w') as f:
            yaml.safe_dump(invalid_config, f)
        
        with pytest.raises(ConfigError, match="OAuth2 field required"):
            Config(str(config_file))

    @pytest.mark.unit
    def test_env_variable_override(self, sample_config_file):
        """Test that environment variables override config file values"""
        with patch.dict(os.environ, {
            'EMAILPARSE_GMAIL_USER': 'override@gmail.com',
            'EMAILPARSE_GMAIL_PORT': '995',
            'EMAILPARSE_APP_LOG_LEVEL': 'DEBUG'
        }):
            config = Config(str(sample_config_file))
            
            assert config.get_nested('gmail', 'user') == 'override@gmail.com'
            assert config.get_nested('gmail', 'port') == 995  # Should be converted to int
            assert config.get_nested('app', 'log_level') == 'DEBUG'

    @pytest.mark.unit
    def test_env_variable_type_conversion(self, sample_config_file):
        """Test that environment variables are converted to appropriate types"""
        with patch.dict(os.environ, {
            'EMAILPARSE_GMAIL_PORT': '993',
            'EMAILPARSE_GMAIL_USE_SSL': 'true',
            'EMAILPARSE_LMSTUDIO_MODEL_TEMPERATURE': '0.7',
            'EMAILPARSE_APP_RESUME_FROM_LAST': 'false'
        }):
            config = Config(str(sample_config_file))
            
            assert config.get_nested('gmail', 'port') == 993
            assert config.get_nested('gmail', 'use_ssl') is True
            assert config.get_nested('lmstudio', 'model', 'temperature') == 0.7
            assert config.get_nested('app', 'resume_from_last') is False

    @pytest.mark.unit
    def test_get_nested_with_default(self, sample_config_file):
        """Test get_nested method with default values"""
        config = Config(str(sample_config_file))
        
        # Existing value
        assert config.get_nested('gmail', 'user') == 'test@gmail.com'
        
        # Non-existing value with default
        assert config.get_nested('gmail', 'nonexistent', default='default_value') == 'default_value'
        
        # Non-existing nested value with default
        assert config.get_nested('nonexistent', 'section', 'key', default=42) == 42

    @pytest.mark.unit
    def test_config_helper_methods(self, sample_config_file):
        """Test configuration helper methods"""
        config = Config(str(sample_config_file))
        
        gmail_config = config.get_gmail_config()
        assert gmail_config['user'] == 'test@gmail.com'
        assert gmail_config['host'] == 'imap.gmail.com'
        
        lmstudio_config = config.get_lmstudio_config()
        assert lmstudio_config['base_url'] == 'http://localhost:1234'
        
        app_config = config.get_app_config()
        assert app_config['log_level'] == 'INFO'
        
        processing_config = config.get_processing_config()
        assert processing_config['batch_size'] == 10
        assert processing_config['mailbox'] == 'INBOX'

    @pytest.mark.unit
    def test_config_file_not_found(self, temp_dir):
        """Test error when configuration file doesn't exist"""
        nonexistent_file = str(temp_dir / 'nonexistent.yaml')
        
        with pytest.raises(ConfigError, match="Configuration file not found"):
            Config(nonexistent_file)

    @pytest.mark.unit
    def test_invalid_yaml_format(self, temp_dir):
        """Test error when configuration file has invalid YAML"""
        invalid_yaml_file = temp_dir / 'invalid.yaml'
        with open(invalid_yaml_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        with pytest.raises(ConfigError, match="Invalid YAML"):
            Config(str(invalid_yaml_file))

    @pytest.mark.unit
    def test_to_dict_method(self, sample_config_file):
        """Test that to_dict returns a copy of configuration"""
        config = Config(str(sample_config_file))
        config_dict = config.to_dict()
        
        # Should contain expected keys
        assert 'gmail' in config_dict
        assert 'lmstudio' in config_dict
        assert 'app' in config_dict
        
        # Should be a copy (modifying shouldn't affect original)
        config_dict['gmail']['user'] = 'modified@gmail.com'
        assert config.get_nested('gmail', 'user') == 'test@gmail.com'

class TestConfigHelperFunctions:
    """Test configuration helper functions"""

    @pytest.mark.unit
    def test_load_config_function(self, sample_config_file):
        """Test load_config convenience function"""
        config = load_config(str(sample_config_file))
        assert isinstance(config, Config)
        assert config.get_nested('gmail', 'user') == 'test@gmail.com'

    @pytest.mark.unit
    @patch('emailparse.config._config_instance', None)
    def test_get_config_singleton(self):
        """Test get_config creates singleton instance"""
        with patch('emailparse.config.Config') as mock_config_class:
            mock_instance = mock_config_class.return_value
            
            # First call should create instance
            config1 = get_config()
            assert config1 is mock_instance
            
            # Second call should return same instance
            config2 = get_config()
            assert config2 is config1
            
            # Config class should only be called once
            mock_config_class.assert_called_once()

    @pytest.mark.unit
    def test_reload_config(self, sample_config_file):
        """Test reload_config function"""
        with patch('emailparse.config._config_instance', None):
            with patch('emailparse.config.Config._find_config_file') as mock_find:
                mock_find.return_value = str(sample_config_file)
                
                # Load initial config
                config1 = get_config()
                
                # Reload with different path
                reload_config(str(sample_config_file))
                config2 = get_config()
                
                # Should be different instances
                assert config1 is not config2