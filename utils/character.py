"""
Coach King — the friendly AI coach character.
Handles the terminal persona and voice output.
Voice uses macOS built-in 'say' command (no API key needed).
"""
import subprocess
import sys
import threading
import os

COACH_NAME = "Coach King"

COACH_ART = r"""
  ╔══════════════════════════════╗
  ║     ♟  COACH  KING  ♟      ║
  ╠══════════════════════════════╣
  ║                              ║
  ║          ( ◕  ◕ )           ║
  ║           \  ∪  /            ║
  ║         ♚ ♛ ♜ ♝ ♞          ║
  ║                              ║
  ║   "Every pawn can be king."  ║
  ╚══════════════════════════════╝
"""

COACH_PERSONALITY = """\
You are Coach King, a warm, encouraging, and deeply knowledgeable chess coach.
You genuinely care about your students and celebrate every small improvement.
Your tone is friendly and conversational — like a mentor, not a lecturer.
You use chess metaphors naturally ("stay patient, like a good endgame",
"calculate before you commit — in chess and in training").
You are never condescending. When pointing out mistakes, you frame them as
opportunities. You're enthusiastic without being fake. Keep messages concise
and human — avoid bullet-point lists in your spoken words.
Always end lessons with a motivating send-off line."""


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def show_coach():
    """Print the Coach King ASCII art."""
    print(COACH_ART)


def coach_says(message: str, speak: bool = True) -> None:
    """Print a Coach King message and optionally speak it aloud."""
    print(f"\n  ♟ Coach King: {message}\n")
    if speak and _voice_enabled():
        _speak_async(message)


def coach_asks(question: str, speak: bool = True) -> str:
    """Speak a question and return the user's input."""
    coach_says(question, speak=speak)
    return input("  > ").strip()


# ---------------------------------------------------------------------------
# Voice engine
# ---------------------------------------------------------------------------

# macOS voices — change to your preferred one:
#   'Daniel'  — British male, calm and clear
#   'Samantha' — American female
#   'Alex'    — American male
MAC_VOICE = "Daniel"
SPEECH_RATE = 175  # words per minute


def _voice_enabled() -> bool:
    return os.getenv("COACH_VOICE", "1") != "0"


def _speak_async(text: str) -> None:
    """Fire-and-forget voice in a daemon thread so it never blocks the program."""
    def _run():
        try:
            if sys.platform == "darwin":
                subprocess.run(
                    ["say", "-v", MAC_VOICE, "-r", str(SPEECH_RATE), text],
                    capture_output=True,
                )
            else:
                # Fallback for non-Mac: try pyttsx3 if installed
                import pyttsx3  # noqa: F401
                engine = pyttsx3.init()
                engine.setProperty("rate", SPEECH_RATE)
                engine.say(text)
                engine.runAndWait()
        except Exception:
            pass  # Voice is a nice-to-have; never crash over it

    threading.Thread(target=_run, daemon=True).start()


def speak_section(title: str, body: str) -> None:
    """Read a titled section aloud (summary only — first 2 sentences)."""
    sentences = body.replace("\n", " ").split(". ")
    preview = ". ".join(sentences[:2]).strip()
    if not preview.endswith("."):
        preview += "."
    _speak_async(f"{title}. {preview}")
