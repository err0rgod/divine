import os

WORKSPACE_DIR = "D:/divine/workspace"


def create_file(path: str, content: str) -> str:
    # Resolve path
    if not os.path.isabs(path):
        path = os.path.join(WORKSPACE_DIR, path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file at {path}"
    except Exception as e:
        return f"Failed to create file: {e!s}"
