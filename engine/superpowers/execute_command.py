import subprocess

WORKSPACE_DIR = "D:/divine/workspace"


def execute_command(cmd: str) -> str:
    try:
        # Run in workspace directory
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=WORKSPACE_DIR,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if not output.strip():
            output = "Command executed successfully with no output."
        return output[:4000]  # truncate very long outputs
    except Exception as e:
        return f"Command execution failed: {e!s}"
