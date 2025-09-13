"""
Simple test script for LM Studio integration
"""

import sys
import yaml
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from lmstudio_client import LMStudioClient
from prompt_engine import PromptEngine

def load_config():
    """Load configuration for testing"""
    config_path = Path("config/config_v1.yaml")
    if not config_path.exists():
        print("Config file not found. Please copy config_v1.yaml.template to config_v1.yaml")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_lm_studio():
    """Test LM Studio connection and basic functionality"""
    print("Testing LM Studio connection...")
    
    config = load_config()
    if not config:
        return False
    
    client = LMStudioClient(config)
    
    # Test connection
    if client.test_connection():
        print("LM Studio connection successful")
    else:
        print("LM Studio connection failed")
        print("Make sure LM Studio is running on http://localhost:1234")
        return False
    
    # Get available models
    models = client.get_available_models()
    print(f"Available models: {len(models)}")
    for model in models:
        model_id = model.get('id', 'unknown')
        print(f"  - {model_id}")
    
    # Test prompt engine
    print("\\nTesting prompt engine...")
    engine = PromptEngine()
    prompt = engine.get_analysis_prompt()
    print(f"Prompt loaded: {len(prompt)} characters")
    
    # Test simple analysis
    print("\\nTesting email analysis...")
    sample_email = '''# Test Email

**From:** test@example.com  
**Subject:** Test Sale Email  

This is a promotional email about a flash sale.'''
    
    result = client.analyze_email(sample_email, prompt)
    
    if result:
        print("Analysis successful:")
        print(f"  Recommendation: {result.get('recommendation', 'Unknown')}")
        print(f"  Category: {result.get('category', 'Unknown')}")
        print(f"  Confidence: {result.get('confidence', 0)}")
        print(f"  Reasoning: {result.get('reasoning', 'None')}")
        return True
    else:
        print("Analysis failed")
        return False

if __name__ == "__main__":
    success = test_lm_studio()
    if success:
        print("\\nAll tests passed! System is ready.")
    else:
        print("\\nTests failed. Check LM Studio setup.")