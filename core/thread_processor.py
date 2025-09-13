"""
Thread-Aware Email Processor
Processes emails by threads with context-aware decisions
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from .thread_analyzer import ThreadAnalyzer, ThreadMessage, ThreadAnalysisResult
from .email_analyzer import EmailAnalysisResult

class ThreadProcessor:
    """Processes emails in thread context"""
    
    def __init__(self, lm_client, prompt_engine):
        """
        Initialize thread processor
        
        Args:
            lm_client: LM Studio client
            prompt_engine: Prompt engine
        """
        self.thread_analyzer = ThreadAnalyzer(lm_client, prompt_engine)
        self.logger = logging.getLogger(__name__)
    
    def group_emails_by_thread(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group emails by thread ID
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Dictionary mapping thread_id -> list of emails
        """
        threads = defaultdict(list)
        
        for email in emails:
            # Try to get thread ID from various sources
            thread_id = self._extract_thread_id(email)
            threads[thread_id].append(email)
        
        self.logger.info(f"Grouped {len(emails)} emails into {len(threads)} threads")
        return dict(threads)
    
    def _extract_thread_id(self, email: Dict[str, Any]) -> str:
        """Extract thread ID from email data"""
        # Check various possible sources for thread ID
        thread_id = email.get('thread_id')
        if thread_id:
            return thread_id
        
        # Check raw Gmail data
        raw_data = email.get('raw_data', {})
        if 'threadId' in raw_data:
            return raw_data['threadId']
        
        # For emails without thread info, treat as single-message thread
        return f"single_{email.get('id', 'unknown')}"
    
    def convert_to_thread_messages(self, emails: List[Dict[str, Any]]) -> List[ThreadMessage]:
        """
        Convert email dictionaries to ThreadMessage objects
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            List of ThreadMessage objects, sorted chronologically
        """
        messages = []
        
        for email in emails:
            # Parse date
            try:
                if isinstance(email.get('date'), str):
                    date = datetime.fromisoformat(email['date'].replace('Z', '+00:00'))
                else:
                    date = datetime.now()  # Fallback
            except:
                date = datetime.now()
            
            # Check if message is starred
            is_starred = self._is_message_starred(email)
            
            # Extract labels
            labels = email.get('labels', [])
            
            message = ThreadMessage(
                message_id=email.get('id', 'unknown'),
                subject=email.get('subject', 'No Subject'),
                sender=email.get('from', 'Unknown Sender'),
                date=date,
                body=email.get('body', ''),
                markdown=email.get('markdown', ''),
                is_starred=is_starred,
                labels=labels
            )
            
            messages.append(message)
        
        # Sort chronologically
        messages.sort(key=lambda m: m.date)
        return messages
    
    def _is_message_starred(self, email: Dict[str, Any]) -> bool:
        """Check if a message is starred"""
        # Check explicit starred flag
        if email.get('is_starred', False):
            return True
        
        # Check labels for STARRED
        labels = email.get('labels', [])
        if 'STARRED' in labels:
            return True
        
        # Check raw Gmail data
        raw_data = email.get('raw_data', {})
        if 'labelIds' in raw_data:
            return 'STARRED' in raw_data['labelIds']
        
        return False
    
    def process_thread(self, thread_emails: List[Dict[str, Any]]) -> ThreadAnalysisResult:
        """
        Process a single thread of emails
        
        Args:
            thread_emails: List of emails in the thread
            
        Returns:
            ThreadAnalysisResult with decisions for thread and individual messages
        """
        if not thread_emails:
            raise ValueError("Cannot process empty thread")
        
        # Convert to thread messages
        thread_messages = self.convert_to_thread_messages(thread_emails)
        
        # Analyze the thread
        thread_result = self.thread_analyzer.analyze_thread(thread_messages)
        
        self.logger.info(f"Thread {thread_result.thread_id}: {thread_result.thread_recommendation} "
                        f"({thread_result.message_count} messages, confidence: {thread_result.thread_confidence:.2f})")
        
        return thread_result
    
    def process_threads(self, emails: List[Dict[str, Any]]) -> List[ThreadAnalysisResult]:
        """
        Process multiple threads
        
        Args:
            emails: List of all emails to process
            
        Returns:
            List of ThreadAnalysisResult objects
        """
        # Group emails by thread
        thread_groups = self.group_emails_by_thread(emails)
        
        results = []
        for thread_id, thread_emails in thread_groups.items():
            try:
                thread_result = self.process_thread(thread_emails)
                results.append(thread_result)
            except Exception as e:
                self.logger.error(f"Failed to process thread {thread_id}: {e}")
                # Create fallback result
                fallback_result = self._create_fallback_result(thread_id, thread_emails)
                results.append(fallback_result)
        
        return results
    
    def _create_fallback_result(self, thread_id: str, emails: List[Dict[str, Any]]) -> ThreadAnalysisResult:
        """Create fallback result when thread processing fails"""
        # Check for starred messages
        has_starred = any(self._is_message_starred(email) for email in emails)
        
        # Create simple decisions
        message_decisions = {}
        for email in emails:
            recommendation = "KEEP" if has_starred else "KEEP"  # Default to KEEP on error
            message_decisions[email.get('id', 'unknown')] = EmailAnalysisResult(
                email_id=email.get('id', 'unknown'),
                recommendation=recommendation,
                category="Fallback Decision",
                confidence=0.5,
                reasoning="Thread processing failed, using fallback",
                key_factors=["Processing error"],
                analysis_timestamp=datetime.now().isoformat(),
                model_used="fallback"
            )
        
        return ThreadAnalysisResult(
            thread_id=thread_id,
            thread_subject=emails[0].get('subject', 'Unknown'),
            message_count=len(emails),
            participants=[email.get('from', 'Unknown') for email in emails],
            date_range=(datetime.now(), datetime.now()),
            thread_recommendation="KEEP_THREAD" if has_starred else "MIXED",
            thread_confidence=0.5,
            thread_reasoning="Fallback decision due to processing error",
            message_decisions=message_decisions,
            has_starred_messages=has_starred,
            auto_keep_reasons=["Contains starred messages"] if has_starred else []
        )
    
    def get_actionable_decisions(self, thread_result: ThreadAnalysisResult) -> List[Tuple[str, str, str]]:
        """
        Get list of actionable decisions from thread analysis
        
        Args:
            thread_result: Thread analysis result
            
        Returns:
            List of tuples: (message_id, action, reason)
            Actions: 'keep', 'delete', 'no_action'
        """
        actions = []
        
        for message_id, decision in thread_result.message_decisions.items():
            if decision.recommendation == "KEEP":
                action = "keep"
                reason = decision.reasoning
            elif decision.recommendation == "JUNK-CANDIDATE":
                action = "delete"
                reason = decision.reasoning
            else:
                action = "no_action"
                reason = "No clear recommendation"
            
            actions.append((message_id, action, reason))
        
        return actions