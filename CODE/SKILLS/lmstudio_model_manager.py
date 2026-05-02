#!/usr/bin/env python3
"""
LM Studio Model Manager

Sync GGUF models from laptop to Raspberry Pi for local LLM inference.

Usage:
    python3 lmstudio_model_manager.py --list              # List local models
    python3 lmstudio_model_manager.py --remote LAPTOP_IP  # List models on laptop
    python3 lmstudio_model_manager.py --sync LAPTOP_IP    # Sync all models from laptop
    python3 lmstudio_model_manager.py --sync LAPTOP_IP --model "phi*"  # Sync specific model
    python3 lmstudio_model_manager.py --status            # Check LM Studio status
    python3 lmstudio_model_manager.py --recommend         # Recommend models for tasks
"""

import os
import sys
import json
import argparse
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Optional

# Paths
LOCAL_MODELS_DIR = Path.home() / ".lmstudio" / "models"
LMSTUDIO_API = "http://localhost:1234/v1/models"

# Recommended models for each task (small models for Pi, sorted by size)
RECOMMENDED_MODELS = {
    "tiny": {
        "model": "tinyllama-1.1b-chat",
        "gguf": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "file": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size": "0.7 GB",
        "speed": "~1s",
        "task": "Ultra-fast yes/no, simple extraction"
    },
    "smol": {
        "model": "smollm-1.7b-instruct",
        "gguf": "lmstudio-community/SmolLM-1.7B-Instruct-GGUF",
        "file": "SmolLM-1.7B-Instruct-Q4_K_M.gguf",
        "size": "1.0 GB",
        "speed": "~1-2s",
        "task": "Fast classification, edge-optimized"
    },
    "code": {
        "model": "qwen2.5-coder-1.5b-instruct",
        "gguf": "lmstudio-community/Qwen2.5-Coder-1.5B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf",
        "size": "1.0 GB",
        "speed": "~2s",
        "task": "Code fixes, error analysis"
    },
    "gemma": {
        "model": "gemma-2-2b-instruct",
        "gguf": "lmstudio-community/gemma-2-2b-it-GGUF",
        "file": "gemma-2-2b-it-Q4_K_M.gguf",
        "size": "1.5 GB",
        "speed": "~2-3s",
        "task": "Smart classification, multilingual, reasoning"
    },
    "general": {
        "model": "llama-3.2-3b-instruct",
        "gguf": "lmstudio-community/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size": "1.9 GB",
        "speed": "~4s",
        "task": "General conversation, summarization"
    },
    "reasoning": {
        "model": "phi-3.5-mini-instruct",
        "gguf": "lmstudio-community/Phi-3.5-mini-instruct-GGUF",
        "file": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "size": "2.2 GB",
        "speed": "~4-5s",
        "task": "Complex reasoning, long context"
    },
    "embed": {
        "model": "nomic-embed-text-v1.5",
        "gguf": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "file": "nomic-embed-text-v1.5.Q4_K_M.gguf",
        "size": "0.1 GB",
        "speed": "instant",
        "task": "Text embeddings, semantic search"
    }
}


def get_local_models() -> List[Dict]:
    """Get list of locally installed models."""
    models = []
    if LOCAL_MODELS_DIR.exists():
        for gguf in LOCAL_MODELS_DIR.rglob("*.gguf"):
            size_mb = gguf.stat().st_size / (1024 * 1024)
            models.append({
                "name": gguf.stem,
                "path": str(gguf),
                "size_mb": round(size_mb, 1),
                "size_gb": round(size_mb / 1024, 2)
            })
    return models


def get_loaded_models() -> List[str]:
    """Get models currently loaded in LM Studio."""
    try:
        r = requests.get(LMSTUDIO_API, timeout=2)
        if r.status_code == 200:
            return [m['id'] for m in r.json().get('data', [])]
    except:
        pass
    return []


def get_remote_models(laptop_ip: str, user: str = "tudor") -> List[Dict]:
    """Get models from Windows laptop via SSH."""
    models = []

    # Try to list models on laptop
    cmd = f'ssh -o ConnectTimeout=5 {user}@{laptop_ip} "dir /s /b \\"%USERPROFILE%\\.lmstudio\\models\\*.gguf\\" 2>nul"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    name = Path(line).stem
                    models.append({
                        "name": name,
                        "path": line.strip(),
                        "remote": True
                    })
    except Exception as e:
        print(f"Error connecting to laptop: {e}")

    return models


def sync_models(laptop_ip: str, pattern: str = None, user: str = "tudor"):
    """Sync models from laptop to local LM Studio."""
    print(f"Syncing from {user}@{laptop_ip}...")

    # Ensure local directory exists
    LOCAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Build rsync command
    src = f"{user}@{laptop_ip}:.lmstudio/models/"
    dst = str(LOCAL_MODELS_DIR) + "/"

    cmd = ["rsync", "-avz", "--progress"]
    if pattern:
        cmd.extend(["--include", f"*{pattern}*", "--exclude", "*"])
    cmd.extend([src, dst])

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)


def check_status():
    """Check LM Studio status and model availability."""
    print("=== LM Studio Status ===")
    print(f"API: {LMSTUDIO_API}")

    loaded = get_loaded_models()
    if loaded:
        print(f"Status: Running")
        print(f"Loaded models: {len(loaded)}")
        for m in loaded:
            print(f"  - {m}")
    else:
        print("Status: Not running or no models loaded")

    print(f"\n=== Local Models ===")
    print(f"Directory: {LOCAL_MODELS_DIR}")
    local = get_local_models()
    total_gb = sum(m['size_gb'] for m in local)
    print(f"Models: {len(local)} ({total_gb:.1f} GB)")
    for m in local:
        loaded_mark = "*" if m['name'] in ' '.join(loaded) else " "
        print(f"  {loaded_mark} {m['name']} ({m['size_gb']:.1f} GB)")


def show_recommendations():
    """Show recommended models for each task."""
    print("=== Recommended Models for Raspberry Pi ===")
    print("(Sorted by size, smallest first)\n")

    local = [m['name'].lower() for m in get_local_models()]

    for task, info in RECOMMENDED_MODELS.items():
        installed = "INSTALLED" if any(info['model'].lower() in m for m in local) else "not installed"
        status_icon = "✓" if "INSTALLED" in installed else " "
        print(f"[{status_icon}] [{task.upper()}] {info['model']}")
        print(f"    Size: {info['size']} | Speed: {info.get('speed', 'N/A')}")
        print(f"    Task: {info['task']}")
        print(f"    GGUF: {info['gguf']}")
        print()

    print("=" * 50)
    print("PRIORITY DOWNLOADS (for Pi):")
    print("  1. smollm-1.7b-instruct  (1.0GB) - Fast classification")
    print("  2. gemma-2-2b-instruct   (1.5GB) - Smart + multilingual")
    print()
    print("To download in LM Studio UI:")
    print("  1. Search for model name (e.g., 'smollm 1.7b')")
    print("  2. Download Q4_K_M quantization")
    print("  3. Sync: python3 lmstudio_model_manager.py --sync LAPTOP_IP")


def main():
    parser = argparse.ArgumentParser(description='LM Studio Model Manager')
    parser.add_argument('--list', '-l', action='store_true', help='List local models')
    parser.add_argument('--remote', '-r', type=str, help='List models on laptop (IP)')
    parser.add_argument('--sync', '-s', type=str, help='Sync models from laptop (IP)')
    parser.add_argument('--model', '-m', type=str, help='Model pattern for sync')
    parser.add_argument('--status', action='store_true', help='Check LM Studio status')
    parser.add_argument('--recommend', action='store_true', help='Show recommended models')
    parser.add_argument('--user', '-u', type=str, default='tudor', help='SSH user')

    args = parser.parse_args()

    if args.status:
        check_status()

    elif args.list:
        models = get_local_models()
        print(f"Local models in {LOCAL_MODELS_DIR}:")
        for m in models:
            print(f"  {m['name']} ({m['size_gb']:.1f} GB)")

    elif args.remote:
        models = get_remote_models(args.remote, args.user)
        print(f"Models on {args.remote}:")
        for m in models:
            print(f"  {m['name']}")

    elif args.sync:
        sync_models(args.sync, args.model, args.user)
        print("\nDone. Restart LM Studio to load new models.")

    elif args.recommend:
        show_recommendations()

    else:
        check_status()


if __name__ == "__main__":
    main()
