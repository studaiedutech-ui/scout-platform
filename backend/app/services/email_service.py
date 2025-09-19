"""
Email Service for SaaS Platform
Handles transactional emails and notifications
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending transactional emails
    """
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 from_email: str, from_name: str = "S.C.O.U.T. Platform"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        
        # Setup Jinja2 for email templates
        self.jinja_env = Environment(
            loader=FileSystemLoader('app/templates/emails'),
            autoescape=True
        )
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   text_content: Optional[str] = None, to_name: Optional[str] = None) -> bool:
        """
        Send an email
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            
            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_template_email(self, to_email: str, template_name: str, context: Dict[str, Any],
                           to_name: Optional[str] = None) -> bool:
        """
        Send an email using a template
        """
        try:
            # Load and render template
            template = self.jinja_env.get_template(f"{template_name}.html")
            html_content = template.render(**context)
            
            # Get subject from context or use default
            subject = context.get('subject', 'Notification from S.C.O.U.T. Platform')
            
            return self.send_email(to_email, subject, html_content, to_name=to_name)
            
        except Exception as e:
            logger.error(f"Failed to send template email {template_name} to {to_email}: {str(e)}")
            return False


class NotificationService:
    """
    High-level notification service for SaaS events
    """
    
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
    
    # User Management Notifications
    
    def send_welcome_email(self, user_email: str, user_name: str, company_name: str, 
                          activation_link: str) -> bool:
        """
        Send welcome email to new users
        """
        context = {
            'subject': f'Welcome to S.C.O.U.T. Platform - {company_name}',
            'user_name': user_name,
            'company_name': company_name,
            'activation_link': activation_link,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='welcome',
            context=context,
            to_name=user_name
        )
    
    def send_password_reset_email(self, user_email: str, user_name: str, reset_link: str) -> bool:
        """
        Send password reset email
        """
        context = {
            'subject': 'Reset Your S.C.O.U.T. Platform Password',
            'user_name': user_name,
            'reset_link': reset_link,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='password_reset',
            context=context,
            to_name=user_name
        )
    
    def send_email_verification(self, user_email: str, user_name: str, verification_link: str) -> bool:
        """
        Send email verification
        """
        context = {
            'subject': 'Verify Your Email Address - S.C.O.U.T. Platform',
            'user_name': user_name,
            'verification_link': verification_link,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='email_verification',
            context=context,
            to_name=user_name
        )
    
    # Subscription Notifications
    
    def send_subscription_welcome(self, user_email: str, user_name: str, company_name: str,
                                 plan_name: str, trial_days: int) -> bool:
        """
        Send subscription welcome email
        """
        context = {
            'subject': f'Welcome to {plan_name} Plan - S.C.O.U.T. Platform',
            'user_name': user_name,
            'company_name': company_name,
            'plan_name': plan_name,
            'trial_days': trial_days,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='subscription_welcome',
            context=context,
            to_name=user_name
        )
    
    def send_trial_ending_warning(self, user_email: str, user_name: str, company_name: str,
                                 days_remaining: int) -> bool:
        """
        Send trial ending warning
        """
        context = {
            'subject': f'Your Trial Ends in {days_remaining} Days - S.C.O.U.T. Platform',
            'user_name': user_name,
            'company_name': company_name,
            'days_remaining': days_remaining,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='trial_ending',
            context=context,
            to_name=user_name
        )
    
    def send_payment_failed(self, user_email: str, user_name: str, company_name: str,
                           plan_name: str, amount: float) -> bool:
        """
        Send payment failed notification
        """
        context = {
            'subject': 'Payment Failed - S.C.O.U.T. Platform',
            'user_name': user_name,
            'company_name': company_name,
            'plan_name': plan_name,
            'amount': amount,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=user_email,
            template_name='payment_failed',
            context=context,
            to_name=user_name
        )
    
    # Recruitment Notifications
    
    def send_new_application(self, recruiter_email: str, recruiter_name: str, 
                           candidate_name: str, job_title: str, company_name: str) -> bool:
        """
        Notify recruiter of new application
        """
        context = {
            'subject': f'New Application: {candidate_name} for {job_title}',
            'recruiter_name': recruiter_name,
            'candidate_name': candidate_name,
            'job_title': job_title,
            'company_name': company_name,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=recruiter_email,
            template_name='new_application',
            context=context,
            to_name=recruiter_name
        )
    
    def send_assessment_invitation(self, candidate_email: str, candidate_name: str,
                                  job_title: str, company_name: str, assessment_link: str) -> bool:
        """
        Send assessment invitation to candidate
        """
        context = {
            'subject': f'Assessment Invitation: {job_title} at {company_name}',
            'candidate_name': candidate_name,
            'job_title': job_title,
            'company_name': company_name,
            'assessment_link': assessment_link,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=candidate_email,
            template_name='assessment_invitation',
            context=context,
            to_name=candidate_name
        )
    
    def send_assessment_completed(self, recruiter_email: str, recruiter_name: str,
                                candidate_name: str, job_title: str, score: float) -> bool:
        """
        Notify recruiter that assessment is completed
        """
        context = {
            'subject': f'Assessment Completed: {candidate_name} for {job_title}',
            'recruiter_name': recruiter_name,
            'candidate_name': candidate_name,
            'job_title': job_title,
            'score': score,
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=recruiter_email,
            template_name='assessment_completed',
            context=context,
            to_name=recruiter_name
        )
    
    # System Notifications
    
    def send_usage_alert(self, admin_email: str, admin_name: str, company_name: str,
                        resource_type: str, current_usage: int, limit: int) -> bool:
        """
        Send usage limit alert
        """
        usage_percentage = (current_usage / limit) * 100 if limit > 0 else 100
        
        context = {
            'subject': f'Usage Alert: {resource_type} - {company_name}',
            'admin_name': admin_name,
            'company_name': company_name,
            'resource_type': resource_type,
            'current_usage': current_usage,
            'limit': limit,
            'usage_percentage': round(usage_percentage, 1),
            'year': datetime.now().year
        }
        
        return self.email_service.send_template_email(
            to_email=admin_email,
            template_name='usage_alert',
            context=context,
            to_name=admin_name
        )


# Email templates would be created in backend/app/templates/emails/
# For now, let's create a simple template creator

def create_email_templates():
    """
    Create basic email templates for the notification system
    """
    import os
    
    template_dir = "app/templates/emails"
    os.makedirs(template_dir, exist_ok=True)
    
    templates = {
        'welcome.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to S.C.O.U.T. Platform</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to S.C.O.U.T. Platform</h1>
        </div>
        <div class="content">
            <h2>Hello {{ user_name }}!</h2>
            <p>Welcome to {{ company_name }} on the S.C.O.U.T. Platform! We're excited to help you transform your recruitment process with AI-powered talent acquisition.</p>
            <p>To get started, please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{{ activation_link }}" class="button">Verify Email Address</a>
            </p>
            <p>If you have any questions, feel free to reach out to our support team.</p>
            <p>Best regards,<br>The S.C.O.U.T. Platform Team</p>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} S.C.O.U.T. Platform. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        ''',
        
        'subscription_welcome.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to {{ plan_name }} Plan</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .highlight { background: #e9ecef; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{ plan_name }} Plan!</h1>
        </div>
        <div class="content">
            <h2>Hello {{ user_name }}!</h2>
            <p>Congratulations! {{ company_name }} is now subscribed to the {{ plan_name }} plan on S.C.O.U.T. Platform.</p>
            <div class="highlight">
                <h3>Your {{ trial_days }}-day trial has started!</h3>
                <p>You have full access to all {{ plan_name }} features for the next {{ trial_days }} days. No payment required during your trial period.</p>
            </div>
            <p>Here's what you can do next:</p>
            <ul>
                <li>Create your first job posting</li>
                <li>Set up AI-powered assessments</li>
                <li>Invite team members</li>
                <li>Customize your company profile</li>
            </ul>
            <p>Best regards,<br>The S.C.O.U.T. Platform Team</p>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} S.C.O.U.T. Platform. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        '''
    }
    
    for filename, content in templates.items():
        with open(os.path.join(template_dir, filename), 'w') as f:
            f.write(content.strip())
    
    print(f"Created {len(templates)} email templates in {template_dir}")


if __name__ == "__main__":
    create_email_templates()