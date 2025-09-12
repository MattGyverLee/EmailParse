"""Test fixtures package"""

from .sample_emails import (
    create_test_email,
    create_newsletter_email,
    create_promotional_email,
    create_important_email,
    create_meeting_email,
    create_receipt_email,
    create_spam_email,
    get_sample_email_batch,
    get_junk_email_samples,
    get_keep_email_samples,
)

__all__ = [
    'create_test_email',
    'create_newsletter_email',
    'create_promotional_email',
    'create_important_email',
    'create_meeting_email',
    'create_receipt_email',
    'create_spam_email',
    'get_sample_email_batch',
    'get_junk_email_samples',
    'get_keep_email_samples',
]