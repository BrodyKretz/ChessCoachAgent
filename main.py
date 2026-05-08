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

    from graph.pipeline import run_coaching_session
    run_coaching_session()


if __name__ == "__main__":
    main()
