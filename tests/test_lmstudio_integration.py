"""
Test script for LM Studio integration
Tests connection and email analysis functionality
"""

import sys
import yaml
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.lmstudio_client import LMStudioClient
from utils.prompt_engine import PromptEngine
from core.email_analyzer import EmailAnalyzer

def load_config():
    """Load configuration for testing"""
    config_path = Path("config/config_v1.yaml")
    if not config_path.exists():
        print("❌ Config file not found. Please copy config_v1.yaml.template to config_v1.yaml")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_lm_studio_connection(config):
    """Test basic LM Studio connection"""
    print("🔍 Testing LM Studio connection...")
    
    client = LMStudioClient(config)
    
    # Test connection
    if client.test_connection():
        print("✅ LM Studio connection successful")
    else:
        print("❌ LM Studio connection failed")
        print("   Make sure LM Studio is running on http://localhost:1234")
        return False
    
    # Get available models
    models = client.get_available_models()
    print(f"📋 Available models: {len(models)}")
    for model in models:
        model_id = model.get('id', 'unknown')
        print(f"   • {model_id}")
    
    return True

def test_prompt_engine():
    """Test prompt engine functionality"""
    print("\\n🔍 Testing Prompt Engine...")
    
    engine = PromptEngine()
    
    # Test prompt loading
    prompt = engine.get_analysis_prompt()
    if len(prompt) > 100:
        print("✅ Prompt loaded successfully")
        print(f"   Prompt length: {len(prompt)} characters")
    else:
        print("❌ Prompt loading failed or prompt too short")
        return False
    
    # Test stats
    stats = engine.get_prompt_stats()
    print(f"   Current version: {stats.get('current_version', 'unknown')}")
    print(f"   Total versions: {stats.get('total_versions', 'unknown')}")
    
    return True

def test_email_analysis(config):
    """Test email analysis with sample email"""
    print("\\n🔍 Testing Email Analysis...")
    
    # Create sample email data
    sample_email = {
        'id': 'test_email_001',
        'subject': 'Flash Sale - 50% Off Everything!',
        'from': 'deals@retailstore.com',
        'date': '2024-01-15',
        'markdown': '''# Flash Sale - 50% Off Everything!

**From:** deals@retailstore.com  
**Date:** January 15, 2024  
**Subject:** Flash Sale - 50% Off Everything!

---

🔥 **FLASH SALE ALERT!** 🔥

Get 50% off EVERYTHING in our store! This incredible deal won't last long.

**Sale Details:**
- Valid until midnight tonight
- No code needed - discount applied at checkout
- Free shipping on orders over $25

Shop now before it's too late!

[SHOP NOW](https://retailstore.com/sale)

---
*This email was sent to customer@email.com. Unsubscribe here.*'''
    }
    
    try:
        analyzer = EmailAnalyzer(config)
        
        # Test system validation
        issues = analyzer.validate_system()
        if issues:
            print("⚠️ System validation issues:")
            for issue in issues:
                print(f"   • {issue}")
        
        # Analyze the sample email
        result = analyzer.analyze_email(sample_email)
        
        if result:
            print("✅ Email analysis successful")
            print(f"   Recommendation: {result.recommendation}")
            print(f"   Category: {result.category}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Reasoning: {result.reasoning}")
            
            if result.key_factors:
                print("   Key factors:")
                for factor in result.key_factors:
                    print(f"     • {factor}")
            
            return True
        else:
            print("❌ Email analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Email analysis error: {e}")
        return False

def test_prompt_improvement(config):
    """Test prompt improvement functionality"""
    print("\\n🔍 Testing Prompt Improvement...")
    
    try:
        client = LMStudioClient(config)
        engine = PromptEngine()
        
        # Sample feedback scenario
        current_prompt = engine.get_analysis_prompt()
        user_feedback = "This is a newsletter I actually read regularly for industry updates"
        email_content = "Weekly Tech Newsletter - AI Industry Updates"
        
        suggestion = client.suggest_prompt_update(
            current_prompt=current_prompt,
            user_feedback=user_feedback,
            email_content=email_content
        )
        
        if suggestion:
            print("✅ Prompt improvement suggestion received")
            print(f"   Suggestion length: {len(suggestion)} characters")
            print(f"   Preview: {suggestion[:200]}...")
            return True
        else:
            print("❌ No prompt improvement suggestion received")
            return False
            
    except Exception as e:
        print(f"❌ Prompt improvement error: {e}")
        return False

def main():
    """Run all tests"""
    print("EmailParse LM Studio Integration Test")
    print("=" * 50)
    
    # Load config
    config = load_config()
    if not config:
        return False
    
    print(f"Config loaded from: config/config_v1.yaml")
    lm_config = config.get('lmstudio', {})
    print(f"LM Studio URL: {lm_config.get('base_url', 'http://localhost:1234')}")
    print(f"Model: {lm_config.get('model', {}).get('name', 'mistral')}")
    
    # Run tests
    tests = [
        ("LM Studio Connection", lambda: test_lm_studio_connection(config)),
        ("Prompt Engine", test_prompt_engine),
        ("Email Analysis", lambda: test_email_analysis(config)),
        ("Prompt Improvement", lambda: test_prompt_improvement(config))
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\\n{'=' * 20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\\n{'=' * 50}")
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\\nAll tests passed! System is ready for use.")
        print("\\nNext steps:")
        print("1. Make sure nous-hermes-2-mistral-7b-dpo is loaded in LM Studio")
        print("2. Run: python email_processor_v1.py --validate")
        print("3. Run: python email_processor_v1.py")
    else:
        print("\\nSome tests failed. Please check the issues above.")
        print("\\nTroubleshooting:")
        print("1. Ensure LM Studio is running on http://localhost:1234")
        print("2. Load nous-hermes-2-mistral-7b-dpo model in LM Studio")
        print("3. Check config/config_v1.yaml settings")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)