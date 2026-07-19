"""Keyboard-first Textual operations interface (not a chat UI)."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Label, TabbedContent, TabPane

PAGES = (
    ("dashboard", "Dashboard", "Server status, request totals, and active routes."),
    ("providers", "Providers", "Enable adapters and edit provider base URLs."),
    (
        "credentials",
        "Credentials",
        "Manage keyring and environment references; values stay hidden.",
    ),
    ("models", "Models", "Inspect discovered models and capability overrides."),
    ("aliases", "Aliases", "Configure explicit aliases such as coding, fast, and default."),
    ("routing", "Routing", "Edit deterministic routing policies and classifier settings."),
    ("fallbacks", "Fallbacks", "Order provider/model fallback chains."),
    ("agents", "CLI Agents", "Configure explicit Claude, Codex, and OpenCode profiles."),
    ("server", "Server", "Bind address, port, limits, and deadlines."),
    ("usage", "Usage", "Review metadata-only usage and latency statistics."),
    ("health", "Health", "Inspect provider health scores and circuit state."),
    ("diagnostics", "Diagnostics", "Run local configuration and dependency checks."),
    ("logs", "Redacted Logs", "View structured logs with centralized secret redaction."),
)


class DivineRouterTUI(App[None]):
    TITLE = "Divine Router"
    SUB_TITLE = "Local AI gateway operations"
    CSS = """
    Screen { background: $surface; }
    TabbedContent { height: 1fr; }
    VerticalScroll { padding: 2 3; }
    Label { width: 100%; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "Quit"),
        ("d", "switch_dashboard", "Dashboard"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="dashboard"):
            for page_id, title, description in PAGES:
                with TabPane(title, id=page_id):
                    with VerticalScroll():
                        yield Label(f"{title}\n\n{description}")
        yield Footer()

    def action_switch_dashboard(self) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = "dashboard"


def run_tui() -> None:
    DivineRouterTUI().run()
