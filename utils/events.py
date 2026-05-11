"""
EventBus singleton — decouples agents from output mode.
CLI mode:  bus.debug() prints, bus.ask() uses input()
Web mode:  bus.debug() sends to WebSocket, bus.ask() blocks on input queue
"""
import queue
import threading
from typing import Optional


class EventBus:
    def __init__(self):
        self._mode = "cli"
        self._event_q: Optional[queue.Queue] = None
        self._input_q: Optional[queue.Queue] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_web(self, event_q: queue.Queue, input_q: queue.Queue):
        with self._lock:
            self._mode = "web"
            self._event_q = event_q
            self._input_q = input_q

    def setup_cli(self):
        with self._lock:
            self._mode = "cli"
            self._event_q = None
            self._input_q = None

    def is_web(self) -> bool:
        return self._mode == "web"

    # ------------------------------------------------------------------
    # Emit helpers
    # ------------------------------------------------------------------

    def _put(self, event: dict):
        with self._lock:
            q = self._event_q
        if q is not None:
            q.put(event)

    def debug(self, message: str):
        """Plain-English status line for the debug window."""
        if self.is_web():
            self._put({"type": "debug", "message": message})
        else:
            print(f"  {message}")

    def node_active(self, node: str):
        """Light up a node in the pipeline diagram."""
        if self.is_web():
            self._put({"type": "node", "node": node, "status": "active"})

    def node_complete(self, node: str):
        """Mark a node done."""
        if self.is_web():
            self._put({"type": "node", "node": node, "status": "complete"})

    def node_waiting(self, node: str):
        """Mark a node waiting for user input."""
        if self.is_web():
            self._put({"type": "node", "node": node, "status": "waiting"})

    def stream_chunk(self, agent: str, text: str):
        """Send a chunk of streaming LLM output."""
        if self.is_web():
            self._put({"type": "stream", "agent": agent, "text": text})
        else:
            print(text, end="", flush=True)

    def speak(self, text: str):
        """Tell the frontend to speak text via Web Speech API."""
        if self.is_web():
            self._put({"type": "speak", "text": text})

    def show_question(self, question_id: str, question: str, options: list = None):
        """Show a question in the UI (web) or print it (CLI)."""
        if self.is_web():
            self._put({
                "type": "question",
                "id": question_id,
                "question": question,
                "options": options or [],
            })
        else:
            from utils.character import coach_says
            coach_says(question, speak=True)
            if options:
                for opt in options:
                    print(f"    {opt}")

    def ask(self, question_id: str, question: str, options: list = None) -> str:
        """Show a question and block until the user answers."""
        self.show_question(question_id, question, options)
        if self.is_web():
            with self._lock:
                q = self._input_q
            return q.get() if q else ""
        else:
            return input("  > ").strip()

    def complete(self, md_path: str, pdf_path: str,
                 positions_pdf_path: Optional[str] = None):
        """Signal that the session is finished."""
        if self.is_web():
            payload = {"type": "complete", "md_path": md_path, "pdf_path": pdf_path}
            if positions_pdf_path:
                payload["positions_pdf_path"] = positions_pdf_path
            self._put(payload)

    def error(self, message: str):
        if self.is_web():
            self._put({"type": "error", "message": message})
        else:
            print(f"  ERROR: {message}")


# Singleton used by all agents and pipeline nodes
bus = EventBus()
