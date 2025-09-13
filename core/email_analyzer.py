"""
Email Analysis Pipeline
Orchestrates Gmail API, LM Studio, and Prompt Engine for email classification
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from clients.lmstudio_client import LMStudioClient
from utils.prompt_engine import PromptEngine

@dataclass
class EmailAnalysisResult:
    """Result of email analysis"""
    email_id: str
    recommendation: str  # KEEP or JUNK-CANDIDATE
    category: str
    confidence: float
    reasoning: str
    key_factors: List[str]
    red_flags: List[str] = None
    analysis_timestamp: str = None
    model_used: str = None
    
    def __post_init__(self):
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now().isoformat()
        if self.red_flags is None:
            self.red_flags = []

class EmailAnalyzer:
    """Main email analysis pipeline"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.lm_client = LMStudioClient(config)
        self.prompt_engine = PromptEngine()
        
        # Test LM Studio connection
        if not self.lm_client.test_connection():
            self.logger.warning("LM Studio connection failed - analysis will not work")
    
    def analyze_email(self, email_data: Dict[str, Any]) -> Optional[EmailAnalysisResult]:
        """
        Analyze a single email using LM Studio
        
        Args:
            email_data: Email data with 'id', 'markdown', and other metadata
            
        Returns:
            EmailAnalysisResult or None if analysis failed
        """
        try:
            email_id = email_data.get('id', 'unknown')
            email_markdown = email_data.get('markdown', '')
            
            if not email_markdown:
                self.logger.error(f"No markdown content for email {email_id}")
                return None
            
            # Get current prompt
            prompt = self.prompt_engine.get_analysis_prompt()
            
            # Analyze with LM Studio
            self.logger.info(f"Analyzing email {email_id} with LM Studio")
            raw_result = self.lm_client.analyze_email(email_markdown, prompt)
            
            if not raw_result:
                self.logger.error(f"LM Studio analysis failed for email {email_id}")
                return None
            
            # Convert to structured result
            result = EmailAnalysisResult(
                email_id=email_id,
                recommendation=raw_result.get('recommendation', 'KEEP'),
                category=raw_result.get('category', 'Unknown'),
                confidence=float(raw_result.get('confidence', 0.5)),
                reasoning=raw_result.get('reasoning', 'No reasoning provided'),
                key_factors=raw_result.get('key_factors', []),
                red_flags=raw_result.get('red_flags', []),
                model_used=self.lm_client.model_name
            )
            
            # Validate recommendation
            if result.recommendation not in ['KEEP', 'JUNK-CANDIDATE']:
                self.logger.warning(f"Invalid recommendation '{result.recommendation}' for email {email_id}, defaulting to KEEP")
                result.recommendation = 'KEEP'
            
            # Validate confidence
            if not 0.0 <= result.confidence <= 1.0:
                self.logger.warning(f"Invalid confidence {result.confidence} for email {email_id}, defaulting to 0.5")
                result.confidence = 0.5
            
            self.logger.info(f"Email {email_id} analyzed: {result.recommendation} (confidence: {result.confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze email {email_id}: {e}")
            return None
    
    def analyze_batch(self, emails: List[Dict[str, Any]]) -> List[EmailAnalysisResult]:
        """
        Analyze a batch of emails
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            List of EmailAnalysisResult objects
        """
        results = []
        
        for i, email in enumerate(emails, 1):
            self.logger.info(f"Analyzing email {i}/{len(emails)}")
            
            result = self.analyze_email(email)
            if result:
                results.append(result)
            else:
                self.logger.warning(f"Skipping email {email.get('id', 'unknown')} due to analysis failure")
        
        self.logger.info(f"Completed analysis of {len(results)}/{len(emails)} emails")
        return results
    
    def update_prompt_from_feedback(self, email_data: Dict[str, Any], user_feedback: str, 
                                  original_analysis: EmailAnalysisResult) -> bool:
        """
        Update the prompt based on user feedback
        
        Args:
            email_data: The email that was misclassified
            user_feedback: User's explanation for their decision
            original_analysis: Original LLM analysis result
            
        Returns:
            True if prompt was updated successfully
        """
        try:
            self.logger.info("Requesting prompt improvement from LLM")
            
            # Get current prompt
            current_prompt = self.prompt_engine.get_analysis_prompt()
            email_markdown = email_data.get('markdown', '')
            
            # Ask LLM for improvement suggestion
            suggestion = self.lm_client.suggest_prompt_update(
                current_prompt=current_prompt,
                user_feedback=user_feedback,
                email_content=email_markdown
            )
            
            if suggestion:
                self.logger.info("Received prompt improvement suggestion from LLM")
                
                # Update the prompt
                success = self.prompt_engine.update_prompt(
                    suggested_improvement=suggestion,
                    user_feedback=user_feedback,
                    email_content=email_markdown
                )
                
                if success:
                    self.logger.info("Prompt updated successfully")
                    return True
                else:
                    self.logger.error("Failed to update prompt")
                    return False
            else:
                self.logger.warning("No improvement suggestion received from LLM")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update prompt from feedback: {e}")
            return False
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get statistics about the analysis system"""
        try:
            # Test LM Studio connection
            lm_connected = self.lm_client.test_connection()
            
            # Get prompt stats
            prompt_stats = self.prompt_engine.get_prompt_stats()
            
            return {
                "lm_studio": {
                    "connected": lm_connected,
                    "base_url": self.lm_client.base_url,
                    "model_name": self.lm_client.model_name,
                    "temperature": self.lm_client.temperature,
                    "max_tokens": self.lm_client.max_tokens
                },
                "prompt_engine": prompt_stats,
                "system_status": "ready" if lm_connected else "lm_studio_disconnected"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get analysis stats: {e}")
            return {"error": str(e)}
    
    def validate_system(self) -> List[str]:
        """
        Validate that all system components are working
        
        Returns:
            List of validation issues (empty if all good)
        """
        issues = []
        
        try:
            # Check LM Studio connection
            if not self.lm_client.test_connection():
                issues.append("LM Studio is not accessible - check if server is running")
            
            # Check prompt file
            if not self.prompt_engine.prompt_file.exists():
                issues.append(f"Prompt file {self.prompt_engine.prompt_file} not found")
            
            # Check prompt content
            prompt = self.prompt_engine.get_analysis_prompt()
            if len(prompt) < 100:
                issues.append("Prompt file appears to be empty or too short")
            
        except Exception as e:
            issues.append(f"System validation error: {e}")
        
        return issues