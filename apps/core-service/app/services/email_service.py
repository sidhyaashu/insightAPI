"""Core Service — Email Service: Dispatches standard professional HTML & plain-text emails."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from app.core.config import settings

logger = logging.getLogger("core.email")


class EmailService:
    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, text_content: str, html_content: str) -> None:
        """Internal helper to dispatch standard multipart HTML & plain text emails via SMTP."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info("[DEV EMAIL] SMTP credentials not configured. Email logged to console.")
            return

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
            msg["To"] = to_email

            # Set plain text as primary fallback
            msg.set_content(text_content)
            # Add HTML alternative for rich rendering
            msg.add_alternative(html_content, subtype="html")

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"[SMTP DISPATCH] Successfully delivered professional email to {to_email}")
        except Exception as e:
            logger.error(f"[SMTP ERROR] Failed to deliver email to {to_email}: {e}")

    @staticmethod
    def _build_html_template(title: str, preheader: str, content_html: str) -> str:
        """Standard professional HTML email layout compatible with Gmail, Outlook, Apple Mail."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f4f4f5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
      color: #18181b;
    }}
    .wrapper {{
      width: 100%;
      table-layout: fixed;
      background-color: #f4f4f5;
      padding: 40px 0;
    }}
    .container {{
      max-width: 580px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 16px;
      border: 1px solid #e4e4e7;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }}
    .header {{
      background-color: #18181b;
      padding: 28px 32px;
      text-align: left;
    }}
    .brand {{
      color: #ffffff;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.5px;
      text-decoration: none;
      font-family: monospace;
    }}
    .content {{
      padding: 36px 32px;
    }}
    .title {{
      font-size: 22px;
      font-weight: 700;
      color: #09090b;
      margin-top: 0;
      margin-bottom: 16px;
      letter-spacing: -0.4px;
    }}
    .paragraph {{
      font-size: 14px;
      line-height: 1.6;
      color: #52525b;
      margin-top: 0;
      margin-bottom: 24px;
    }}
    .btn-container {{
      margin: 32px 0;
      text-align: left;
    }}
    .btn {{
      display: inline-block;
      background-color: #18181b;
      color: #ffffff !important;
      font-size: 14px;
      font-weight: 600;
      padding: 14px 28px;
      border-radius: 10px;
      text-decoration: none;
      text-align: center;
      transition: background-color 0.2s ease;
    }}
    .fallback {{
      background-color: #f4f4f5;
      border: 1px solid #e4e4e7;
      border-radius: 10px;
      padding: 16px;
      margin-top: 28px;
      font-size: 12px;
      color: #71717a;
      word-break: break-all;
    }}
    .fallback-url {{
      color: #18181b;
      font-family: monospace;
      font-size: 11px;
      display: block;
      margin-top: 6px;
    }}
    .footer {{
      border-top: 1px solid #f4f4f5;
      padding: 24px 32px;
      background-color: #fafafa;
      text-align: center;
      font-size: 12px;
      color: #a1a1aa;
    }}
  </style>
</head>
<body>
  <div style="display:none;font-size:1px;color:#f4f4f5;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preheader}
  </div>
  <div class="wrapper">
    <div class="container">
      <div class="header">
        <span class="brand">✳ InsightAPI AI</span>
      </div>
      <div class="content">
        {content_html}
      </div>
      <div class="footer">
        <p style="margin:0 0 6px 0;">© 2026 {settings.APP_NAME}. All rights reserved.</p>
        <p style="margin:0;">Autonomous Web API Intelligence & Endpoint Discovery Platform.</p>
      </div>
    </div>
  </div>
</body>
</html>"""

    @classmethod
    async def send_verification_email(cls, to_email: str, token: str) -> None:
        """Send a standard professional HTML email verification link."""
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        
        logger.info(f"============================================================")
        logger.info(f"[EMAIL DISPATCH] Verification email sent to: {to_email}")
        logger.info(f"[VERIFY LINK] {verify_url}")
        logger.info(f"============================================================")

        subject = f"Verify your email address — {settings.APP_NAME}"
        preheader = "Please confirm your email address to activate your InsightAPI AI account."

        text_content = (
            f"Welcome to {settings.APP_NAME}!\n\n"
            f"Please verify your email address by opening the following URL in your browser:\n"
            f"{verify_url}\n\n"
            f"If you did not create an account, please ignore this email."
        )

        html_body = f"""
          <h1 class="title">Verify your email address</h1>
          <p class="paragraph">
            Welcome to <strong>{settings.APP_NAME}</strong>! Thank you for signing up. Please click the button below to verify your email address and activate your developer account:
          </p>
          <div class="btn-container">
            <a href="{verify_url}" class="btn" target="_blank">Verify Email Address &rarr;</a>
          </div>
          <p class="paragraph" style="font-size: 13px; color: #71717a;">
            This verification link will remain active for 24 hours. If you did not create an account on {settings.APP_NAME}, no action is required.
          </p>
          <div class="fallback">
            If the button above does not work, copy and paste this URL into your browser:
            <span class="fallback-url">{verify_url}</span>
          </div>
        """

        full_html = cls._build_html_template(subject, preheader, html_body)
        cls._send_smtp_email(to_email, subject, text_content, full_html)

    @classmethod
    async def send_password_reset_email(cls, to_email: str, token: str) -> None:
        """Send a standard professional HTML password reset link."""
        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        
        logger.info(f"============================================================")
        logger.info(f"[EMAIL DISPATCH] Password reset email sent to: {to_email}")
        logger.info(f"[RESET LINK] {reset_url}")
        logger.info(f"============================================================")

        subject = f"Reset your password — {settings.APP_NAME}"
        preheader = "Use this link to safely reset your InsightAPI AI account password."

        text_content = (
            f"Hello,\n\n"
            f"We received a request to reset your password for {settings.APP_NAME}.\n\n"
            f"Click or open the link below to set a new password:\n"
            f"{reset_url}\n\n"
            f"If you did not request a password reset, you can safely ignore this email."
        )

        html_body = f"""
          <h1 class="title">Reset your password</h1>
          <p class="paragraph">
            We received a request to reset the password for your <strong>{settings.APP_NAME}</strong> account ({to_email}). Click the button below to set a new password:
          </p>
          <div class="btn-container">
            <a href="{reset_url}" class="btn" target="_blank">Reset Password &rarr;</a>
          </div>
          <p class="paragraph" style="font-size: 13px; color: #71717a;">
            For security reasons, this password reset link will expire in 1 hour. If you did not request a password reset, your account is secure and you can safely ignore this message.
          </p>
          <div class="fallback">
            If the button above does not work, copy and paste this URL into your browser:
            <span class="fallback-url">{reset_url}</span>
          </div>
        """

        full_html = cls._build_html_template(subject, preheader, html_body)
        cls._send_smtp_email(to_email, subject, text_content, full_html)
