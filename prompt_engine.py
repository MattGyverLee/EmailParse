"""
Prompt Engine for Dynamic Prompt Management
Handles loading, updating, and versioning of email analysis prompts
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

class PromptEngine:
    """Engine for managing email analysis prompts with dynamic updates"""
    
    def __init__(self, prompt_file: str = "MistralPrompt.md"):
        """
        Initialize prompt engine
        
        Args:
            prompt_file: Path to the main prompt file
        """
        self.prompt_file = Path(prompt_file)
        self.prompt_history_dir = Path("prompt_history")
        self.prompt_history_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.current_prompt = ""
        self.prompt_version = 1
        
        # Load initial prompt
        self.load_prompt()
    
    def load_prompt(self) -> str:
        """Load the current prompt from file"""
        try:
            if self.prompt_file.exists():
                self.current_prompt = self.prompt_file.read_text(encoding='utf-8')
                self.logger.info(f"Loaded prompt from {self.prompt_file}")
            else:
                self.logger.error(f"Prompt file {self.prompt_file} not found")
                self.current_prompt = self._get_fallback_prompt()
            
            return self.current_prompt
            
        except Exception as e:
            self.logger.error(f"Failed to load prompt: {e}")
            self.current_prompt = self._get_fallback_prompt()
            return self.current_prompt
    
    def get_analysis_prompt(self) -> str:
        """Get the current analysis prompt for LLM"""
        return self.current_prompt
    
    def save_prompt_version(self, reason: str = "User feedback update") -> str:
        """
        Save current prompt version to history
        
        Args:
            reason: Reason for saving this version
            
        Returns:
            Path to saved version file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_file = self.prompt_history_dir / f"prompt_v{self.prompt_version}_{timestamp}.md"
            
            # Create metadata
            metadata = {
                "version": self.prompt_version,
                "timestamp": timestamp,
                "reason": reason,
                "file_path": str(version_file)
            }
            
            # Save prompt with metadata header
            content = f"""<!-- Prompt Version Metadata
{json.dumps(metadata, indent=2)}
-->

{self.current_prompt}"""
            
            version_file.write_text(content, encoding='utf-8')
            self.logger.info(f"Saved prompt version {self.prompt_version} to {version_file}")
            
            return str(version_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save prompt version: {e}")
            return ""
    
    def update_prompt(self, suggested_improvement: str, user_feedback: str, email_content: str) -> bool:
        """
        Update the prompt based on LLM suggestion and user feedback
        
        Args:
            suggested_improvement: LLM's suggestion for improving the prompt
            user_feedback: User's original feedback
            email_content: Email content that triggered the update
            
        Returns:
            True if prompt was updated successfully
        """
        try:
            # Save current version before updating
            self.save_prompt_version(f"Before update - User feedback: {user_feedback[:100]}...")
            
            # Apply the improvement (this is a simplified version - in practice you'd want more sophisticated merging)
            improvement_log = f"""

---

## Prompt Improvement Log

### Version {self.prompt_version + 1} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**User Feedback:** {user_feedback}

**LLM Suggested Improvement:**
{suggested_improvement}

**Example Email Pattern:**
```
{email_content[:200]}...
```

---
"""
            
            # Add improvement log to the prompt (append at the end)
            self.current_prompt += improvement_log
            
            # Update version
            self.prompt_version += 1
            
            # Save updated prompt to main file
            self.prompt_file.write_text(self.current_prompt, encoding='utf-8')
            
            self.logger.info(f"Updated prompt to version {self.prompt_version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update prompt: {e}")
            return False
    
    def get_prompt_stats(self) -> Dict[str, Any]:
        """Get statistics about prompt versions and updates"""
        try:
            history_files = list(self.prompt_history_dir.glob("prompt_v*.md"))
            
            return {
                "current_version": self.prompt_version,
                "total_versions": len(history_files),
                "prompt_file": str(self.prompt_file),
                "history_dir": str(self.prompt_history_dir),
                "prompt_length": len(self.current_prompt),
                "last_modified": datetime.fromtimestamp(self.prompt_file.stat().st_mtime).isoformat() if self.prompt_file.exists() else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get prompt stats: {e}")
            return {}
    
    def list_prompt_versions(self) -> List[Dict[str, Any]]:
        """List all saved prompt versions"""
        try:
            versions = []
            history_files = sorted(self.prompt_history_dir.glob("prompt_v*.md"))
            
            for file_path in history_files:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Extract metadata if present
                    if content.startswith("<!-- Prompt Version Metadata"):
                        metadata_end = content.find("-->")
                        if metadata_end != -1:
                            metadata_text = content[len("<!-- Prompt Version Metadata"):metadata_end].strip()
                            metadata = json.loads(metadata_text)
                            metadata["file_size"] = file_path.stat().st_size
                            versions.append(metadata)
                    else:
                        # Fallback for files without metadata
                        versions.append({
                            "version": "unknown",
                            "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y%m%d_%H%M%S"),
                            "reason": "No metadata available",
                            "file_path": str(file_path),
                            "file_size": file_path.stat().st_size
                        })
                        
                except Exception as e:
                    self.logger.error(f"Failed to read version file {file_path}: {e}")
                    continue
            
            return versions
            
        except Exception as e:
            self.logger.error(f"Failed to list prompt versions: {e}")
            return []
    
    def _get_fallback_prompt(self) -> str:
        """Get a basic fallback prompt if main prompt file is unavailable"""
        return """
# Basic Email Categorization Prompt

Analyze the provided email and classify it as either:
- **KEEP**: Email should be retained
- **JUNK-CANDIDATE**: Email should be deleted

Respond in JSON format:
```json
{
  "recommendation": "KEEP" | "JUNK-CANDIDATE",
  "category": "Category name",
  "confidence": 0.1-1.0,
  "reasoning": "Brief explanation",
  "key_factors": ["Factor 1", "Factor 2"]
}
```

Focus on identifying outdated, promotional, or irrelevant content for JUNK-CANDIDATE classification.
When uncertain, recommend KEEP.
"""