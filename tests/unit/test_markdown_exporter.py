"""Tests for markdown exporter"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
import os

from emailparse.markdown_exporter import MarkdownExporter
from tests.fixtures import get_sample_email_batch, create_important_email

class TestMarkdownExporter:
    """Test markdown export functionality"""
    
    @pytest.fixture
    def temp_export_dir(self):
        """Create temporary export directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def exporter(self, temp_export_dir):
        """Create markdown exporter with temp directory"""
        return MarkdownExporter(temp_export_dir)
    
    @pytest.mark.unit
    def test_init(self, temp_export_dir):
        """Test markdown exporter initialization"""
        exporter = MarkdownExporter(temp_export_dir)
        
        assert exporter.output_dir == Path(temp_export_dir)
        assert exporter.output_dir.exists()
    
    @pytest.mark.unit
    def test_init_creates_directory(self, temp_export_dir):
        """Test that initialization creates output directory"""
        export_path = Path(temp_export_dir) / "new_export_dir"
        assert not export_path.exists()
        
        exporter = MarkdownExporter(str(export_path))
        
        assert export_path.exists()
        assert export_path.is_dir()
    
    @pytest.mark.unit
    def test_sanitize_filename(self, exporter):
        """Test filename sanitization"""
        # Test with problematic characters
        result = exporter._sanitize_filename('test<>:"/\\|?*file')
        assert result == 'test_file'
        
        # Test with multiple underscores
        result = exporter._sanitize_filename('test___file___name')
        assert result == 'test_file_name'
        
        # Test with leading/trailing spaces and dots
        result = exporter._sanitize_filename('  .test file.  ')
        assert result == 'test file'
        
        # Test with long filename
        long_name = 'a' * 150
        result = exporter._sanitize_filename(long_name)
        assert len(result) <= 100
        
        # Test with empty string
        result = exporter._sanitize_filename('')
        assert result == 'unnamed'
    
    @pytest.mark.unit
    def test_export_single_email(self, exporter):
        """Test single email export"""
        email_data = create_important_email()
        
        result_path = exporter.export_single_email(email_data)
        
        assert os.path.exists(result_path)
        
        # Check file content
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain email details
        assert email_data['subject'] in content
        # From field should be converted from list to string
        from_display = ', '.join(email_data['from']) if isinstance(email_data['from'], list) else email_data['from']
        assert from_display in content
        assert str(email_data['uid']) in content
        assert "Email Details" in content
        assert "Email Content" in content
        
        # Should contain body in code block
        assert "```" in content
        assert email_data['body'] in content
    
    @pytest.mark.unit
    def test_export_single_email_with_custom_filename(self, exporter):
        """Test single email export with custom filename"""
        email_data = create_important_email()
        custom_filename = "custom_email_export"
        
        result_path = exporter.export_single_email(email_data, custom_filename)
        
        assert custom_filename in result_path
        assert result_path.endswith('.md')
        assert os.path.exists(result_path)
    
    @pytest.mark.unit
    def test_export_batch(self, exporter):
        """Test batch email export"""
        emails = get_sample_email_batch()
        batch_name = "test_batch"
        
        result_path = exporter.export_batch(emails, batch_name)
        
        assert os.path.exists(result_path)
        assert batch_name in result_path
        
        # Check file content
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain batch header
        assert f"# Email Batch: {batch_name}" in content
        assert f"**Total Emails:** {len(emails)}" in content
        
        # Should contain table of contents
        assert "## Table of Contents" in content
        
        # Should contain all emails
        for i, email in enumerate(emails, 1):
            assert f"## Email {i}" in content
            assert email['subject'] in content
        
        # Should have separators between emails
        assert "---" in content
    
    @pytest.mark.unit
    def test_export_batch_empty(self, exporter):
        """Test exporting empty batch"""
        result_path = exporter.export_batch([])
        
        assert result_path == ""
    
    @pytest.mark.unit
    def test_export_batch_auto_filename(self, exporter):
        """Test batch export with automatic filename generation"""
        emails = get_sample_email_batch()[:3]  # Just use 3 emails
        
        with patch('emailparse.markdown_exporter.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250115_143000"
            
            result_path = exporter.export_batch(emails)
            
            assert "email_batch_20250115_143000" in result_path
            assert os.path.exists(result_path)
    
    @pytest.mark.unit
    def test_generate_single_email_section(self, exporter):
        """Test single email section generation"""
        email_data = create_important_email()
        
        markdown = exporter._generate_single_email_section(email_data, 1)
        
        assert "## Email 1" in markdown
        assert f'<a id="email-1"></a>' in markdown
        assert email_data['subject'] in markdown
        assert "| Field | Value |" in markdown
        assert "| UID |" in markdown
        assert "| From |" in markdown
        assert "#### Content Preview" in markdown
        
        # Should truncate content in batch view
        if len(email_data['body']) > 500:
            assert "[... truncated in batch view ...]" in markdown
    
    @pytest.mark.unit
    def test_generate_single_email_markdown(self, exporter):
        """Test single email markdown generation"""
        email_data = create_important_email()
        
        markdown = exporter._generate_single_email_markdown(email_data)
        
        assert f"# {email_data['subject']}" in markdown
        assert "## Email Details" in markdown
        assert "## Email Content" in markdown
        assert f"- **UID:** {email_data['uid']}" in markdown
        # From field is converted from list to string
        from_display = ', '.join(email_data['from']) if isinstance(email_data['from'], list) else email_data['from']
        assert f"- **From:** {from_display}" in markdown
        assert "```" in markdown  # Code block for content
    
    @pytest.mark.unit
    def test_generate_batch_markdown(self, exporter):
        """Test batch markdown generation"""
        emails = get_sample_email_batch()[:3]  # Use 3 emails
        batch_name = "test_batch"
        
        markdown = exporter._generate_batch_markdown(emails, batch_name)
        
        assert f"# Email Batch: {batch_name}" in markdown
        assert f"**Total Emails:** {len(emails)}" in markdown
        assert "## Table of Contents" in markdown
        
        # Check TOC entries
        for i, email in enumerate(emails, 1):
            assert f"{i}. [{email['subject']}](#email-{i})" in markdown
        
        # Check individual email sections
        for i in range(1, len(emails) + 1):
            assert f"## Email {i}" in markdown
            assert f'<a id="email-{i}"></a>' in markdown
        
        # Check separators - there are separators in the email content as well,
        # so we should check that there are at least len(emails) separators
        separator_count = markdown.count("---")
        assert separator_count >= len(emails)  # At least one separator per email
    
    @pytest.mark.unit
    def test_create_index_file(self, exporter):
        """Test index file creation"""
        # Create some batch files first
        emails1 = get_sample_email_batch()[:2]
        emails2 = get_sample_email_batch()[2:4]
        
        batch_file1 = exporter.export_batch(emails1, "batch_1")
        batch_file2 = exporter.export_batch(emails2, "batch_2")
        
        batch_files = [batch_file1, batch_file2]
        
        index_path = exporter.create_index_file(batch_files)
        
        assert os.path.exists(index_path)
        assert "index.md" in index_path
        
        # Check index content
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "# Email Export Index" in content
        assert f"**Total Batches:** {len(batch_files)}" in content
        assert "## Exported Batches" in content
        
        # Should contain links to batch files
        for batch_file in batch_files:
            batch_name = Path(batch_file).name
            assert batch_name in content
    
    @pytest.mark.unit
    def test_create_index_file_empty(self, exporter):
        """Test index file creation with no batches"""
        index_path = exporter.create_index_file([])
        
        assert os.path.exists(index_path)
        
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "**Total Batches:** 0" in content
        assert "*No batches exported yet.*" in content
    
    @pytest.mark.unit
    def test_escape_markdown(self, exporter):
        """Test markdown escaping (currently no-op)"""
        test_text = "This has **bold** and *italic* markdown"
        
        result = exporter._escape_markdown(test_text)
        
        # Currently just returns the text as-is
        assert result == test_text
    
    @pytest.mark.unit
    def test_export_email_with_special_characters(self, exporter):
        """Test exporting email with special characters"""
        email_data = {
            'uid': 12345,
            'subject': 'Test with émojis 📧 and spëcial chars',
            'from': 'sender@example.com',
            'to': 'recipient@example.com',
            'date_str': '2025-01-15T10:30:00+00:00',
            'raw_size_mb': 0.1,
            'body': 'Email with UTF-8: café, naïve, résumé 🎉',
            'message_id': '<test@example.com>'
        }
        
        result_path = exporter.export_single_email(email_data)
        
        assert os.path.exists(result_path)
        
        # Check that UTF-8 content is preserved
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'émojis 📧' in content
        assert 'café, naïve, résumé 🎉' in content
    
    @pytest.mark.unit
    def test_export_email_with_long_body(self, exporter):
        """Test exporting email with very long body"""
        long_body = "A" * 15000  # Longer than typical truncation limit
        
        email_data = {
            'uid': 12345,
            'subject': 'Long email test',
            'from': 'sender@example.com',
            'to': 'recipient@example.com',
            'date_str': '2025-01-15T10:30:00+00:00',
            'raw_size_mb': 15.0,
            'body': long_body,
            'message_id': '<test@example.com>'
        }
        
        result_path = exporter.export_single_email(email_data)
        
        assert os.path.exists(result_path)
        
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain the full body in single email export
        assert long_body in content
    
    @pytest.mark.unit
    def test_batch_export_truncation(self, exporter):
        """Test that batch export truncates long content"""
        long_body = "B" * 1000  # Longer than 500 char batch limit
        
        email_data = {
            'uid': 12345,
            'subject': 'Long email in batch',
            'from': 'sender@example.com',
            'to': 'recipient@example.com',
            'date_str': '2025-01-15T10:30:00+00:00',
            'raw_size_mb': 1.0,
            'body': long_body,
            'message_id': '<test@example.com>'
        }
        
        result_path = exporter.export_batch([email_data], "truncation_test")
        
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should be truncated in batch view
        assert "[... truncated in batch view ...]" in content
        assert long_body not in content  # Full content shouldn't be there