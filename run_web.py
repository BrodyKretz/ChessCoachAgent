"""
Web UI entry point. Run: python run_web.py
Then open http://localhost:8000 in your browser.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Generate teaching guide on first run
if not Path("TEACHING_GUIDE.pdf").exists():
    from utils.pdf_generator import generate_teaching_guide
    print("Generating TEACHING_GUIDE.pdf...")
    generate_teaching_guide()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("\nERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.\n")
    sys.exit(1)

print("\n  ♟ Chess Coach Agent — Web UI")
print("  Open http://localhost:8000 in your browser\n")

from api.server import start
start()
