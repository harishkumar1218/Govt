import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.config_loader import load_platform_config

logger = logging.getLogger(__name__)

def send_system_email(subject, recipient_list, template_name=None, context=None, body=None):
    """
    Base utility to send scalable system emails.
    If template_name is provided, it attempts to render an HTML email (fallback to text).
    If body is provided, it sends a simple text email.
    """
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@upscaspire.com')
        
        if template_name and context:
            try:
                html_message = render_to_string(template_name, context)
                plain_message = strip_tags(html_message)
                send_mail(
                    subject,
                    plain_message,
                    from_email,
                    recipient_list,
                    html_message=html_message,
                    fail_silently=False,
                )
                logger.info(f"HTML Email sent successfully to {recipient_list}")
                return True
            except Exception as e:
                logger.warning(f"Template rendering failed, falling back to plain text. Error: {str(e)}")
        
        plain_message = body if body else "This is an automated message."
        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Plain text Email sent successfully to {recipient_list}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
        return False

def send_mock_test_registration_email(user, date, quiz=None):
    """
    Specific function to send a registration confirmation for Daily Mock Tests.
    """
    platform = load_platform_config()
    quiz_cfg = platform['quiz']
    start_hour = quiz_cfg['default_start_hour']
    start_minute = quiz_cfg['default_start_minute']
    start_label = f"{start_hour % 12 or 12}:{start_minute:02d} {'PM' if start_hour >= 12 else 'AM'}"

    if quiz and quiz.starts_at:
        start_label = quiz.starts_at.strftime('%I:%M %p')

    subject = "Registration Confirmed: Daily All-India Mock Test"
    body = f"""Hello {user.first_name or user.username},

You have successfully registered for the Daily All-India Mock Test Challenge scheduled for {date.strftime('%B %d, %Y')}.

The live test window opens at {start_label}. Please ensure you log in to the {platform['app_name']} portal on time to participate and secure your spot on the Global Leaderboard!

Get ready to test your knowledge!

Best Regards,
The {platform['app_name']} AI Team
"""
    
    return send_system_email(
        subject=subject,
        recipient_list=[user.email],
        body=body
    )
