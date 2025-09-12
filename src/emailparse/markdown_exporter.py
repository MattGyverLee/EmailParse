"""Markdown exporter for email batches"""

import os
from pathlib import Path
from typing import List, Dict, Any
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MarkdownExporter:
    """Export email batches to markdown files"""
    
    def __init__(self, output_dir: str = "email_exports"):
        """
        Initialize markdown exporter
        
        Args:
            output_dir: Directory to save markdown files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Markdown exporter initialized, output directory: {self.output_dir}")
    
    def export_batch(self, emails: List[Dict[str, Any]], batch_name: str = None) -> str:
        """
        Export a batch of emails to a markdown file
        
        Args:
            emails: List of email dictionaries
            batch_name: Optional name for the batch file
            
        Returns:
            Path to the created markdown file
        """
        if not emails:
            logger.warning("No emails to export")
            return ""
        
        # Generate filename
        if batch_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = f"email_batch_{timestamp}"
        
        filename = self._sanitize_filename(batch_name) + ".md"
        filepath = self.output_dir / filename
        
        # Generate markdown content
        markdown_content = self._generate_batch_markdown(emails, batch_name)
        
        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Exported {len(emails)} emails to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to write markdown file {filepath}: {e}")
            raise
    
    def export_single_email(self, email_data: Dict[str, Any], filename: str = None) -> str:
        """
        Export a single email to a markdown file
        
        Args:
            email_data: Email dictionary
            filename: Optional filename (will generate if not provided)
            
        Returns:
            Path to the created markdown file
        """
        if filename is None:
            subject = email_data.get('subject', 'No Subject')
            uid = email_data.get('uid', 'unknown')
            filename = f"email_{uid}_{self._sanitize_filename(subject)[:50]}"
        
        filename = self._sanitize_filename(filename) + ".md"
        filepath = self.output_dir / filename
        
        # Generate markdown content
        markdown_content = self._generate_single_email_markdown(email_data)
        
        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Exported email UID {email_data.get('uid')} to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to write markdown file {filepath}: {e}")
            raise
    
    def _generate_batch_markdown(self, emails: List[Dict[str, Any]], batch_name: str) -> str:
        """
        Generate markdown content for a batch of emails
        
        Args:
            emails: List of email dictionaries
            batch_name: Name of the batch
            
        Returns:
            Markdown content string
        """
        lines = []
        
        # Header
        lines.append(f"# Email Batch: {batch_name}")
        lines.append("")
        lines.append(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Emails:** {len(emails)}")
        lines.append("")
        
        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        for i, email_data in enumerate(emails, 1):
            subject = email_data.get('subject', 'No Subject')
            from_field = email_data.get('from', 'Unknown Sender')
            sender = ', '.join(from_field) if isinstance(from_field, list) else from_field
            lines.append(f"{i}. [{subject}](#email-{i}) - *{sender}*")
        lines.append("")
        
        # Individual emails
        for i, email_data in enumerate(emails, 1):
            email_md = self._generate_single_email_section(email_data, i)
            lines.append(email_md)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_single_email_markdown(self, email_data: Dict[str, Any]) -> str:
        """
        Generate markdown content for a single email
        
        Args:
            email_data: Email dictionary
            
        Returns:
            Markdown content string
        """
        lines = []
        
        subject = email_data.get('subject', 'No Subject')
        lines.append(f"# {subject}")
        lines.append("")
        
        # Email metadata
        lines.append("## Email Details")
        lines.append("")
        
        # Handle from field (could be string or list)
        from_field = email_data.get('from', 'Unknown')
        if isinstance(from_field, list):
            from_display = ', '.join(from_field)
        else:
            from_display = from_field
        
        # Handle to field (could be string or list)
        to_field = email_data.get('to', 'Unknown')
        if isinstance(to_field, list):
            to_display = ', '.join(to_field)
        else:
            to_display = to_field
        
        lines.append(f"- **UID:** {email_data.get('uid', 'Unknown')}")
        lines.append(f"- **From:** {from_display}")
        lines.append(f"- **To:** {to_display}")
        lines.append(f"- **Date:** {email_data.get('date_str', 'Unknown')}")
        lines.append(f"- **Size:** {email_data.get('raw_size_mb', 0)} MB")
        
        if email_data.get('message_id'):
            lines.append(f"- **Message ID:** `{email_data['message_id']}`")
        
        lines.append("")
        
        # Email body
        lines.append("## Email Content")
        lines.append("")
        
        body = email_data.get('body', '(No content)')
        # Escape any markdown that might be in the email content
        body = self._escape_markdown(body)
        
        # Wrap in code block to preserve formatting
        lines.append("```")
        lines.append(body)
        lines.append("```")
        
        return "\n".join(lines)
    
    def _generate_single_email_section(self, email_data: Dict[str, Any], email_num: int) -> str:
        """
        Generate markdown section for a single email within a batch
        
        Args:
            email_data: Email dictionary
            email_num: Email number in the batch
            
        Returns:
            Markdown section string
        """
        lines = []
        
        subject = email_data.get('subject', 'No Subject')
        lines.append(f"## Email {email_num}")
        lines.append(f'<a id="email-{email_num}"></a>')
        lines.append("")
        lines.append(f"### {subject}")
        lines.append("")
        
        # Handle from/to fields for display
        from_field = email_data.get('from', 'Unknown')
        from_display = ', '.join(from_field) if isinstance(from_field, list) else from_field
        
        to_field = email_data.get('to', 'Unknown')
        to_display = ', '.join(to_field) if isinstance(to_field, list) else to_field
        
        # Metadata table
        lines.append("| Field | Value |")
        lines.append("|-------|--------|")
        lines.append(f"| UID | {email_data.get('uid', 'Unknown')} |")
        lines.append(f"| From | {from_display} |")
        lines.append(f"| To | {to_display} |")
        lines.append(f"| Date | {email_data.get('date_str', 'Unknown')} |")
        lines.append(f"| Size | {email_data.get('raw_size_mb', 0)} MB |")
        lines.append("")
        
        # Body preview (truncated for batch view)
        lines.append("#### Content Preview")
        lines.append("")
        
        body = email_data.get('body', '(No content)')
        # Truncate for batch view
        if len(body) > 500:
            body = body[:500] + "\n\n[... truncated in batch view ...]"
        
        body = self._escape_markdown(body)
        
        lines.append("```")
        lines.append(body)
        lines.append("```")
        
        return "\n".join(lines)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for filesystem compatibility
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Trim and remove leading/trailing underscores
        sanitized = sanitized.strip('_. ')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized or "unnamed"
    
    def _escape_markdown(self, text: str) -> str:
        """
        Escape markdown special characters in text
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        if not text:
            return text
        
        # Don't escape content that will be in code blocks
        # The code block itself handles the escaping
        return text
    
    def create_index_file(self, batch_files: List[str]) -> str:
        """
        Create an index markdown file listing all exported batches
        
        Args:
            batch_files: List of batch file paths
            
        Returns:
            Path to index file
        """
        index_path = self.output_dir / "index.md"
        
        lines = []
        lines.append("# Email Export Index")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Batches:** {len(batch_files)}")
        lines.append("")
        
        if batch_files:
            lines.append("## Exported Batches")
            lines.append("")
            
            for batch_file in batch_files:
                batch_path = Path(batch_file)
                relative_path = batch_path.relative_to(self.output_dir) if batch_path.is_absolute() else batch_path
                file_stats = os.stat(batch_file) if os.path.exists(batch_file) else None
                
                if file_stats:
                    file_size = round(file_stats.st_size / 1024, 1)  # KB
                    mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                    lines.append(f"- [{relative_path.name}]({relative_path}) ({file_size} KB, modified: {mod_time})")
                else:
                    lines.append(f"- [{relative_path.name}]({relative_path})")
            
            lines.append("")
        else:
            lines.append("*No batches exported yet.*")
            lines.append("")
        
        # Write index file
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            logger.info(f"Created index file: {index_path}")
            return str(index_path)
            
        except Exception as e:
            logger.error(f"Failed to create index file: {e}")
            raise