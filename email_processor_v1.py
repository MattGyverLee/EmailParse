"""
EmailParse V1.0 - Main Processing Engine
Orchestrates the complete email processing workflow with human-in-the-loop feedback
"""

import os
import sys
import json
import yaml
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.interactive_cli import InteractiveCLI
from core.email_analyzer import EmailAnalyzer, EmailAnalysisResult
from clients.gmail_client_wrapper import GmailClientWrapper
from core.thread_processor import ThreadProcessor
from utils.config import Config

class EmailProcessor:
    """Main email processing engine"""
    
    def __init__(self, config_path: str = "config/config_v1.yaml"):
        """
        Initialize email processor
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = Config(config_path)
        self.setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.processed_log_file = "processed_log.jsonl"
        
        # Initialize components
        try:
            self.gmail_client = GmailClientWrapper(self.config)
            self.analyzer = EmailAnalyzer(self.config)
            self.cli = InteractiveCLI(self.config)
            
            # Initialize thread processor
            self.thread_processor = ThreadProcessor(
                self.analyzer.lm_client, 
                self.analyzer.prompt_engine
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
        
        # Load processed emails log
        self.processed_emails = self.load_processed_log()
        
        # Track recent actions for undo capability
        self.recent_actions = []
        self.max_undo_actions = 10
    
    def setup_logging(self):
        """Setup logging configuration"""
        app_config = self.config.get_app_config()
        log_level = app_config.get('log_level', 'INFO')
        log_file = app_config.get('log_file', 'logs/emailparse.log')
        
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def load_processed_log(self) -> set:
        """Load set of already processed email IDs"""
        processed = set()
        
        try:
            if Path(self.processed_log_file).exists():
                with open(self.processed_log_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                email_id = entry.get('email_id')
                                if email_id:
                                    processed.add(email_id)
                            except json.JSONDecodeError as je:
                                self.logger.warning(f"Skipping malformed JSON on line {line_num}: {je}")
                                continue
                
                self.logger.info(f"Loaded {len(processed)} processed email IDs")
            
        except Exception as e:
            self.logger.error(f"Error loading processed log: {e}")
            # If log is completely corrupted, start fresh
            if "Extra data" in str(e) or "JSONDecodeError" in str(e):
                self.logger.warning("Processed log appears corrupted, starting with empty set")
                try:
                    # Backup the corrupted log
                    corrupted_backup = f"{self.processed_log_file}.corrupted"
                    Path(self.processed_log_file).rename(corrupted_backup)
                    self.logger.info(f"Backed up corrupted log to {corrupted_backup}")
                except Exception:
                    pass
        
        return processed
    
    def log_processed_email(self, email_id: str, decision: str, analysis: Optional[EmailAnalysisResult] = None,
                          user_feedback: Optional[str] = None):
        """Log processed email to JSONL file"""
        try:
            entry = {
                'email_id': email_id,
                'decision': decision,
                'timestamp': datetime.now().isoformat(),
                'user_feedback': user_feedback
            }
            
            if analysis:
                entry['ai_analysis'] = {
                    'recommendation': analysis.recommendation,
                    'category': analysis.category,
                    'confidence': analysis.confidence,
                    'reasoning': analysis.reasoning
                }
            
            with open(self.processed_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\\n')
            
            # Add to in-memory set
            self.processed_emails.add(email_id)
            
        except Exception as e:
            self.logger.error(f"Failed to log processed email {email_id}: {e}")
    
    def fetch_unprocessed_emails(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch emails that haven't been processed yet
        
        Args:
            limit: Maximum number of emails to fetch
            
        Returns:
            List of unprocessed email data
        """
        try:
            processing_config = self.config.get_processing_config()
            batch_size = limit or processing_config.get('batch_size', 10)
            
            self.logger.info(f"Fetching up to {batch_size} emails from Gmail")
            
            # Fetch emails from Gmail - only add buffer if batch_size is large enough
            if batch_size >= 10:
                fetch_limit = batch_size + min(5, batch_size // 2)  # Add buffer for larger batches
            else:
                fetch_limit = batch_size  # For small batches, fetch exact amount
            self.logger.info(f"Fetching {fetch_limit} emails from Gmail API")
            all_emails = self.gmail_client.fetch_emails(limit=fetch_limit)
            
            # Filter out already processed emails
            unprocessed = []
            for email in all_emails:
                email_id = email.get('id')
                if email_id and email_id not in self.processed_emails:
                    unprocessed.append(email)
                
                if len(unprocessed) >= batch_size:
                    break
            
            self.logger.info(f"Found {len(unprocessed)} unprocessed emails")
            return unprocessed
            
        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def process_single_email(self, email_data: Dict[str, Any]) -> bool:
        """
        Process a single email with human-in-the-loop interaction
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            True to continue processing, False to stop
        """
        try:
            email_id = email_data.get('id', 'unknown')
            
            # Analyze email with AI
            self.logger.info(f"Processing email {email_id}")
            analysis = self.analyzer.analyze_email(email_data)
            
            # Display email and get user decision with confidence-based logic
            self.cli.display_email(email_data, analysis)
            decision, feedback, should_update_prompt = self.cli.get_user_decision(analysis)
            
            # Handle user decision
            if decision == "quit":
                return False
            elif decision == "skip":
                self.logger.info(f"Skipping email {email_id}")
                return True
            elif decision == "undo":
                # Handle undo action
                if self.undo_last_action():
                    self.cli.console.print("[green]Last action undone successfully[/green]")
                    # Update session stats to reflect undo
                    if self.cli.session_stats['processed'] > 0:
                        self.cli.session_stats['processed'] -= 1
                else:
                    self.cli.console.print("[red]Could not undo last action[/red]")
                return True  # Continue processing
            
            # Process feedback and update prompt only when needed
            prompt_actually_updated = False
            if should_update_prompt and analysis:
                if feedback:
                    prompt_actually_updated = self.cli.process_user_feedback(email_data, analysis, feedback)
                else:
                    # Generate default feedback for cases where user didn't provide explanation
                    ai_rec = analysis.recommendation
                    user_action = "delete" if decision == "delete" else "keep"
                    default_feedback = f"User chose to {user_action} despite AI recommending {ai_rec}. Confidence was {analysis.confidence:.2f}"
                    prompt_actually_updated = self.cli.process_user_feedback(email_data, analysis, default_feedback)
            
            # Execute the decision (apply labels, move emails, etc.)
            self.execute_decision(email_data, decision, analysis)
            
            # Log the processed email
            self.log_processed_email(email_id, decision, analysis, feedback)
            
            # Update session stats
            self.cli.update_session_stats(decision, analysis, prompt_actually_updated)
            
            # Show progress periodically
            if self.cli.session_stats['processed'] % 5 == 0:
                self.cli.display_session_stats()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing email {email_data.get('id', 'unknown')}: {e}")
            return True  # Continue processing other emails
    
    def execute_decision(self, email_data: Dict[str, Any], decision: str, 
                        analysis: Optional[EmailAnalysisResult] = None):
        """
        Execute user decision by applying labels or moving emails
        
        Args:
            email_data: Email data
            decision: User decision ('keep' or 'delete')
            analysis: AI analysis result
        """
        try:
            email_id = email_data.get('id')
            action_record = {
                'email_id': email_id,
                'decision': decision,
                'timestamp': datetime.now().isoformat(),
                'email_data': email_data,
                'analysis': analysis,
                'executed': False,
                'reversible': True
            }
            
            if decision == "delete":
                # Apply "Junk-Candidate" label and remove from Inbox
                processing_config = self.config.get_processing_config()
                junk_label = processing_config.get('junk_folder', 'Junk-Candidate')
                
                # Add junk label
                add_success = self.gmail_client.add_label(email_id, junk_label)
                
                # Remove from Inbox
                remove_success = self.gmail_client.remove_label(email_id, 'INBOX')
                
                if add_success and remove_success:
                    self.logger.info(f"Applied '{junk_label}' label and removed from Inbox for email {email_id}")
                    action_record['executed'] = True
                    action_record['action_details'] = {'label_added': junk_label, 'label_removed': 'INBOX'}
                elif add_success:
                    self.logger.info(f"Applied '{junk_label}' label to email {email_id} (Inbox removal may have failed)")
                    action_record['executed'] = True
                    action_record['action_details'] = {'label_added': junk_label, 'inbox_removal': 'failed'}
                else:
                    self.logger.error(f"Failed to apply '{junk_label}' label to email {email_id}")
                    action_record['executed'] = False
                    action_record['reversible'] = False
            
            elif decision == "keep":
                # For now, just leave the email as-is
                # In future versions, could add "Reviewed" label or move to processed folder
                self.logger.info(f"Keeping email {email_id} (no action required)")
                action_record['executed'] = True
                action_record['action_details'] = {'action': 'keep', 'no_changes': True}
            
            # Add to recent actions for undo capability
            self.recent_actions.append(action_record)
            if len(self.recent_actions) > self.max_undo_actions:
                self.recent_actions.pop(0)
            
        except Exception as e:
            self.logger.error(f"Failed to execute decision for email {email_id}: {e}")
            raise  # Re-raise to trigger error recovery
    
    def undo_last_action(self) -> bool:
        """
        Undo the last action performed
        
        Returns:
            True if undo was successful
        """
        if not self.recent_actions:
            self.logger.warning("No recent actions to undo")
            return False
        
        try:
            last_action = self.recent_actions[-1]
            
            if not last_action.get('executed') or not last_action.get('reversible'):
                self.logger.warning("Last action cannot be undone")
                return False
            
            email_id = last_action['email_id']
            decision = last_action['decision']
            
            if decision == "delete":
                # Remove the junk label
                action_details = last_action.get('action_details', {})
                junk_label = action_details.get('label_added')
                
                if junk_label:
                    success = self.gmail_client.remove_label(email_id, junk_label)
                    if success:
                        self.logger.info(f"Undid delete action: removed '{junk_label}' label from email {email_id}")
                        # Remove from processed log
                        self.remove_from_processed_log(email_id)
                        # Remove from recent actions
                        self.recent_actions.pop()
                        return True
                    else:
                        self.logger.error(f"Failed to undo delete action for email {email_id}")
                        return False
            
            elif decision == "keep":
                # For keep actions, just remove from processed log
                self.remove_from_processed_log(email_id)
                self.recent_actions.pop()
                self.logger.info(f"Undid keep action for email {email_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to undo last action: {e}")
            return False
    
    def remove_from_processed_log(self, email_id: str):
        """Remove email ID from processed set and log file"""
        try:
            # Remove from in-memory set
            self.processed_emails.discard(email_id)
            
            # Rewrite log file without this email
            if Path(self.processed_log_file).exists():
                temp_log = []
                
                with open(self.processed_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line.strip())
                            if entry.get('email_id') != email_id:
                                temp_log.append(line)
                
                with open(self.processed_log_file, 'w', encoding='utf-8') as f:
                    f.writelines(temp_log)
                
                self.logger.info(f"Removed email {email_id} from processed log")
        
        except Exception as e:
            self.logger.error(f"Failed to remove email {email_id} from processed log: {e}")
    
    def get_recent_actions(self) -> List[Dict[str, Any]]:
        """Get list of recent actions for display"""
        return self.recent_actions.copy()
    
    def run_interactive_session(self, max_emails: int = None, thread_mode: bool = True):
        """
        Run interactive processing session
        
        Args:
            max_emails: Maximum number of emails to process (None for unlimited)
            thread_mode: Whether to process emails in thread context
        """
        try:
            # Display welcome and check system
            if not self.cli.display_welcome():
                return
            
            # Fetch unprocessed emails
            emails = self.fetch_unprocessed_emails(max_emails)
            
            if not emails:
                self.cli.console.print("\\n[yellow]No unprocessed emails found![/yellow]")
                return
            
            if thread_mode:
                self.cli.console.print(f"\\n[bold]Starting thread-aware processing with {len(emails)} emails[/bold]")
                self.run_thread_processing_session(emails)
            else:
                self.cli.console.print(f"\\n[bold]Starting individual processing with {len(emails)} emails[/bold]")
                self.run_individual_processing_session(emails)
            
            # Show final stats and goodbye
            self.cli.display_goodbye()
            
        except KeyboardInterrupt:
            self.cli.console.print("\\n\\n[yellow]Processing interrupted by user[/yellow]")
            self.cli.display_session_stats()
        except Exception as e:
            self.logger.error(f"Error in interactive session: {e}")
            self.cli.console.print(f"\\n[red]Error: {e}[/red]")
    
    def run_thread_processing_session(self, emails: List[Dict[str, Any]]):
        """Run thread-aware processing session"""
        # Process emails by threads
        thread_results = self.thread_processor.process_threads(emails)
        
        for thread_result in thread_results:
            if not self.process_thread_interactively(thread_result):
                break  # User chose to quit
    
    def run_individual_processing_session(self, emails: List[Dict[str, Any]]):
        """Run individual email processing session (legacy mode)"""
        for i, email_data in enumerate(emails, 1):
            self.cli.console.print(f"\\n[bold cyan]Email {i}/{len(emails)}[/bold cyan]")
            
            if not self.process_single_email(email_data):
                break  # User chose to quit
    
    def process_thread_interactively(self, thread_result) -> bool:
        """
        Process a thread interactively with user decisions
        
        Args:
            thread_result: ThreadAnalysisResult object
            
        Returns:
            True to continue processing, False to quit
        """
        try:
            self.cli.console.print(f"\\n[bold magenta]Thread: {thread_result.thread_subject}[/bold magenta]")
            self.cli.console.print(f"[dim]Messages: {thread_result.message_count}, Participants: {len(thread_result.participants)}[/dim]")
            
            # Check for auto-keep conditions
            if thread_result.has_starred_messages:
                self.cli.console.print(f"\\n[bold green]Thread contains starred messages - AUTO KEEP[/bold green]")
                self.cli.console.print(f"[dim]Reason: {', '.join(thread_result.auto_keep_reasons)}[/dim]")
                
                # Auto-execute keep decisions for all messages
                for message_id, decision in thread_result.message_decisions.items():
                    self.execute_thread_decision(message_id, "keep", decision)
                    self.log_processed_email(message_id, "keep", decision, "Auto-keep: starred thread")
                
                # Update stats
                self.cli.session_stats['processed'] += thread_result.message_count
                self.cli.session_stats['kept'] += thread_result.message_count
                
                return True
            
            # Display thread analysis
            self.display_thread_analysis(thread_result)
            
            # Get user decision for the thread
            thread_decision = self.get_thread_decision(thread_result)
            
            if thread_decision == "quit":
                return False
            elif thread_decision == "skip":
                self.logger.info(f"Skipping thread {thread_result.thread_id}")
                return True
            
            # Execute decisions based on thread choice
            self.execute_thread_decisions(thread_result, thread_decision)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing thread {thread_result.thread_id}: {e}")
            return True  # Continue with next thread
    
    def display_thread_analysis(self, thread_result):
        """Display thread analysis results to user"""
        from rich.panel import Panel
        from rich.table import Table
        
        # Thread overview
        overview_table = Table(show_header=False, box=None, padding=(0, 1))
        overview_table.add_column("Field", style="bold")
        overview_table.add_column("Value")
        
        overview_table.add_row("Thread Subject:", thread_result.thread_subject)
        overview_table.add_row("Messages:", str(thread_result.message_count))
        overview_table.add_row("Participants:", ", ".join(thread_result.participants))
        
        date_start, date_end = thread_result.date_range
        if date_start == date_end:
            date_str = date_start.strftime("%Y-%m-%d")
        else:
            date_str = f"{date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
        overview_table.add_row("Date Range:", date_str)
        
        # Color-code thread recommendation
        rec_color = "green" if thread_result.thread_recommendation == "KEEP_THREAD" else "red" if thread_result.thread_recommendation == "DELETE_THREAD" else "yellow"
        recommendation = f"[{rec_color}]{thread_result.thread_recommendation}[/{rec_color}]"
        overview_table.add_row("AI Recommendation:", recommendation)
        overview_table.add_row("Confidence:", f"{thread_result.thread_confidence:.1%}")
        overview_table.add_row("Reasoning:", thread_result.thread_reasoning)
        
        thread_panel = Panel(
            overview_table,
            title="Thread Analysis",
            border_style="blue"
        )
        self.cli.console.print(thread_panel)
        
        # Individual message decisions if mixed
        if thread_result.thread_recommendation == "MIXED":
            self.display_message_decisions(thread_result)
    
    def display_message_decisions(self, thread_result):
        """Display individual message decisions for mixed threads"""
        from rich.table import Table
        from rich.panel import Panel
        
        msg_table = Table()
        msg_table.add_column("Message", style="cyan")
        msg_table.add_column("From", style="white")
        msg_table.add_column("Decision", style="bold")
        msg_table.add_column("Confidence", style="dim")
        msg_table.add_column("Reasoning", style="dim")
        
        for message_id, decision in thread_result.message_decisions.items():
            # Get message info (simplified for display)
            msg_num = message_id.split('_')[-1] if '_' in message_id else message_id[-3:]
            sender = next((p for p in thread_result.participants), "Unknown")
            
            decision_color = "green" if decision.recommendation == "KEEP" else "red"
            decision_text = f"[{decision_color}]{decision.recommendation}[/{decision_color}]"
            
            msg_table.add_row(
                f"#{msg_num}",
                sender,
                decision_text,
                f"{decision.confidence:.1%}",
                decision.reasoning[:50] + "..." if len(decision.reasoning) > 50 else decision.reasoning
            )
        
        decisions_panel = Panel(
            msg_table,
            title="Individual Message Decisions",
            border_style="yellow"
        )
        self.cli.console.print(decisions_panel)
    
    def get_thread_decision(self, thread_result) -> str:
        """Get user decision for thread processing"""
        from rich.prompt import Prompt, Confirm
        
        self.cli.console.print("\\n" + "="*80)
        
        # Show thread options
        if thread_result.thread_recommendation in ["KEEP_THREAD", "DELETE_THREAD"]:
            # Clear thread recommendation
            action = "keep" if thread_result.thread_recommendation == "KEEP_THREAD" else "delete"
            try:
                if Confirm.ask(f"Accept AI recommendation to {action} entire thread?", default=True):
                    return f"thread_{action}"
            except (EOFError, KeyboardInterrupt):
                self.cli.console.print("\n[yellow]Session interrupted. Defaulting to keep thread for safety.[/yellow]")
                return "thread_keep"
        
        # Show detailed options
        options_text = f"""
[bold]Thread Processing Options:[/bold]

[green]K[/green] - Keep entire thread (all {thread_result.message_count} messages)
[red]D[/red] - Delete entire thread (mark all as Junk-Candidate)
[yellow]M[/yellow] - Process messages individually (mixed decisions)
[blue]S[/blue] - Skip this thread
[blue]Q[/blue] - Quit processing
[dim]?[/dim] - Show help
"""
        self.cli.console.print(options_text)
        
        while True:
            try:
                choice = Prompt.ask(
                    "Your decision",
                    choices=["k", "d", "m", "s", "q", "?", "help"],
                    default="k",
                    show_choices=False
                ).lower()
            except (EOFError, KeyboardInterrupt):
                self.cli.console.print("\n[yellow]Session interrupted. Defaulting to keep thread for safety.[/yellow]")
                return "thread_keep"
            
            if choice in ["?", "help"]:
                self.show_thread_help()
                continue
            elif choice == "k":
                return "thread_keep"
            elif choice == "d":
                return "thread_delete"
            elif choice == "m":
                return "mixed"
            elif choice == "s":
                return "skip"
            elif choice == "q":
                return "quit"
    
    def show_thread_help(self):
        """Show help for thread processing"""
        help_text = """
[bold]Thread Processing Help[/bold]

[bold green]Thread Commands:[/bold green]
- [green]K[/green] - Keep Thread: Mark all messages in thread as important
- [red]D[/red] - Delete Thread: Mark all messages as junk candidates  
- [yellow]M[/yellow] - Mixed: Process each message individually based on AI recommendations
- [blue]S[/blue] - Skip: Skip this thread for now
- [blue]Q[/blue] - Quit: Exit processing session

[bold yellow]Thread Context:[/bold yellow]
The AI analyzes the entire conversation context, considering:
- Conversation flow and relationships between messages
- All participants and their roles
- Evolution of the discussion over time
- Overall thread value vs individual message importance

[bold blue]Special Rules:[/bold blue]
- Messages with stars are AUTOMATICALLY kept (entire thread)
- Only tagging operations are performed (no deletion)
- Thread decisions apply to ALL messages in the conversation

[bold red]Safety:[/bold red]
- Starred messages force the entire thread to be kept
- When uncertain, choose Keep or Mixed for safer processing
- You can review individual messages in Mixed mode
"""
        
        from rich.panel import Panel
        help_panel = Panel(help_text, title="Thread Processing Help", border_style="blue")
        self.cli.console.print(help_panel)
    
    def execute_thread_decisions(self, thread_result, thread_decision: str):
        """Execute user's thread decision"""
        if thread_decision == "thread_keep":
            # Keep all messages
            for message_id, decision in thread_result.message_decisions.items():
                self.execute_thread_decision(message_id, "keep", decision)
                self.log_processed_email(message_id, "keep", decision, "Thread keep decision")
            
            self.cli.session_stats['processed'] += thread_result.message_count
            self.cli.session_stats['kept'] += thread_result.message_count
            
        elif thread_decision == "thread_delete":
            # Delete all messages
            for message_id, decision in thread_result.message_decisions.items():
                self.execute_thread_decision(message_id, "delete", decision)
                self.log_processed_email(message_id, "delete", decision, "Thread delete decision")
            
            self.cli.session_stats['processed'] += thread_result.message_count
            self.cli.session_stats['deleted'] += thread_result.message_count
            
        elif thread_decision == "mixed":
            # Process each message according to AI recommendation
            for message_id, decision in thread_result.message_decisions.items():
                action = "keep" if decision.recommendation == "KEEP" else "delete"
                self.execute_thread_decision(message_id, action, decision)
                self.log_processed_email(message_id, action, decision, "Mixed thread decision")
                
                if action == "keep":
                    self.cli.session_stats['kept'] += 1
                else:
                    self.cli.session_stats['deleted'] += 1
            
            self.cli.session_stats['processed'] += thread_result.message_count
    
    def execute_thread_decision(self, message_id: str, action: str, analysis):
        """Execute decision for a single message in thread context"""
        try:
            if action == "delete":
                # Apply Junk-Candidate label and remove from Inbox
                processing_config = self.config.get_processing_config()
                junk_label = processing_config.get('junk_folder', 'Junk-Candidate')
                
                # Add junk label
                add_success = self.gmail_client.add_label(message_id, junk_label)
                
                # Remove from Inbox
                remove_success = self.gmail_client.remove_label(message_id, 'INBOX')
                
                if add_success and remove_success:
                    self.logger.info(f"Applied '{junk_label}' label and removed from Inbox for message {message_id} in thread context")
                elif add_success:
                    self.logger.info(f"Applied '{junk_label}' label to message {message_id} in thread context (Inbox removal may have failed)")
                else:
                    self.logger.error(f"Failed to apply '{junk_label}' label to message {message_id}")
            elif action == "keep":
                # Keep message (no action needed, just log)
                self.logger.info(f"Keeping message {message_id} in thread context")
                
        except Exception as e:
            self.logger.error(f"Failed to execute thread decision for message {message_id}: {e}")
    
    def validate_setup(self) -> bool:
        """Validate that everything is set up correctly"""
        issues = []
        
        # Check Gmail connection
        try:
            if hasattr(self.gmail_client, 'test_connection'):
                if not self.gmail_client.test_connection():
                    issues.append("Gmail API connection failed")
        except Exception as e:
            issues.append(f"Gmail client error: {e}")
        
        # Check LM Studio
        analyzer_issues = self.analyzer.validate_system()
        issues.extend(analyzer_issues)
        
        if issues:
            self.cli.console.print("\\n[bold red]Setup Issues:[/bold red]")
            for issue in issues:
                self.cli.console.print(f"  - [red]{issue}[/red]")
            return False
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="EmailParse V1.0 - Interactive Email Processing")
    parser.add_argument("--config", default="config/config_v1.yaml", help="Config file path")
    parser.add_argument("--max-emails", type=int, help="Maximum number of emails to process")
    parser.add_argument("--validate", action="store_true", help="Only validate setup, don't process emails")
    parser.add_argument("--thread-mode", action="store_true", help="Enable thread-aware processing (default)")
    parser.add_argument("--individual-mode", action="store_true", help="Process emails individually (legacy mode)")
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = EmailProcessor(args.config)
        
        if args.validate:
            # Just validate setup
            if processor.validate_setup():
                processor.cli.console.print("\\n[bold green]All systems ready![/bold green]")
            else:
                sys.exit(1)
        else:
            # Determine processing mode
            if args.individual_mode:
                thread_mode = False
            else:
                thread_mode = True  # Default to thread mode
            
            # Run interactive session
            processor.run_interactive_session(args.max_emails, thread_mode=thread_mode)
    
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()