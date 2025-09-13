"""
Test prompt diff functionality
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from interactive_cli import InteractiveCLI

def test_prompt_diff():
    """Test the prompt diff display functionality"""
    print("Testing prompt diff display...")
    
    # Create mock config
    config = {
        'app': {
            'email_preview_length': 500,
            'show_progress': True
        }
    }
    
    cli = InteractiveCLI(config)
    
    # Test with sample prompt changes
    old_prompt = """# Email Categorization Prompt

## Instructions
Analyze emails and categorize them.

## Categories
- KEEP: Important emails
- JUNK-CANDIDATE: Spam emails

## Response Format
Respond in JSON format with recommendation."""
    
    new_prompt = """# Email Categorization Prompt

## Instructions
Analyze emails and categorize them using advanced logic.

## Categories
- KEEP: Important emails  
- JUNK-CANDIDATE: Spam emails
- NEWSLETTER: Marketing newsletters

## Response Format
Respond in JSON format with recommendation and confidence score.

## Special Rules
- Always err on the side of caution
- Consider sender reputation"""
    
    print("\\nTesting prompt diff generation...")
    
    try:
        # Test the diff functionality
        cli.show_prompt_diff(old_prompt, new_prompt)
        print("Prompt diff functionality working!")
        return True
        
    except Exception as e:
        print(f"Prompt diff test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_prompt_diff()
    if success:
        print("\\nPrompt diff testing completed successfully!")
    else:
        print("\\nPrompt diff testing failed.")