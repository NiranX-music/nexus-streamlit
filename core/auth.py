"""
core/auth.py - Authentication proxy mapping to generate_token
"""
from core.generate_token import send_otp, get_token

__all__ = ["send_otp", "get_token"]
