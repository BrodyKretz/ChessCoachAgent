"""
Web UI entry point. Run: python run_web.py
Then open http://localhost:8000 in your browser.
"""
import os
import sys
from dotenv import load_dotenv


load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("\nERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.\n")
    sys.exit(1)

print("\n  ♟ Chess Coach Agent — Web UI")
print("  Open http://localhost:8000 in your browser\n")

from api.server import start
start()
