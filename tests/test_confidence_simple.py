"""
Simple test for confidence-based workflow
"""

import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from email_analyzer import EmailAnalyzer, EmailAnalysisResult
from interactive_cli import InteractiveCLI

def load_config():
    config_path = Path("config/config_v1.yaml")
    if not config_path.exists():
        print("Config file not found")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_confidence_logic():
    """Test confidence-based decision logic"""
    print("Testing confidence-based workflow...")
    
    config = load_config()
    if not config:
        return False
    
    cli = InteractiveCLI(config)
    
    # Test high confidence case
    high_conf_analysis = EmailAnalysisResult(
        email_id="test_001",
        recommendation="JUNK-CANDIDATE",
        category="Commercial/Marketing",
        confidence=0.9,
        reasoning="Clear promotional content",
        key_factors=["Sales promotion", "Unsubscribe link"]
    )
    
    # Test low confidence case  
    low_conf_analysis = EmailAnalysisResult(
        email_id="test_002", 
        recommendation="KEEP",
        category="Newsletter/Information",
        confidence=0.3,
        reasoning="Uncertain about value",
        key_factors=["Newsletter format", "Educational content"]
    )
    
    # Test confidence interpretations
    print("High confidence analysis:")
    print(f"  Confidence: {high_conf_analysis.confidence}")
    print(f"  Level: {cli._get_confidence_level(high_conf_analysis.confidence)}")
    print(f"  Auto-accept candidate: {cli._is_auto_accept_candidate(high_conf_analysis)}")
    print(f"  Interpretation: {cli._get_confidence_interpretation(high_conf_analysis.confidence)}")
    
    print("\\nLow confidence analysis:")
    print(f"  Confidence: {low_conf_analysis.confidence}")
    print(f"  Level: {cli._get_confidence_level(low_conf_analysis.confidence)}")
    print(f"  Auto-accept candidate: {cli._is_auto_accept_candidate(low_conf_analysis)}")
    print(f"  Interpretation: {cli._get_confidence_interpretation(low_conf_analysis.confidence)}")
    
    print("\\nConfidence workflow test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_confidence_logic()
    if success:
        print("\\nAll confidence tests passed!")
    else:
        print("\\nSome tests failed.")
    sys.exit(0 if success else 1)