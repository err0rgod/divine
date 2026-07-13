import os
import glob
import re

# We will collect all hardcoded keys and replace them in the files.
env_vars = {}

# Pre-fill from what we know or can easily scrape
env_vars["FIRECRAWL_API_KEY"] = "fc-0c8ab81418d04c60bb300901d9d17596"
env_vars["BLUESMINDS_API_KEY"] = "sk-usV6QNNxcuD10CozWceYo8xA2ZceCrzzrgLhvJpHg29zR23z"

# We will replace these specific lines in all python files
key_patterns = [
    (r'API_KEY\s*=\s*[\"\'](.*?)[\"\']', 'API_KEY'),
    (r'api_key\s*=\s*[\"\'](.*?)[\"\']', 'API_KEY'),
    (r'ACCOUNT_ID\s*=\s*[\"\']([a-f0-9]{32})[\"\']', 'CLOUDFLARE_ACCOUNT_ID')
]

for py_file in glob.glob('*.py'):
    if py_file == 'extract_env.py':
        continue
        
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    name = py_file.split('.')[0].upper()
    env_key_name = f"{name}_API_KEY"

    # Find API_KEY
    api_key_match = re.search(r'API_KEY\s*=\s*[\"\'](.*?)[\"\']', content)
    if api_key_match:
        key_val = api_key_match.group(1)
        if len(key_val) > 10 and "os.environ" not in key_val:
            env_vars[env_key_name] = key_val
            content = re.sub(
                r'API_KEY\s*=\s*[\"\'].*?[\"\']',
                f'API_KEY = os.environ.get("{env_key_name}")',
                content
            )
            modified = True

    # Find ACCOUNT_ID
    account_id_match = re.search(r'ACCOUNT_ID\s*=\s*[\"\']([a-f0-9]{32})[\"\']', content)
    if account_id_match:
        acc_val = account_id_match.group(1)
        env_vars['CLOUDFLARE_ACCOUNT_ID'] = acc_val
        content = re.sub(
            r'ACCOUNT_ID\s*=\s*[\"\'].*?[\"\']',
            f'ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")',
            content
        )
        modified = True

    # Check proxy.py specific keys
    if py_file == 'proxy.py':
        # Find OpenRouter key in proxy.py if hardcoded
        pass

    if modified:
        # ensure 'import os' is at the top
        if 'import os' not in content:
            content = "import os\nfrom dotenv import load_dotenv\nload_dotenv()\n\n" + content
        elif 'from dotenv import load_dotenv' not in content:
            content = content.replace("import os", "import os\nfrom dotenv import load_dotenv\nload_dotenv()")
            
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {py_file} to use environment variables.")

# Also extract from working.txt just in case
with open('working.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if '=' in line:
            parts = line.split('=')
            key_name = parts[0].strip().upper().replace(' ', '_') + '_API_KEY'
            val = parts[1].split()[0].strip()
            if len(val) > 10 and key_name not in env_vars.values():
                env_vars[key_name] = val

# Write .env
with open('.env', 'w', encoding='utf-8') as f:
    for k, v in env_vars.items():
        f.write(f'{k}={v}\n')

print(f"Created .env file with {len(env_vars)} keys.")
