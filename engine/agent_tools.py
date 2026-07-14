import os
import subprocess
import json
import base64
import requests
import re
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_DIR = "D:/divine/workspace"
CONTEXT_DIR = "D:/divine/context"
MEMORY_FILE = os.path.join(CONTEXT_DIR, "memory.json")
UPLOADS_DIR = os.path.join(CONTEXT_DIR, "uploads")

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(CONTEXT_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Try importing specialized libraries, fallback gracefully
try:
    from exa_py import Exa
    EXA_API_KEY = os.environ.get("EXA_SEARCH_API_KEY", "")
    if not EXA_API_KEY:
        EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
    exa = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None
except ImportError:
    exa = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Default windows path
except ImportError:
    pytesseract = None
    Image = None

# Import superpowers from modular files
from .superpowers import (
    search_web,
    read_url,
    execute_command,
    create_file,
    save_memory
)
from .superpowers.save_memory import load_memory

def extract_file_content(filepath: str, is_multimodal_model: bool = False) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    
    # Text files
    if ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.csv']:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return "Failed to read text file."
            
    # PDF files
    elif ext == '.pdf':
        if fitz:
            try:
                text = ""
                doc = fitz.open(filepath)
                for page in doc:
                    text += page.get_text()
                # If it's a huge PDF, we should technically chunk it. 
                # For now, return up to a reasonable limit or let Cohere handle it if passed differently.
                return text[:20000] # limit to 20k chars for basic fallback
            except Exception as e:
                return f"Failed to extract PDF: {str(e)}"
        else:
            return "PyMuPDF not installed, cannot read PDF."
            
    # Image files
    elif ext in ['.png', '.jpg', '.jpeg', '.webp']:
        if is_multimodal_model:
            # Return a special marker that the orchestrator will catch to attach as base64
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"[IMAGE_BASE64:{ext}:{b64}]"
        else:
            # Fallback to OCR
            if pytesseract and Image:
                try:
                    img = Image.open(filepath)
                    text = pytesseract.image_to_string(img)
                    return f"OCR Extraction:\n{text}"
                except Exception as e:
                    return f"OCR Failed: {str(e)}"
            else:
                return "Multimodal not supported by model and pytesseract not installed."
                
    return "Unsupported file type."

def parse_and_execute_tags(response_text: str) -> Dict[str, Any]:
    """Scans for XML tags, executes them, and returns the results to append to context."""
    results = {}
    
    # 1. Web Search
    search_matches = re.finditer(r'<search_web>(.*?)</search_web>', response_text, re.DOTALL)
    for match in search_matches:
        query = match.group(1).strip()
        res = search_web(query)
        results[f"Web Search: {query}"] = res
        
    # 2. Command Execution
    cmd_matches = re.finditer(r'<execute_cmd>(.*?)</execute_cmd>', response_text, re.DOTALL)
    for match in cmd_matches:
        cmd = match.group(1).strip()
        res = execute_command(cmd)
        results[f"Command: {cmd}"] = res
        
    # 3. Read URL
    url_matches = re.finditer(r'<read_url>(.*?)</read_url>', response_text, re.DOTALL)
    for match in url_matches:
        url = match.group(1).strip()
        res = read_url(url)
        results[f"Read URL: {url}"] = res

    # 4. File Creation
    # Syntax: <create_file path="...">...</create_file>
    file_matches = re.finditer(r'<create_file\s+path=["\'](.*?)["\']>(.*?)</create_file>', response_text, re.DOTALL)
    for match in file_matches:
        path = match.group(1).strip()
        content = match.group(2).strip()
        res = create_file(path, content)
        results[f"File Created: {path}"] = res
        
    # 5. Read Local File
    read_file_matches = re.finditer(r'<read_file\s+path=["\'](.*?)["\']>.*?</read_file>', response_text, re.DOTALL)
    for match in read_file_matches:
        path = match.group(1).strip()
        res = extract_file_content(path)
        results[f"Read File: {path}"] = res
        
    # Also support <read_file path="..."> without inner content just in case the LLM writes it like <read_file path="..."/>
    read_file_self_closing = re.finditer(r'<read_file\s+path=["\'](.*?)["\']\s*/?>', response_text)
    for match in read_file_self_closing:
        path = match.group(1).strip()
        if f"Read File: {path}" not in results:
            res = extract_file_content(path)
            results[f"Read File: {path}"] = res
        
    # 4. Save Memory
    mem_matches = re.finditer(r'<save_memory>(.*?)</save_memory>', response_text, re.DOTALL)
    for match in mem_matches:
        fact = match.group(1).strip()
        res = save_memory(fact)
        results[f"Memory Saved"] = res
        
    return results
