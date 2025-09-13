"""
Thread-Aware Email Analysis
Handles email threads with context-aware LLM decision making
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from email_analyzer import EmailAnalysisResult

@dataclass
class ThreadMessage:
    """Individual message within a thread"""
    message_id: str
    subject: str
    sender: str
    date: datetime
    body: str
    markdown: str
    is_starred: bool = False
    labels: List[str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []

@dataclass
class ThreadAnalysisResult:
    """Result of analyzing an entire thread"""
    thread_id: str
    thread_subject: str
    message_count: int
    participants: List[str]
    date_range: Tuple[datetime, datetime]
    
    # Overall thread recommendation
    thread_recommendation: str  # KEEP_THREAD, DELETE_THREAD, MIXED
    thread_confidence: float
    thread_reasoning: str
    
    # Individual message decisions
    message_decisions: Dict[str, EmailAnalysisResult]
    
    # Special considerations
    has_starred_messages: bool = False
    auto_keep_reasons: List[str] = None
    
    def __post_init__(self):
        if self.auto_keep_reasons is None:
            self.auto_keep_reasons = []

class ThreadAnalyzer:
    """Analyzes email threads with context awareness"""
    
    def __init__(self, lm_client, prompt_engine):
        """
        Initialize thread analyzer
        
        Args:
            lm_client: LM Studio client for analysis
            prompt_engine: Prompt engine for dynamic prompts
        """
        self.lm_client = lm_client
        self.prompt_engine = prompt_engine
        self.logger = logging.getLogger(__name__)
    
    def analyze_thread(self, thread_messages: List[ThreadMessage]) -> ThreadAnalysisResult:
        """
        Analyze an entire email thread with context
        
        Args:
            thread_messages: List of messages in the thread (chronologically ordered)
            
        Returns:
            ThreadAnalysisResult with thread-level and message-level decisions
        """
        if not thread_messages:
            raise ValueError("Cannot analyze empty thread")
        
        # Check for starred messages (auto-keep)
        starred_messages = [msg for msg in thread_messages if msg.is_starred]
        has_starred = len(starred_messages) > 0
        
        # Extract thread metadata
        thread_id = self._extract_thread_id(thread_messages)
        participants = self._get_unique_participants(thread_messages)
        date_range = self._get_date_range(thread_messages)
        
        # If any message is starred, auto-keep the thread
        if has_starred:
            return self._create_auto_keep_result(
                thread_messages, 
                thread_id, 
                participants, 
                date_range,
                f"Thread contains {len(starred_messages)} starred message(s)"
            )
        
        # Analyze thread context + individual messages
        self.logger.info(f"Analyzing thread {thread_id} with {len(thread_messages)} messages")
        
        # Create thread context for LLM
        thread_context = self._build_thread_context(thread_messages)
        
        # Get thread-level analysis
        thread_analysis = self._analyze_thread_context(thread_context)
        
        # Analyze individual messages with thread context
        message_decisions = {}
        for message in thread_messages:
            message_analysis = self._analyze_message_in_context(message, thread_context, thread_analysis)
            message_decisions[message.message_id] = message_analysis
        
        # Determine overall thread recommendation
        thread_recommendation = self._determine_thread_recommendation(thread_analysis, message_decisions)
        
        return ThreadAnalysisResult(
            thread_id=thread_id,
            thread_subject=thread_messages[0].subject,
            message_count=len(thread_messages),
            participants=participants,
            date_range=date_range,
            thread_recommendation=thread_recommendation['recommendation'],
            thread_confidence=thread_recommendation['confidence'],
            thread_reasoning=thread_recommendation['reasoning'],
            message_decisions=message_decisions,
            has_starred_messages=has_starred
        )
    
    def _extract_thread_id(self, messages: List[ThreadMessage]) -> str:
        """Extract or generate thread ID"""
        # In Gmail API, we would get this from the thread object
        # For now, use the first message ID as thread identifier
        return f"thread_{messages[0].message_id}"
    
    def _get_unique_participants(self, messages: List[ThreadMessage]) -> List[str]:
        """Get unique email participants in the thread"""
        participants = set()
        for message in messages:
            participants.add(message.sender)
        return sorted(list(participants))
    
    def _get_date_range(self, messages: List[ThreadMessage]) -> Tuple[datetime, datetime]:
        """Get date range of the thread"""
        dates = [msg.date for msg in messages]
        return (min(dates), max(dates))
    
    def _create_auto_keep_result(self, messages: List[ThreadMessage], thread_id: str, 
                                participants: List[str], date_range: Tuple[datetime, datetime],
                                reason: str) -> ThreadAnalysisResult:
        """Create auto-keep result for starred threads"""
        # Create KEEP decisions for all messages
        message_decisions = {}
        for message in messages:
            message_decisions[message.message_id] = EmailAnalysisResult(
                email_id=message.message_id,
                recommendation="KEEP",
                category="Starred Message",
                confidence=1.0,
                reasoning="Message or thread contains starred items",
                key_factors=["Starred message", "Auto-keep rule"],
                analysis_timestamp=datetime.now().isoformat(),
                model_used="auto-keep-rule"
            )
        
        return ThreadAnalysisResult(
            thread_id=thread_id,
            thread_subject=messages[0].subject,
            message_count=len(messages),
            participants=participants,
            date_range=date_range,
            thread_recommendation="KEEP_THREAD",
            thread_confidence=1.0,
            thread_reasoning=reason,
            message_decisions=message_decisions,
            has_starred_messages=True,
            auto_keep_reasons=[reason]
        )
    
    def _build_thread_context(self, messages: List[ThreadMessage]) -> str:
        """Build thread context for LLM analysis"""
        context_parts = []
        
        # Thread overview
        context_parts.append(f"# Email Thread Analysis")
        context_parts.append(f"**Thread Subject:** {messages[0].subject}")
        context_parts.append(f"**Message Count:** {len(messages)}")
        context_parts.append(f"**Participants:** {', '.join(self._get_unique_participants(messages))}")
        
        date_range = self._get_date_range(messages)
        context_parts.append(f"**Date Range:** {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}")
        context_parts.append(f"")
        
        # Individual messages
        context_parts.append("## Messages in Thread (chronological order)")
        context_parts.append("")
        
        for i, message in enumerate(messages, 1):
            context_parts.append(f"### Message {i} of {len(messages)}")
            context_parts.append(f"**From:** {message.sender}")
            context_parts.append(f"**Date:** {message.date.strftime('%Y-%m-%d %H:%M')}")
            context_parts.append(f"**Starred:** {'Yes' if message.is_starred else 'No'}")
            if message.labels:
                context_parts.append(f"**Labels:** {', '.join(message.labels)}")
            context_parts.append("")
            context_parts.append(message.markdown)
            context_parts.append("")
            context_parts.append("---")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _analyze_thread_context(self, thread_context: str) -> Dict[str, Any]:
        """Get thread-level analysis from LLM"""
        try:
            # Create thread-specific prompt
            base_prompt = self.prompt_engine.get_analysis_prompt()
            
            thread_prompt = f"""{base_prompt}

## THREAD ANALYSIS MODE

You are analyzing an EMAIL THREAD, not just a single email. Consider:

1. **Thread Context**: The relationship between messages, conversation flow
2. **Participants**: Who is involved and their roles
3. **Evolution**: How the conversation develops over time
4. **Overall Value**: The thread's collective importance vs individual messages

## Thread-Level Decisions:
- **KEEP_THREAD**: Entire thread has value, keep all messages
- **DELETE_THREAD**: Entire thread is junk, delete all messages  
- **MIXED**: Some messages valuable, others not - analyze individually

## Response Format:
```json
{{
  "thread_recommendation": "KEEP_THREAD" | "DELETE_THREAD" | "MIXED",
  "thread_confidence": 0.1-1.0,
  "thread_reasoning": "Why this thread should be kept/deleted/mixed",
  "key_thread_factors": ["Factor 1", "Factor 2"],
  "conversation_type": "Type of conversation (e.g., work discussion, marketing, support)"
}}
```

Analyze the ENTIRE thread context, not individual messages.
"""

            result = self.lm_client.analyze_email(thread_context, thread_prompt)
            return result if result else {}
            
        except Exception as e:
            self.logger.error(f"Thread context analysis failed: {e}")
            return {
                "thread_recommendation": "MIXED",
                "thread_confidence": 0.5,
                "thread_reasoning": "Analysis failed, defaulting to individual message review",
                "key_thread_factors": ["Analysis error"],
                "conversation_type": "Unknown"
            }
    
    def _analyze_message_in_context(self, message: ThreadMessage, thread_context: str, 
                                  thread_analysis: Dict[str, Any]) -> EmailAnalysisResult:
        """Analyze individual message with full thread context"""
        try:
            # If thread analysis is decisive, apply to all messages
            thread_rec = thread_analysis.get('thread_recommendation', 'MIXED')
            if thread_rec in ['KEEP_THREAD', 'DELETE_THREAD']:
                recommendation = "KEEP" if thread_rec == "KEEP_THREAD" else "JUNK-CANDIDATE"
                return EmailAnalysisResult(
                    email_id=message.message_id,
                    recommendation=recommendation,
                    category=thread_analysis.get('conversation_type', 'Thread Decision'),
                    confidence=thread_analysis.get('thread_confidence', 0.8),
                    reasoning=f"Thread-level decision: {thread_analysis.get('thread_reasoning', 'Part of thread analysis')}",
                    key_factors=thread_analysis.get('key_thread_factors', ['Thread context']),
                    analysis_timestamp=datetime.now().isoformat(),
                    model_used=self.lm_client.model_name
                )
            
            # Mixed thread - analyze this message individually with context
            message_prompt = f"""{self.prompt_engine.get_analysis_prompt()}

## MESSAGE IN THREAD CONTEXT

**Thread Analysis:** {thread_analysis.get('thread_reasoning', 'Mixed thread')}
**Thread Type:** {thread_analysis.get('conversation_type', 'Unknown')}

You are analyzing ONE MESSAGE within a larger thread. Consider:
- The message's individual value
- Its role in the overall conversation
- Whether it adds unique information
- Whether removing it would break thread coherence

**Message to analyze:**
{message.markdown}

Respond with standard JSON format for this individual message.
"""

            result = self.lm_client.analyze_email(message.markdown, message_prompt)
            
            if result:
                return EmailAnalysisResult(
                    email_id=message.message_id,
                    recommendation=result.get('recommendation', 'KEEP'),
                    category=result.get('category', 'Thread Message'),
                    confidence=result.get('confidence', 0.5),
                    reasoning=result.get('reasoning', 'Individual message analysis'),
                    key_factors=result.get('key_factors', ['Thread context']),
                    analysis_timestamp=datetime.now().isoformat(),
                    model_used=self.lm_client.model_name
                )
            else:
                # Fallback
                return EmailAnalysisResult(
                    email_id=message.message_id,
                    recommendation="KEEP",
                    category="Analysis Failed",
                    confidence=0.5,
                    reasoning="Could not analyze message, defaulting to keep",
                    key_factors=["Analysis error"],
                    analysis_timestamp=datetime.now().isoformat(),
                    model_used="fallback"
                )
                
        except Exception as e:
            self.logger.error(f"Message analysis failed for {message.message_id}: {e}")
            # Default to KEEP on error
            return EmailAnalysisResult(
                email_id=message.message_id,
                recommendation="KEEP",
                category="Error Fallback",
                confidence=0.5,
                reasoning=f"Analysis error: {str(e)}",
                key_factors=["Error recovery"],
                analysis_timestamp=datetime.now().isoformat(),
                model_used="error-fallback"
            )
    
    def _determine_thread_recommendation(self, thread_analysis: Dict[str, Any], 
                                       message_decisions: Dict[str, EmailAnalysisResult]) -> Dict[str, Any]:
        """Determine overall thread recommendation based on analysis"""
        thread_rec = thread_analysis.get('thread_recommendation', 'MIXED')
        
        if thread_rec in ['KEEP_THREAD', 'DELETE_THREAD']:
            return {
                'recommendation': thread_rec,
                'confidence': thread_analysis.get('thread_confidence', 0.8),
                'reasoning': thread_analysis.get('thread_reasoning', 'Thread-level decision')
            }
        
        # Mixed thread - aggregate individual decisions
        keep_count = sum(1 for decision in message_decisions.values() 
                        if decision.recommendation == 'KEEP')
        delete_count = len(message_decisions) - keep_count
        
        if delete_count == 0:
            return {
                'recommendation': 'KEEP_THREAD',
                'confidence': 0.9,
                'reasoning': 'All individual messages should be kept'
            }
        elif keep_count == 0:
            return {
                'recommendation': 'DELETE_THREAD', 
                'confidence': 0.9,
                'reasoning': 'All individual messages should be deleted'
            }
        else:
            return {
                'recommendation': 'MIXED',
                'confidence': 0.7,
                'reasoning': f'Mixed decisions: {keep_count} keep, {delete_count} delete'
            }