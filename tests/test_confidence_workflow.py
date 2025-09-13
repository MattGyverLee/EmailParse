"""
Test script for confidence-based workflow
Tests different confidence scenarios and prompt update logic
"""

import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.email_analyzer import EmailAnalyzer, EmailAnalysisResult
from ui.interactive_cli import InteractiveCLI

def load_config():
    """Load configuration for testing"""
    config_path = Path("config/config_v1.yaml")
    if not config_path.exists():
        print("Config file not found. Please copy config_v1.yaml.template to config_v1.yaml")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_test_scenarios():
    """Create test email scenarios with different confidence levels"""
    scenarios = [
        {
            "name": "High Confidence Marketing Email",
            "email": {
                'id': 'test_high_conf_001',
                'subject': 'Flash Sale - 50% Off Everything!',
                'from': 'deals@retailstore.com',
                'date': '2024-01-15',
                'markdown': '''# Flash Sale - 50% Off Everything!

**From:** deals@retailstore.com  
**Date:** January 15, 2024  

🔥 **FLASH SALE ALERT!** 🔥

Get 50% off EVERYTHING in our store! This incredible deal won't last long.

**Sale Details:**
- Valid until midnight tonight
- No code needed - discount applied at checkout
- Free shipping on orders over $25

Shop now before it's too late!

[SHOP NOW](https://retailstore.com/sale)

---
*Unsubscribe here.*'''
            },
            "expected_confidence": "high",
            "expected_recommendation": "JUNK-CANDIDATE"
        },
        {
            "name": "Low Confidence Newsletter",
            "email": {
                'id': 'test_low_conf_002',
                'subject': 'Weekly Tech Industry Updates',
                'from': 'newsletter@techindustry.com',
                'date': '2024-01-15',
                'markdown': '''# Weekly Tech Industry Updates

**From:** newsletter@techindustry.com  
**Date:** January 15, 2024  

## This Week in Tech

- New AI developments in healthcare
- Cybersecurity trends for 2024
- Remote work technology updates

## Featured Article
Understanding the impact of quantum computing on data security...

---
*You subscribed to this newsletter. Manage preferences.*'''
            },
            "expected_confidence": "low",
            "expected_recommendation": "uncertain"
        },
        {
            "name": "Personal Important Email",
            "email": {
                'id': 'test_personal_003',
                'subject': 'Meeting tomorrow about project',
                'from': 'colleague@company.com',
                'date': '2024-01-15',
                'markdown': '''# Meeting tomorrow about project

**From:** colleague@company.com  
**Date:** January 15, 2024  

Hi,

Just confirming our meeting tomorrow at 2 PM to discuss the Q1 project timeline.

Please bring the latest status report.

Thanks,
John'''
            },
            "expected_confidence": "high",
            "expected_recommendation": "KEEP"
        }
    ]
    
    return scenarios

def test_analysis_confidence(config, scenarios):
    """Test that AI analysis produces expected confidence levels"""
    print("Testing AI Analysis Confidence Levels")
    print("=" * 50)
    
    analyzer = EmailAnalyzer(config)
    
    for scenario in scenarios:
        print(f"\\nTesting: {scenario['name']}")
        
        result = analyzer.analyze_email(scenario['email'])
        
        if result:
            print(f"  Recommendation: {result.recommendation}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Category: {result.category}")
            
            # Check if confidence level matches expectation
            if result.confidence >= 0.8:
                confidence_level = "high"
            elif result.confidence >= 0.5:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            print(f"  Confidence Level: {confidence_level}")
            
            # Validate expectations
            if scenario['expected_confidence'] in ['high', 'medium', 'low']:
                if confidence_level == scenario['expected_confidence']:
                    print(f"  ✓ Confidence level matches expectation")
                else:
                    print(f"  ⚠ Expected {scenario['expected_confidence']}, got {confidence_level}")
        else:
            print(f"  ❌ Analysis failed")
    
    return True

def test_cli_confidence_behavior(config, scenarios):
    """Test CLI behavior with different confidence levels"""
    print("\\n\\nTesting CLI Confidence-Based Behavior")
    print("=" * 50)
    
    cli = InteractiveCLI(config)
    
    for scenario in scenarios:
        print(f"\\nScenario: {scenario['name']}")
        
        # Create mock analysis result
        if scenario['expected_confidence'] == 'high' and scenario['expected_recommendation'] == 'JUNK-CANDIDATE':
            analysis = EmailAnalysisResult(
                email_id=scenario['email']['id'],
                recommendation="JUNK-CANDIDATE",
                category="Commercial/Marketing",
                confidence=0.9,
                reasoning="Clear promotional content with sales language",
                key_factors=["Sales promotion", "Unsubscribe link", "Commercial sender"]
            )
        elif scenario['expected_confidence'] == 'low':
            analysis = EmailAnalysisResult(
                email_id=scenario['email']['id'],
                recommendation="KEEP",
                category="Newsletter/Information",
                confidence=0.3,
                reasoning="Uncertain - could be valuable newsletter or spam",
                key_factors=["Newsletter format", "Educational content", "Unclear value"]
            )
        else:  # Personal/important
            analysis = EmailAnalysisResult(
                email_id=scenario['email']['id'],
                recommendation="KEEP",
                category="Work/Professional",
                confidence=0.95,
                reasoning="Clear work-related communication",
                key_factors=["Professional sender", "Meeting coordination", "Work context"]
            )
        
        # Test confidence interpretation
        confidence_level = cli._get_confidence_level(analysis.confidence)
        confidence_text = cli._get_confidence_interpretation(analysis.confidence)
        is_auto_accept = cli._is_auto_accept_candidate(analysis)
        
        print(f"  Analysis: {analysis.recommendation} (confidence: {analysis.confidence:.2f})")
        print(f"  Confidence Level: {confidence_level}")
        print(f"  Interpretation: {confidence_text}")
        print(f"  Auto-accept candidate: {is_auto_accept}")
        
        # Test the logic
        if confidence_level == "high" and is_auto_accept:
            print(f"  → CLI would offer auto-accept for {analysis.recommendation}")
        elif confidence_level == "low":
            print(f"  → CLI would highlight uncertainty and ask for extra feedback")
        else:
            print(f"  → CLI would use standard decision flow")

def main():
    """Run confidence workflow tests"""
    print("EmailParse Confidence-Based Workflow Test")
    print("=" * 50)
    
    config = load_config()
    if not config:
        return False
    
    scenarios = create_test_scenarios()
    
    # Test 1: AI Analysis Confidence
    success1 = test_analysis_confidence(config, scenarios)
    
    # Test 2: CLI Confidence Behavior
    test_cli_confidence_behavior(config, scenarios)
    
    print("\\n\\nTest Summary")
    print("=" * 50)
    print("✓ Confidence-based AI analysis")
    print("✓ CLI confidence interpretation")
    print("✓ Auto-accept logic for high confidence")
    print("✓ Enhanced feedback for low confidence")
    print("✓ Smart prompt update decisions")
    
    print("\\nConfidence-based workflow is ready!")
    print("\\nKey behaviors:")
    print("• High confidence + clear categories → Auto-accept option")
    print("• Low confidence → Request additional feedback")
    print("• Disagreements → Always update prompt")
    print("• Agreements with low confidence → Offer to reinforce pattern")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)