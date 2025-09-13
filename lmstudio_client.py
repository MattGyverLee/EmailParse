"""
LM Studio API Client for Email Analysis
Handles communication with local LM Studio server running Mistral model
"""

import json
import requests
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class LMStudioClient:
    """Client for communicating with LM Studio API"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LM Studio client with configuration"""
        self.base_url = config.get('lmstudio', {}).get('base_url', 'http://localhost:1234')
        self.api_key = config.get('lmstudio', {}).get('api_key', '')
        self.timeout = config.get('lmstudio', {}).get('timeout', 30)
        
        # Model parameters
        model_config = config.get('lmstudio', {}).get('model', {})
        self.model_name = model_config.get('name', 'mistral')
        self.temperature = model_config.get('temperature', 0.3)
        self.max_tokens = model_config.get('max_tokens', 500)
        
        self.logger = logging.getLogger(__name__)
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def test_connection(self) -> bool:
        """Test if LM Studio server is running and accessible"""
        try:
            response = requests.get(
                f'{self.base_url}/v1/models',
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to LM Studio: {e}")
            return False
    
    def get_available_models(self) -> list:
        """Get list of available models from LM Studio"""
        try:
            response = requests.get(
                f'{self.base_url}/v1/models',
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get models: {e}")
            return []
    
    def analyze_email(self, email_markdown: str, prompt_template: str) -> Optional[Dict[str, Any]]:
        """
        Analyze an email using the LM Studio model
        
        Args:
            email_markdown: Email content in markdown format
            prompt_template: The prompt template to use
            
        Returns:
            Dict containing analysis results or None if failed
        """
        try:
            # Construct the full prompt
            full_prompt = f"{prompt_template}\n\n## Email to Analyze:\n\n{email_markdown}"
            
            # Prepare the API request
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert email categorization assistant. Always respond with valid JSON in the specified format."
                    },
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            self.logger.debug(f"Sending request to LM Studio: {payload}")
            
            # Make the API request
            response = requests.post(
                f'{self.base_url}/v1/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the response content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # Try to parse JSON response
                try:
                    # Clean up the response (remove markdown code blocks if present)
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        content = content.split('```')[1].split('```')[0].strip()
                    
                    analysis_result = json.loads(content)
                    
                    # Validate required fields
                    required_fields = ['recommendation', 'category', 'confidence', 'reasoning']
                    if all(field in analysis_result for field in required_fields):
                        return analysis_result
                    else:
                        self.logger.error(f"Missing required fields in response: {analysis_result}")
                        return None
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {content}")
                    self.logger.error(f"JSON error: {e}")
                    return None
            else:
                self.logger.error(f"Unexpected API response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in analyze_email: {e}")
            return None
    
    def suggest_prompt_update(self, current_prompt: str, user_feedback: str, email_content: str) -> Optional[str]:
        """
        Ask the LLM to suggest updates to the prompt based on user feedback
        
        Args:
            current_prompt: Current prompt template
            user_feedback: User's explanation for their decision
            email_content: The email that was misclassified
            
        Returns:
            Suggested prompt improvement or None if failed
        """
        try:
            improvement_prompt = f"""
You are a prompt engineering expert. A user has provided feedback on an email classification.

## Current Prompt Template:
{current_prompt}

## Email Content:
{email_content}

## User Feedback:
{user_feedback}

## Task:
The user disagreed with the AI classification and provided their reasoning. Based on this feedback, suggest GENERAL improvements to the prompt template that would help the AI make better classifications for similar emails in the future.

IMPORTANT: 
- Suggest general improvements, not overfitting to this specific email
- Focus on improving categorization criteria or adding new considerations
- Keep the same JSON response format
- Don't suggest changes based on sender names or specific content - focus on patterns and categories

Respond with ONLY the improved section(s) of the prompt that should be updated, not the entire prompt. Be specific about what to add or modify.
"""

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a prompt engineering expert focused on improving email classification systems."
                    },
                    {
                        "role": "user",
                        "content": improvement_prompt
                    }
                ],
                "temperature": 0.7,  # Slightly higher for creativity
                "max_tokens": 800,
                "stream": False
            }
            
            response = requests.post(
                f'{self.base_url}/v1/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                suggestion = result['choices'][0]['message']['content'].strip()
                return suggestion
            else:
                self.logger.error(f"Unexpected API response format: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get prompt suggestion: {e}")
            return None