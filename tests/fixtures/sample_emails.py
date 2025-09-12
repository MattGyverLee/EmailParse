"""Sample email fixtures for testing"""

from datetime import datetime, timezone
from typing import List, Dict, Any

def create_test_email(
    uid: int = 12345,
    subject: str = "Test Email",
    sender: str = "test@example.com",
    body: str = "Test email body content",
    **kwargs
) -> Dict[str, Any]:
    """Create a test email with default values"""
    
    default_email = {
        'uid': uid,
        'subject': subject,
        'from': [sender],
        'to': ['recipient@example.com'],
        'date': datetime.now(timezone.utc).isoformat(),
        'size': len(body),
        'body': body,
        'headers': {
            'Message-ID': f'<test-{uid}@example.com>',
            'Content-Type': 'text/plain; charset=utf-8',
            'From': sender,
            'To': 'recipient@example.com',
            'Subject': subject,
        }
    }
    
    # Update with any provided overrides
    default_email.update(kwargs)
    return default_email

def create_newsletter_email(uid: int = 20001) -> Dict[str, Any]:
    """Create a newsletter-style email (likely junk)"""
    return create_test_email(
        uid=uid,
        subject="Weekly Newsletter - Tech Updates",
        sender="newsletter@techsite.com",
        body="""
        This week's top tech stories:
        - AI breakthrough in natural language processing
        - New smartphone releases
        - Cryptocurrency market updates
        
        Click here to unsubscribe: http://techsite.com/unsubscribe
        View in browser: http://techsite.com/newsletter/week-45
        """,
        headers={
            'List-Unsubscribe': '<http://techsite.com/unsubscribe>',
            'Precedence': 'bulk',
        }
    )

def create_promotional_email(uid: int = 20002) -> Dict[str, Any]:
    """Create a promotional email (likely junk)"""
    return create_test_email(
        uid=uid,
        subject="🎉 SALE: 50% Off Everything - Limited Time!",
        sender="deals@retailstore.com",
        body="""
        FLASH SALE! 
        
        Get 50% off everything in our store!
        Use code: SAVE50
        
        ⏰ Hurry! Sale ends tonight at midnight!
        
        Shop now: http://retailstore.com/sale
        Unsubscribe: http://retailstore.com/unsubscribe
        """,
        headers={
            'X-Mailer': 'MailChimp',
            'List-Unsubscribe': '<http://retailstore.com/unsubscribe>',
        }
    )

def create_important_email(uid: int = 20003) -> Dict[str, Any]:
    """Create an important email (should keep)"""
    return create_test_email(
        uid=uid,
        subject="Your Amazon Order Has Shipped - Tracking Information",
        sender="auto-confirm@amazon.com",
        body="""
        Hello,
        
        Your Amazon order #123-4567890-1234567 has shipped!
        
        Order Details:
        - MacBook Pro 14" (1x)
        - Expected delivery: January 18, 2025
        
        Tracking Number: 1Z999AA1234567890
        
        Track your package: https://amazon.com/tracking/1Z999AA1234567890
        
        Thank you for your order!
        Amazon Customer Service
        """,
        headers={
            'From': 'Amazon.com <auto-confirm@amazon.com>',
            'Authentication-Results': 'spf=pass smtp.mailfrom=amazon.com',
        }
    )

def create_meeting_email(uid: int = 20004) -> Dict[str, Any]:
    """Create a meeting invitation (should keep)"""
    return create_test_email(
        uid=uid,
        subject="Meeting Invitation: Project Review - January 20, 2025",
        sender="colleague@company.com",
        body="""
        Hi,
        
        You're invited to join our project review meeting:
        
        Date: Monday, January 20, 2025
        Time: 2:00 PM - 3:00 PM (EST)
        Location: Conference Room B / Zoom
        
        Agenda:
        - Q4 project status review
        - Q1 planning discussion
        - Action items review
        
        Please confirm your attendance.
        
        Best regards,
        Sarah Johnson
        Project Manager
        """,
        headers={
            'Content-Type': 'text/calendar; method=REQUEST',
            'X-MS-Exchange-Organization': 'company.com',
        }
    )

def create_receipt_email(uid: int = 20005) -> Dict[str, Any]:
    """Create a receipt email (should keep)"""
    return create_test_email(
        uid=uid,
        subject="Receipt for your Stripe payment (inv_1234567890)",
        sender="receipts@stripe.com",
        body="""
        Receipt from Stripe
        
        Thanks for your payment!
        
        Amount: $29.99
        Description: Monthly subscription - EmailParse Pro
        Invoice: inv_1234567890
        Date: January 15, 2025
        
        Payment Method: •••• •••• •••• 1234
        
        Download PDF: https://stripe.com/receipts/inv_1234567890
        
        Questions? Contact support@emailparse.com
        """,
        headers={
            'From': 'Stripe <receipts@stripe.com>',
            'X-Stripe-Envelope-From': 'receipts@stripe.com',
        }
    )

def create_spam_email(uid: int = 20006) -> Dict[str, Any]:
    """Create an obvious spam email"""
    return create_test_email(
        uid=uid,
        subject="Re: Congratulations! You've Won $1,000,000!!!",
        sender="winner@lottery-scam.suspicious",
        body="""
        CONGRATULATIONS!!!
        
        You have been selected as the LUCKY WINNER of our international lottery!
        You have won $1,000,000 USD!!!
        
        To claim your prize, send us:
        - Your full name
        - Your bank account details
        - A processing fee of $500
        
        Act now! This offer expires in 24 hours!
        
        Reply immediately to claim your prize!
        """,
        headers={
            'X-Spam-Score': '15.2',
            'X-Spam-Flag': 'YES',
        }
    )

def get_sample_email_batch() -> List[Dict[str, Any]]:
    """Get a batch of sample emails for testing"""
    return [
        create_newsletter_email(30001),
        create_important_email(30002),
        create_promotional_email(30003),
        create_meeting_email(30004),
        create_receipt_email(30005),
        create_spam_email(30006),
        create_test_email(30007, "Regular personal email", "friend@gmail.com", "Hey, want to grab coffee later?"),
        create_test_email(30008, "Work email", "boss@company.com", "Please review the quarterly report by Friday."),
        create_promotional_email(30009),
        create_newsletter_email(30010),
    ]

def get_junk_email_samples() -> List[Dict[str, Any]]:
    """Get emails that should be classified as junk"""
    return [
        create_newsletter_email(),
        create_promotional_email(),
        create_spam_email(),
    ]

def get_keep_email_samples() -> List[Dict[str, Any]]:
    """Get emails that should be kept"""
    return [
        create_important_email(),
        create_meeting_email(),
        create_receipt_email(),
    ]