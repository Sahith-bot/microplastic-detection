"""Vercel entry point: Vercel runs this file as a Python serverless function and serves the Flask `app`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401
