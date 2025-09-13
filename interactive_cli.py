"""
Interactive CLI for Human-in-the-Loop Email Processing
Provides user interface for reviewing and correcting AI email classifications
"""

import os
import json
import logging
import difflib
from typing import Dict, Any, Optional, List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress
from rich.syntax import Syntax
from datetime import datetime

from email_analyzer import EmailAnalyzer, EmailAnalysisResult

class InteractiveCLI:
    """Interactive command-line interface for email processing"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize interactive CLI
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
        # Initialize email analyzer
        self.analyzer = EmailAnalyzer(config)
        
        # CLI settings
        self.email_preview_length = config.get('app', {}).get('email_preview_length', 500)
        self.show_progress = config.get('app', {}).get('show_progress', True)
        
        # Session tracking
        self.session_stats = {
            'processed': 0,
            'kept': 0,
            'deleted': 0,
            'ai_agreements': 0,
            'ai_disagreements': 0,
            'prompt_updates': 0,
            'start_time': datetime.now()
        }
    
    def display_welcome(self):
        """Display welcome message and system status"""
        self.console.print("\n")
        welcome_panel = Panel.fit(
            "[bold blue]EmailParse V1.0 - Interactive Email Processing[/bold blue]\n"
            "[dim]Human-in-the-loop email classification with AI assistance[/dim]",
            border_style="blue"
        )
        self.console.print(welcome_panel)
        
        # Check system status
        issues = self.analyzer.validate_system()
        if issues:
            self.console.print("\n[bold red]⚠️ System Issues Detected:[/bold red]")
            for issue in issues:
                self.console.print(f"  • [red]{issue}[/red]")
            
            if not Confirm.ask("\nContinue anyway?"):
                return False
        else:
            self.console.print("\n[bold green]✅ System ready[/bold green]")
        
        return True
    
    def display_email(self, email_data: Dict[str, Any], analysis: Optional[EmailAnalysisResult] = None) -> None:
        """
        Display email content and AI analysis
        
        Args:
            email_data: Email data dictionary
            analysis: AI analysis result (if available)
        """
        # Email header
        subject = email_data.get('subject', 'No Subject')
        sender = email_data.get('from', 'Unknown Sender')
        date = email_data.get('date', 'Unknown Date')
        email_id = email_data.get('id', 'unknown')
        
        header_table = Table(show_header=False, box=None, padding=(0, 1))
        header_table.add_column("Field", style="bold")
        header_table.add_column("Value")
        
        header_table.add_row("Subject:", subject)
        header_table.add_row("From:", sender)
        header_table.add_row("Date:", str(date))
        header_table.add_row("ID:", email_id)
        
        email_panel = Panel(
            header_table,
            title="📧 Email Details",
            border_style="cyan"
        )
        self.console.print(email_panel)
        
        # Email content preview
        content = email_data.get('body', email_data.get('text_content', 'No content available'))
        if len(content) > self.email_preview_length:
            content = content[:self.email_preview_length] + "\\n\\n[...truncated...]"
        
        content_panel = Panel(
            content,
            title="📄 Email Content (Preview)",
            border_style="dim"
        )
        self.console.print(content_panel)
        
        # AI Analysis (if available)
        if analysis:
            self.display_ai_analysis(analysis)
    
    def display_ai_analysis(self, analysis: EmailAnalysisResult) -> None:
        """Display AI analysis results"""
        # Create analysis table
        analysis_table = Table(show_header=False, box=None, padding=(0, 1))
        analysis_table.add_column("Field", style="bold")
        analysis_table.add_column("Value")
        
        # Color-code recommendation
        rec_color = "green" if analysis.recommendation == "KEEP" else "red"
        recommendation = f"[{rec_color}]{analysis.recommendation}[/{rec_color}]"
        
        # Format confidence as percentage with color coding
        confidence_color = self._get_confidence_color(analysis.confidence)
        confidence = f"[{confidence_color}]{analysis.confidence:.1%}[/{confidence_color}]"
        
        analysis_table.add_row("Recommendation:", recommendation)
        analysis_table.add_row("Category:", analysis.category)
        analysis_table.add_row("Confidence:", confidence)
        analysis_table.add_row("Reasoning:", analysis.reasoning)
        
        if analysis.key_factors:
            factors = "\\n".join([f"• {factor}" for factor in analysis.key_factors])
            analysis_table.add_row("Key Factors:", factors)
        
        if analysis.red_flags:
            flags = "\\n".join([f"⚠️ {flag}" for flag in analysis.red_flags])
            analysis_table.add_row("Red Flags:", f"[red]{flags}[/red]")
        
        # Add confidence interpretation
        confidence_text = self._get_confidence_interpretation(analysis.confidence)
        analysis_table.add_row("Confidence Level:", f"[dim]{confidence_text}[/dim]")
        
        ai_panel = Panel(
            analysis_table,
            title="🤖 AI Analysis",
            border_style="yellow"
        )
        self.console.print(ai_panel)
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence display based on level"""
        if confidence >= 0.8:
            return "green"
        elif confidence >= 0.6:
            return "yellow" 
        else:
            return "red"
    
    def _get_confidence_interpretation(self, confidence: float) -> str:
        """Get human-readable confidence interpretation"""
        if confidence >= 0.9:
            return "Very High - AI is very confident in this decision"
        elif confidence >= 0.8:
            return "High - AI is confident in this decision"
        elif confidence >= 0.7:
            return "Medium-High - AI is moderately confident"
        elif confidence >= 0.5:
            return "Medium - AI has some uncertainty"
        else:
            return "Low - AI is uncertain, human review recommended"
    
    def get_user_decision(self, analysis: Optional[EmailAnalysisResult] = None) -> Tuple[str, Optional[str], bool]:
        """
        Get user decision on email classification with confidence-based logic
        
        Args:
            analysis: AI analysis result (if available)
            
        Returns:
            Tuple of (decision, feedback, should_update_prompt) where:
            - decision is one of: 'keep', 'delete', 'skip', 'quit' 
            - feedback is user explanation (if provided)
            - should_update_prompt indicates if prompt should be updated based on this interaction
        """
        self.console.print("\\n" + "="*80)
        
        # Confidence-based interaction logic
        if analysis:
            confidence_level = self._get_confidence_level(analysis.confidence)
            
            if confidence_level == "low":
                # Low confidence: Always ask for human decision and reasoning
                self.console.print("[yellow]⚠️ AI has low confidence in this recommendation.[/yellow]")
                self.console.print("[dim]Your input is especially valuable here![/dim]\\n")
            elif confidence_level == "high" and self._is_auto_accept_candidate(analysis):
                # High confidence: Offer auto-accept option
                self.console.print(f"[green]✓ AI is confident in this recommendation: {analysis.recommendation}[/green]")
                
                if Confirm.ask(f"Accept AI recommendation to {analysis.recommendation.lower()}?", default=True):
                    decision = "delete" if analysis.recommendation == "JUNK-CANDIDATE" else "keep"
                    return decision, None, False  # High confidence + agreement = no prompt update needed
        
        # Show standard options
        options_text = """
[bold]What would you like to do with this email?[/bold]

[green]K[/green] - Keep this email
[red]D[/red] - Delete this email (mark as Junk-Candidate)
[yellow]S[/yellow] - Skip this email (decide later)
[blue]U[/blue] - Undo last action
[blue]Q[/blue] - Quit processing
[dim]?[/dim] - Show help
"""
        self.console.print(options_text)
        
        while True:
            choice = Prompt.ask(
                "Your decision",
                choices=["k", "d", "s", "u", "q", "?", "help"],
                default="k",
                show_choices=False
            ).lower()
            
            if choice in ["?", "help"]:
                self.show_help()
                continue
            elif choice == "k":
                decision = "keep"
                break
            elif choice == "d":
                decision = "delete"
                break
            elif choice == "s":
                decision = "skip"
                break
            elif choice == "u":
                decision = "undo"
                break
            elif choice == "q":
                decision = "quit"
                break
        
        # Determine if we should update the prompt and get feedback
        feedback = None
        should_update_prompt = False
        
        if analysis and decision not in ["skip", "quit", "undo"]:
            ai_wants_delete = analysis.recommendation == "JUNK-CANDIDATE"
            user_wants_delete = decision == "delete"
            disagreement = ai_wants_delete != user_wants_delete
            confidence_level = self._get_confidence_level(analysis.confidence)
            
            if disagreement:
                # User disagrees with AI
                self.console.print(f"\\n[yellow]You disagree with the AI recommendation ({analysis.recommendation})[/yellow]")
                should_update_prompt = True  # Always update on disagreement
                
                if Confirm.ask("Would you like to explain why? This helps improve the AI"):
                    feedback = Prompt.ask(
                        "Please explain your reasoning (this will help update the AI prompt)",
                        default=""
                    )
                    if feedback.strip():
                        self.console.print("[dim]Thank you! This feedback will be used to improve the AI.[/dim]")
                    else:
                        feedback = f"User chose to {decision} despite AI recommending {analysis.recommendation}"
            
            elif confidence_level == "low":
                # Low confidence, even if user agrees - ask if they want to reinforce this pattern
                self.console.print(f"\\n[dim]You agree with the AI's uncertain recommendation.[/dim]")
                
                if Confirm.ask("Would you like to help the AI be more confident about similar emails in the future?"):
                    feedback = Prompt.ask(
                        "What makes this clearly a candidate to " + ("delete" if user_wants_delete else "keep") + "?",
                        default=""
                    )
                    if feedback.strip():
                        should_update_prompt = True
                        self.console.print("[dim]Thank you! This will help the AI be more confident.[/dim]")
        
        return decision, feedback, should_update_prompt
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level category"""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _is_auto_accept_candidate(self, analysis: EmailAnalysisResult) -> bool:
        """Determine if this is a good candidate for auto-acceptance"""
        # Only offer auto-accept for very clear cases
        return (
            analysis.confidence >= 0.85 and
            analysis.category in [
                "Commercial/Marketing", 
                "Time-Sensitive Expired Content",
                "Social Media & Platform Notifications",
                "Obvious Spam & Suspicious Content"
            ]
        )
    
    def show_help(self):
        """Display help information"""
        help_text = """
[bold]EmailParse Interactive Help[/bold]

[bold green]Commands:[/bold green]
• [green]K[/green] - Keep: Mark email as important, leave in current location
• [red]D[/red] - Delete: Mark email as junk candidate, apply "Junk-Candidate" label
• [yellow]S[/yellow] - Skip: Skip this email for now, will be processed again later
• [blue]U[/blue] - Undo: Undo the last action (remove labels, restore state)
• [blue]Q[/blue] - Quit: Exit the processing session (progress is saved)

[bold yellow]AI Learning:[/bold yellow]
When you disagree with the AI's recommendation, you'll be asked to explain why.
This feedback helps improve the AI's future classifications by updating the prompt.

[bold blue]Tips:[/bold blue]
• The AI learns general patterns, not specific email content
• Focus on explaining the type of content or sender rather than specific details
• Your feedback helps classify similar emails better in the future

[bold red]Safety:[/bold red]
• When in doubt, choose Keep - it's safer to keep an email than delete it
• You can always manually delete emails later
• The AI defaults to Keep when uncertain
"""
        
        help_panel = Panel(help_text, title="Help", border_style="blue")
        self.console.print(help_panel)
    
    def display_session_stats(self):
        """Display current session statistics"""
        stats = self.session_stats
        elapsed = datetime.now() - stats['start_time']
        
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value", style="cyan")
        
        stats_table.add_row("Emails Processed:", str(stats['processed']))
        stats_table.add_row("Kept:", f"{stats['kept']} ({stats['kept']/max(1,stats['processed']):.1%})")
        stats_table.add_row("Deleted:", f"{stats['deleted']} ({stats['deleted']/max(1,stats['processed']):.1%})")
        stats_table.add_row("AI Agreements:", f"{stats['ai_agreements']} ({stats['ai_agreements']/max(1,stats['processed']):.1%})")
        stats_table.add_row("AI Disagreements:", f"{stats['ai_disagreements']} ({stats['ai_disagreements']/max(1,stats['processed']):.1%})")
        stats_table.add_row("Prompt Updates:", str(stats['prompt_updates']))
        stats_table.add_row("Session Time:", str(elapsed).split('.')[0])
        
        stats_panel = Panel(
            stats_table,
            title="📊 Session Statistics",
            border_style="green"
        )
        self.console.print(stats_panel)
    
    def process_user_feedback(self, email_data: Dict[str, Any], analysis: EmailAnalysisResult, 
                            user_feedback: str) -> bool:
        """
        Process user feedback and update the prompt if needed
        
        Args:
            email_data: Email data
            analysis: Original AI analysis
            user_feedback: User's explanation
            
        Returns:
            True if prompt was updated successfully
        """
        try:
            self.console.print("\\n[dim]Processing your feedback...[/dim]")
            
            # Get current prompt before update
            old_prompt = self.analyzer.prompt_engine.get_analysis_prompt()
            
            success = self.analyzer.update_prompt_from_feedback(
                email_data=email_data,
                user_feedback=user_feedback,
                original_analysis=analysis
            )
            
            if success:
                self.console.print("[green]AI prompt updated with your feedback![/green]")
                
                # Get updated prompt and show diff
                new_prompt = self.analyzer.prompt_engine.get_analysis_prompt()
                self.show_prompt_diff(old_prompt, new_prompt)
                
                return True
            else:
                self.console.print("[red]Failed to update AI prompt[/red]")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to process user feedback: {e}")
            self.console.print(f"[red]Error processing feedback: {e}[/red]")
            return False
    
    def show_prompt_diff(self, old_prompt: str, new_prompt: str):
        """
        Show a visual diff of prompt changes
        
        Args:
            old_prompt: Original prompt text
            new_prompt: Updated prompt text
        """
        try:
            # Split into lines for diffing
            old_lines = old_prompt.splitlines(keepends=True)
            new_lines = new_prompt.splitlines(keepends=True)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                old_lines, 
                new_lines,
                fromfile='Previous Prompt',
                tofile='Updated Prompt',
                lineterm='',
                n=3  # Context lines
            ))
            
            if not diff_lines:
                self.console.print("[dim]No changes detected in prompt[/dim]")
                return
            
            # Show diff summary first
            added_lines = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            removed_lines = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            
            if added_lines > 0 or removed_lines > 0:
                self.console.print(f"\\n[cyan]Prompt Changes: +{added_lines} additions, -{removed_lines} deletions[/cyan]")
                
                # Ask if user wants to see full diff
                if Confirm.ask("Show detailed prompt changes?", default=True):
                    self.display_detailed_diff(diff_lines)
            else:
                self.console.print("[dim]No significant changes to display[/dim]")
                
        except Exception as e:
            self.logger.error(f"Failed to generate prompt diff: {e}")
            self.console.print("[red]Could not display prompt changes[/red]")
    
    def display_detailed_diff(self, diff_lines: List[str]):
        """Display the detailed diff with syntax highlighting"""
        try:
            # Convert diff to string
            diff_text = ''.join(diff_lines)
            
            # Create syntax-highlighted diff
            diff_syntax = Syntax(
                diff_text, 
                "diff", 
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            
            # Display in a panel
            diff_panel = Panel(
                diff_syntax,
                title="[bold cyan]Prompt Changes[/bold cyan]",
                border_style="cyan",
                expand=False
            )
            
            self.console.print(diff_panel)
            
            # Show legend
            legend_text = """
[green]+[/green] Lines added to prompt
[red]-[/red] Lines removed from prompt  
[dim]Context lines shown for reference[/dim]
"""
            
            legend_panel = Panel.fit(
                legend_text,
                title="Legend",
                border_style="dim"
            )
            
            self.console.print(legend_panel)
            
        except Exception as e:
            self.logger.error(f"Failed to display detailed diff: {e}")
            # Fallback to simple text display
            self.console.print("\\n[cyan]Prompt Changes:[/cyan]")
            for line in diff_lines:
                if line.startswith('+') and not line.startswith('+++'):
                    self.console.print(f"[green]{line.rstrip()}[/green]")
                elif line.startswith('-') and not line.startswith('---'):
                    self.console.print(f"[red]{line.rstrip()}[/red]")
                elif not line.startswith(('@@', '+++', '---')):
                    self.console.print(f"[dim]{line.rstrip()}[/dim]")
    
    def update_session_stats(self, decision: str, analysis: Optional[EmailAnalysisResult], 
                           had_prompt_update: bool = False):
        """Update session statistics"""
        self.session_stats['processed'] += 1
        
        if decision == "keep":
            self.session_stats['kept'] += 1
        elif decision == "delete":
            self.session_stats['deleted'] += 1
        
        # Track AI agreement/disagreement
        if analysis:
            ai_wants_delete = analysis.recommendation == "JUNK-CANDIDATE"
            user_wants_delete = decision == "delete"
            
            if ai_wants_delete == user_wants_delete:
                self.session_stats['ai_agreements'] += 1
            else:
                self.session_stats['ai_disagreements'] += 1
        
        # Track prompt updates (when they actually happened)
        if had_prompt_update:
            self.session_stats['prompt_updates'] += 1
    
    def display_goodbye(self):
        """Display goodbye message with final stats"""
        self.console.print("\\n")
        
        goodbye_text = f"""
[bold blue]EmailParse Session Complete[/bold blue]

Thank you for using EmailParse! Your feedback helps improve the AI.

Final Statistics:
"""
        
        goodbye_panel = Panel.fit(goodbye_text, border_style="blue")
        self.console.print(goodbye_panel)
        
        self.display_session_stats()
        
        self.console.print("\\n[dim]Session saved. You can resume processing anytime.[/dim]")
        self.console.print("[dim]Goodbye! 👋[/dim]\\n")