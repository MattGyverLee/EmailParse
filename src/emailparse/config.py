"""Configuration management for EmailParse V1.0"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Configuration-related errors"""
    pass

class Config:
    """Configuration manager with validation and environment variable support"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config file. If None, looks for config/config_v1.yaml
        """
        self.config_path = config_path or self._find_config_file()
        self.data = {}
        self.load()
    
    def _find_config_file(self) -> str:
        """Find the configuration file in standard locations"""
        possible_paths = [
            "config/config_v1.yaml",
            "config_v1.yaml",
            os.path.expanduser("~/.emailparse/config_v1.yaml"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no config found, create from template
        template_path = "config/config_v1.yaml.template"
        if os.path.exists(template_path):
            raise ConfigError(
                f"No configuration file found. Please copy {template_path} to "
                "config/config_v1.yaml and configure your settings."
            )
        
        raise ConfigError(
            "No configuration file found. Please create config/config_v1.yaml"
        )
    
    def load(self):
        """Load configuration from file and apply environment overrides"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}")
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        env_prefix = "EMAILPARSE_"
        
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            
            # Remove prefix and convert to nested dict path
            config_key = key[len(env_prefix):]
            
            # Handle special mappings for known structure
            # Expected format: EMAILPARSE_SECTION_SUBSECTION_KEY
            if config_key.startswith('GMAIL_'):
                section = 'gmail'
                remaining = config_key[6:].lower()  # Remove 'GMAIL_'
            elif config_key.startswith('LMSTUDIO_'):
                section = 'lmstudio'
                remaining = config_key[9:].lower()  # Remove 'LMSTUDIO_'
            elif config_key.startswith('APP_'):
                section = 'app'
                remaining = config_key[4:].lower()  # Remove 'APP_'
            else:
                # Fallback: treat as direct key
                keys = config_key.lower().split('_')
                section = keys[0]
                remaining = '_'.join(keys[1:]) if len(keys) > 1 else ''
            
            # Ensure section exists
            if section not in self.data:
                self.data[section] = {}
            
            if remaining:
                # Handle nested keys like 'model_temperature' -> ['model', 'temperature']
                if remaining in ['log_level', 'resume_from_last', 'email_preview_length', 'show_progress']:
                    # These are direct keys under their section
                    self.data[section][remaining] = self._convert_env_value(value)
                else:
                    # Split on underscore for nested structure
                    nested_keys = remaining.split('_')
                    current = self.data[section]
                    
                    # Navigate to nested location
                    for k in nested_keys[:-1]:
                        if k not in current:
                            current[k] = {}
                        current = current[k]
                    
                    # Set the final value
                    final_key = nested_keys[-1]
                    current[final_key] = self._convert_env_value(value)
            else:
                # Direct section-level override (rare)
                self.data[section] = self._convert_env_value(value)
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer values
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float values
        try:
            return float(value)
        except ValueError:
            pass
        
        # String value (default)
        return value
    
    def _validate(self):
        """Validate required configuration values"""
        required_fields = [
            ('gmail', 'user'),
            ('gmail', 'auth', 'method'),
            ('lmstudio', 'base_url'),
        ]
        
        errors = []
        
        for field_path in required_fields:
            if not self._has_nested_key(field_path):
                field_name = '.'.join(field_path)
                errors.append(f"Missing required configuration: {field_name}")
        
        # Validate auth method
        auth_method = self.get_nested('gmail', 'auth', 'method')
        if auth_method == 'app_password':
            if not self.get_nested('gmail', 'auth', 'app_password'):
                errors.append("App password required when using app_password auth method")
        elif auth_method == 'oauth2':
            oauth_fields = ['client_id', 'client_secret', 'refresh_token']
            for field in oauth_fields:
                if not self.get_nested('gmail', 'auth', 'oauth2', field):
                    errors.append(f"OAuth2 field required: gmail.auth.oauth2.{field}")
        else:
            errors.append(f"Invalid auth method: {auth_method}. Must be 'app_password' or 'oauth2'")
        
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors))
    
    def _has_nested_key(self, keys: tuple) -> bool:
        """Check if nested key exists"""
        try:
            current = self.data
            for key in keys:
                current = current[key]
            return current is not None
        except (KeyError, TypeError):
            return False
    
    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Get nested configuration value"""
        try:
            current = self.data
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_gmail_config(self) -> Dict[str, Any]:
        """Get Gmail configuration"""
        return self.data.get('gmail', {})
    
    def get_lmstudio_config(self) -> Dict[str, Any]:
        """Get LM Studio configuration"""
        return self.data.get('lmstudio', {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration"""
        return self.data.get('app', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get email processing configuration"""
        return self.get_nested('gmail', 'processing', default={})
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        import copy
        return copy.deepcopy(self.data)

def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration (convenience function)"""
    return Config(config_path)

# Global configuration instance
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def reload_config(config_path: Optional[str] = None):
    """Reload global configuration"""
    global _config_instance
    _config_instance = Config(config_path)