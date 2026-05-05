"""
Chess Coach Agent — Entry Point
Run: python main.py
"""
import os
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and add your API key.\n")
        sys.exit(1)

    # Generate teaching guide on first run
    if not os.path.exists("TEACHING_GUIDE.pdf"):
        from utils.pdf_generator import generate_teaching_guide
        print("First run detected — generating TEACHING_GUIDE.pdf...")
        generate_teaching_guide()

    from graph.pipeline import run_coaching_session
    run_coaching_session()


if __name__ == "__main__":
    main()
