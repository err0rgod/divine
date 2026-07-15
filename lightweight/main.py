import json
import os
import subprocess
import sys
import threading
import time

import questionary
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

processes = []


def sync_env_to_keys():
    # Load environment variables from .env
    load_dotenv("D:/divine/.env")

    # Map .env keys to the JSON provider names
    env_map = {
        "MISTRAL_API_KEY": "Mistral",
        "GROQ_API_KEY": "Groq",
        "CEREBRAS_API_KEY": "Cerebras",
        "NVIDIA_NIM_API_KEY": "NVIDIA",
        "BAZAARLINK_API_KEY": "Bazaarlink",
        "COHERE_API_KEY": "Cohere",
        "BLUESMIND_API_KEY": "Bluesmind",
        "AGENTROUTER_API_KEY": "AgentRouter",
        "FORGEAI_API_KEY": "ForgeAI",
        "DEEPSEEK_API_KEY": "DeepSeek",
    }

    config_path = "D:/divine/config/proxy_keys.json"

    try:
        with open(config_path) as f:
            data = json.load(f)
    except Exception:
        data = {"keys": {}}

    updated = False
    if "keys" not in data:
        data["keys"] = {}

    for env_key, provider_name in env_map.items():
        val = os.environ.get(env_key)
        if val and val.strip():
            # Only sync if the provider array is missing or doesn't have this key
            provider_keys = data["keys"].get(provider_name, [])
            if val.strip() not in provider_keys:
                # If they only had the default/empty string, wipe it and add the new one
                if (
                    len(provider_keys) == 1
                    and provider_keys[0].startswith("sk-") == False
                    and provider_keys[0] == ""
                ):
                    data["keys"][provider_name] = [val.strip()]
                else:
                    data["keys"][provider_name] = [val.strip()] + [
                        k for k in provider_keys if k != val.strip()
                    ]
                updated = True

    if updated:
        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)
        # console.print("[dim]✓ Automatically synced new API keys from .env to proxy_keys.json[/dim]")


def run_service(name, cmd_list, color):
    def target():
        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
        )
        processes.append(process)
        for line in process.stdout:
            console.print(f"[{color}][{name}][/] {line.strip()}")

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t


def show_header():
    console.clear()
    header = Text("DIVINE ORCHESTRATOR", style="bold magenta", justify="center")
    sub = Text(
        "Universal Proxy Gateway & Meta-Router", style="dim italic", justify="center"
    )
    panel = Panel.fit(
        f"{header.plain}\n{sub.plain}", border_style="magenta", padding=(1, 5)
    )
    console.print(panel)
    print()


def start_services(start_web=True, start_proxy=True):
    show_header()
    if start_web:
        console.print("[green]►[/] Starting Web Dashboard on http://127.0.0.1:8001")
        run_service(
            "WEB",
            ["uvicorn", "frontend.app:app", "--host", "0.0.0.0", "--port", "8001"],
            "cyan",
        )

    if start_proxy:
        import json

        active_proxy = "Mistral"
        try:
            with open("D:/divine/config/proxy_config.json") as f:
                active_proxy = json.load(f).get("active", "Mistral")
        except Exception:
            pass

        console.print(
            f"[green]►[/] Starting {active_proxy} Proxy on http://127.0.0.1:8000"
        )
        proxy_map = {
            "AgentRouter": "agentrouter_proxy.py",
            "ForgeAI": "forge_ai_proxy.py",
            "Mistral": "mistral_proxy.py",
            "Groq": "groq_proxy.py",
            "NVIDIA": "nvidia_proxy.py",
            "Bluesmind": "bluesmind_proxy.py",
            "Cerebras": "cerebras_proxy.py",
            "DeepSeek": "deepseek_proxy.py",
        }
        script = proxy_map.get(active_proxy, "mistral_proxy.py")
        run_service("PROXY", ["python", f"proxy/{script}"], "yellow")

    console.print(
        "\n[dim]Services are running in the background. Press Ctrl+C to stop and exit.[/dim]\n"
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold red]Shutting down services...[/bold red]")
        for p in processes:
            p.kill()
        sys.exit(0)


def main():
    sync_env_to_keys()
    show_header()

    choice = questionary.select(
        "Select an action:",
        choices=[
            "Start All Services (Web Dashboard + Proxy Server)",
            "Start Web Dashboard Only",
            "Start Proxy Server Only",
            "Switch Target Model (Dynamically)",
            "App Integration Guide (Claude Code, Codex, etc.)",
            "System Information",
            "Exit",
        ],
        style=questionary.Style(
            [
                ("qmark", "fg:magenta bold"),
                ("question", "bold"),
                ("selected", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
            ]
        ),
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
            choices=["Claude Code", "Codex CLI", "Cursor"],
        ).ask()

        console.print("\n[bold cyan]=== Integration Instructions ===[/]\n")
        if app_choice == "Claude Code":
            console.print(
                "Claude Code relies on Anthropic's API format. Divine will automatically translate this for you!"
            )
            console.print(
                "\n[bold]1. Add an alias in the Proxy Gateway Dashboard (Optional):[/]"
            )
            console.print("   `claude-3-5-sonnet-20241022: Mistral, codestral-latest`")
            console.print(
                "\n[bold]2. Run this in your terminal before launching Claude Code:[/]"
            )
            console.print("   [dim]# Windows (PowerShell):[/]")
            console.print('   $env:ANTHROPIC_BASE_URL="http://127.0.0.1:8000"')
            console.print('   $env:ANTHROPIC_API_KEY="sk-claudecode-123"')
            console.print("\n   [dim]# Mac / Linux:[/]")
            console.print('   export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"')
            console.print('   export ANTHROPIC_API_KEY="sk-claudecode-123"')

        elif app_choice == "Codex CLI":
            console.print(
                "Codex CLI expects OpenAI's API. Divine routes this to your Coding Pool."
            )
            console.print(
                "\n[bold]Run this in your terminal before launching Codex CLI:[/]"
            )
            console.print("   [dim]# Windows (PowerShell):[/]")
            console.print('   $env:OPENAI_BASE_URL="http://127.0.0.1:8000/v1"')
            console.print('   $env:OPENAI_API_KEY="sk-codex-123"')
            console.print("\n   [dim]# Mac / Linux:[/]")
            console.print('   export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"')
            console.print('   export OPENAI_API_KEY="sk-codex-123"')

        elif app_choice == "Cursor":
            console.print(
                "You can add Divine as a custom OpenAI-compatible endpoint in Cursor's settings."
            )
            console.print("\n[bold]1. Open Cursor Settings -> Models[/]")
            console.print("[bold]2. Add Custom OpenAI Endpoint:[/]")
            console.print("   URL: http://127.0.0.1:8000/v1")
            console.print("   API Key: sk-cursor-123")
            console.print(
                "[bold]3. Toggle 'Custom models' and type the model you want to alias.[/]"
            )

        console.print(
            "\n[dim]* Make sure you add these `sk-...` keys to your Proxy Gateway in the dashboard![/]"
        )
        input("\nPress Enter to return to menu...")
        main()
    elif choice == "Switch Target Model (Dynamically)":
        import json

        try:
            with open("D:/divine/config/models.json") as f:
                models_data = json.load(f)
        except Exception:
            models_data = {}

        provider_choices = list(models_data.keys())
        provider_choices = [
            p
            for p in provider_choices
            if p not in ["Auto-Select", "Exa", "Firecrawl", "Jina"]
        ]

        if not provider_choices:
            provider_choices = [
                "Mistral",
                "AgentRouter",
                "ForgeAI",
                "Groq",
                "NVIDIA",
                "Bluesmind",
                "Cerebras",
                "DeepSeek",
            ]

        provider = questionary.select(
            "Select the Provider for the proxy to use:", choices=provider_choices
        ).ask()
        if not provider:
            main()
            return

        models_for_provider = models_data.get(provider, [])
        if not models_for_provider:
            models_for_provider = ["default-model"]

        target_model = questionary.select(
            f"Select the Model for {provider}:", choices=models_for_provider
        ).ask()

        if provider and target_model:
            proxy_config = {}
            try:
                with open("D:/divine/config/proxy_config.json") as f:
                    proxy_config = json.load(f)
            except Exception:
                pass

            proxy_config["target_model"] = target_model
            # Automatically update the active proxy if the model belongs to a standalone provider
            if provider in [
                "Mistral",
                "AgentRouter",
                "ForgeAI",
                "Groq",
                "NVIDIA",
                "Bluesmind",
                "Cerebras",
                "DeepSeek",
            ]:
                proxy_config["active"] = provider

            with open("D:/divine/config/proxy_config.json", "w") as f:
                json.dump(proxy_config, f, indent=4)

            console.print(
                f"\n[bold green]Success![/] Target model updated to [cyan]{target_model}[/] (Proxy: {provider})."
            )
            console.print(
                "[dim]The running proxy will automatically use this model on the very next request! (If you changed providers, you may need to restart the proxy).[/dim]"
            )

        input("\nPress Enter to return to menu...")
        main()
    elif choice == "System Information":
        console.print(
            Panel(
                "[bold cyan]Divine Proxy Gateway v1.0[/]\n"
                "An OpenAI-compatible universal proxy gateway pooling advanced models.\n\n"
                "[bold]Ports:[/]\n"
                "Web Dashboard: 8001\n"
                "Proxy Server: 8000\n\n"
                "[bold]Proxy Endpoints:[/]\n"
                "General Chat: http://127.0.0.1:8000/v1/chat/completions\n"
                "Coding CLI: http://127.0.0.1:8000/v1/messages",
                title="System Info",
                border_style="cyan",
            )
        )
        input("\nPress Enter to return to menu...")
        main()
    else:
        console.print("[bold red]Exiting...[/bold red]")
        sys.exit(0)


if __name__ == "__main__":
    main()
