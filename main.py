import sys
import subprocess
import threading
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import questionary

console = Console()

def run_service(name, cmd, color):
    def target():
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        for line in process.stdout:
            console.print(f"[{color}][{name}][/] {line.strip()}")
            
    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t

def show_header():
    console.clear()
    header = Text("DIVINE ORCHESTRATOR", style="bold magenta", justify="center")
    sub = Text("Universal Proxy Gateway & Meta-Router", style="dim italic", justify="center")
    panel = Panel.fit(
        f"{header.plain}\n{sub.plain}",
        border_style="magenta",
        padding=(1, 5)
    )
    console.print(panel)
    print()

def start_services(start_web=True, start_proxy=True):
    show_header()
    if start_web:
        console.print("[green]►[/] Starting Web Dashboard on http://127.0.0.1:8000")
        run_service("WEB", "uvicorn frontend.app:app --host 0.0.0.0 --port 8000", "cyan")
        
    if start_proxy:
        import json
        active_proxy = "Mistral"
        try:
            with open("D:/divine/config/proxy_config.json", "r") as f:
                active_proxy = json.load(f).get("active", "Mistral")
        except:
            pass
            
        console.print(f"[green]►[/] Starting {active_proxy} Proxy on http://127.0.0.1:8001")
        if active_proxy == "AgentRouter":
            run_service("PROXY", "python proxy/agentrouter_proxy.py", "yellow")
        elif active_proxy == "ForgeAI":
            run_service("PROXY", "python proxy/forge_ai_proxy.py", "yellow")
        else:
            run_service("PROXY", "python proxy/mistral_proxy.py", "yellow")
        
    console.print("\n[dim]Services are running in the background. Press Ctrl+C to stop and exit.[/dim]\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold red]Shutting down services...[/bold red]")
        sys.exit(0)

def main():
    show_header()
    
    choice = questionary.select(
        "Select an action:",
        choices=[
            "Start All Services (Web Dashboard + Proxy Server)",
            "Start Web Dashboard Only",
            "Start Proxy Server Only",
            "App Integration Guide (Claude Code, Codex, etc.)",
            "System Information",
            "Exit"
        ],
        style=questionary.Style([
            ('qmark', 'fg:magenta bold'),
            ('question', 'bold'),
            ('selected', 'fg:cyan bold'),
            ('pointer', 'fg:cyan bold'),
        ])
    ).ask()

    if choice == "Start All Services (Web Dashboard + Proxy Server)":
        start_services(True, True)
    elif choice == "Start Web Dashboard Only":
        start_services(True, False)
    elif choice == "Start Proxy Server Only":
        start_services(False, True)
    elif choice == "App Integration Guide (Claude Code, Codex, etc.)":
        app_choice = questionary.select(
            "Which application do you want to route through Divine?",
            choices=["Claude Code", "Codex CLI", "Cursor"]
        ).ask()
        
        console.print("\n[bold cyan]=== Integration Instructions ===[/]\n")
        if app_choice == "Claude Code":
            console.print("Claude Code relies on Anthropic's API format. Divine will automatically translate this for you!")
            console.print("\n[bold]1. Add an alias in the Proxy Gateway Dashboard (Optional):[/]")
            console.print("   `claude-3-5-sonnet-20241022: Mistral, codestral-latest`")
            console.print("\n[bold]2. Run this in your terminal before launching Claude Code:[/]")
            console.print("   [dim]# Windows (PowerShell):[/]")
            console.print("   $env:ANTHROPIC_BASE_URL=\"http://127.0.0.1:8001/proxy/code\"")
            console.print("   $env:ANTHROPIC_API_KEY=\"sk-claudecode-123\"")
            console.print("\n   [dim]# Mac / Linux:[/]")
            console.print("   export ANTHROPIC_BASE_URL=\"http://127.0.0.1:8001/proxy/code\"")
            console.print("   export ANTHROPIC_API_KEY=\"sk-claudecode-123\"")
        
        elif app_choice == "Codex CLI":
            console.print("Codex CLI expects OpenAI's API. Divine routes this to your Coding Pool.")
            console.print("\n[bold]Run this in your terminal before launching Codex CLI:[/]")
            console.print("   [dim]# Windows (PowerShell):[/]")
            console.print("   $env:OPENAI_BASE_URL=\"http://127.0.0.1:8001/proxy/code/v1\"")
            console.print("   $env:OPENAI_API_KEY=\"sk-codex-123\"")
            console.print("\n   [dim]# Mac / Linux:[/]")
            console.print("   export OPENAI_BASE_URL=\"http://127.0.0.1:8001/proxy/code/v1\"")
            console.print("   export OPENAI_API_KEY=\"sk-codex-123\"")
            
        elif app_choice == "Cursor":
            console.print("You can add Divine as a custom OpenAI-compatible endpoint in Cursor's settings.")
            console.print("\n[bold]1. Open Cursor Settings -> Models[/]")
            console.print("[bold]2. Add Custom OpenAI Endpoint:[/]")
            console.print("   URL: http://127.0.0.1:8001/proxy/code/v1")
            console.print("   API Key: sk-cursor-123")
            console.print("[bold]3. Toggle 'Custom models' and type the model you want to alias.[/]")
            
        console.print("\n[dim]* Make sure you add these `sk-...` keys to your Proxy Gateway in the dashboard![/]")
        input("\nPress Enter to return to menu...")
        main()
    elif choice == "System Information":
        console.print(Panel(
            "[bold cyan]Divine Proxy Gateway v1.0[/]\n"
            "An OpenAI-compatible universal proxy gateway pooling advanced models.\n\n"
            "[bold]Ports:[/]\n"
            "Web Dashboard: 8000\n"
            "Proxy Server: 8001\n\n"
            "[bold]Proxy Endpoints:[/]\n"
            "General Chat: http://127.0.0.1:8001/proxy/chat/v1/chat/completions\n"
            "Coding CLI: http://127.0.0.1:8001/proxy/code/v1/chat/completions",
            title="System Info",
            border_style="cyan"
        ))
        input("\nPress Enter to return to menu...")
        main()
    else:
        console.print("[bold red]Exiting...[/bold red]")
        sys.exit(0)

if __name__ == "__main__":
    main()
