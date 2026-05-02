#!/usr/bin/env python3
"""
LLM Triage - Local LLM for simple classification tasks via LM Studio.
Falls back to rules-based if LM Studio unavailable.
(Formerly ollama_triage.py - migrated 2026-02-20)
"""
import sys
import json
import re
import requests

LMSTUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
LMSTUDIO_MODEL = "spam-classifier-3b-v1"

def lmstudio_available():
    """Check if LM Studio is running."""
    try:
        r = requests.get("http://127.0.0.1:1234/v1/models", timeout=3)
        return r.status_code == 200
    except:
        return False

def query_lmstudio(prompt, model=LMSTUDIO_MODEL):
    """Send query to LM Studio."""
    try:
        r = requests.post(LMSTUDIO_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 300,
            "stream": False
        }, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"ERROR: {r.status_code}"
    except Exception as e:
        return f"ERROR: {e}"

def classify_spam(text):
    """Classify if text is spam. Uses rules first, LLM as backup."""
    text_lower = text.lower()
    spam_indicators = [
        "unsubscribe", "click here", "limited time", "act now",
        "free money", "winner", "lottery", "prince", "inheritance",
        "viagra", "casino", "crypto", "invest now"
    ]
    spam_score = sum(1 for ind in spam_indicators if ind in text_lower)
    if spam_score >= 2:
        return {"classification": "SPAM", "confidence": "HIGH", "method": "rules", "score": spam_score}
    elif spam_score == 1:
        if lmstudio_available():
            prompt = f"Is this email spam? Reply only YES or NO.\n\n{text[:500]}"
            response = query_lmstudio(prompt)
            is_spam = "yes" in response.lower()
            return {"classification": "SPAM" if is_spam else "NOT_SPAM", "confidence": "MEDIUM", "method": "lmstudio"}
        return {"classification": "UNCERTAIN", "confidence": "LOW", "method": "rules", "score": spam_score}
    return {"classification": "NOT_SPAM", "confidence": "HIGH", "method": "rules", "score": spam_score}

def parse_error(error_text):
    """Extract key info from error message."""
    patterns = {
        "file": r"File \"([^\"]+)\"",
        "line": r"line (\d+)",
        "error_type": r"(\w+Error):",
        "message": r"Error: (.+)$"
    }
    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, error_text, re.MULTILINE)
        if match:
            result[key] = match.group(1)
    if lmstudio_available() and len(error_text) > 200:
        prompt = f"Summarize this error in one sentence:\n\n{error_text[:1000]}"
        result["summary"] = query_lmstudio(prompt)
    return result

def summarize_log(log_text, max_lines=50):
    """Summarize a log file."""
    lines = log_text.strip().split("\n")
    important = []
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["error", "fail", "exception", "warn", "critical"]):
            important.append(line)
    summary = {
        "total_lines": len(lines),
        "important_lines": len(important),
        "errors": [l for l in important if "error" in l.lower()][:5],
        "warnings": [l for l in important if "warn" in l.lower()][:5]
    }
    if lmstudio_available() and len(lines) > 100:
        prompt = f"Summarize these log entries in 2-3 bullet points:\n\n{chr(10).join(important[:20])}"
        summary["ai_summary"] = query_lmstudio(prompt)
    return summary

def categorize_email_intent(subject, body_preview):
    """Categorize email intent for routing."""
    text = f"{subject} {body_preview}".lower()
    categories = {
        "unsubscribe": ["unsubscribe", "remove me", "stop sending", "opt out"],
        "bounce": ["delivery failed", "undeliverable", "mailbox full", "does not exist"],
        "auto_reply": ["out of office", "automatic reply", "away from", "vacation"],
        "inquiry": ["interested", "more information", "question about", "pricing"],
        "complaint": ["spam", "stop", "harassment", "illegal", "report"]
    }
    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return {"category": category, "method": "rules"}
    if lmstudio_available():
        prompt = f"Categorize this email as one of: inquiry, complaint, spam, other. Reply with just the category.\n\nSubject: {subject}\n{body_preview[:200]}"
        response = query_lmstudio(prompt).lower()
        for cat in ["inquiry", "complaint", "spam", "other"]:
            if cat in response:
                return {"category": cat, "method": "lmstudio"}
    return {"category": "other", "method": "rules"}

def main():
    if len(sys.argv) < 2:
        print("Usage: llm_triage.py <command> [args]")
        print("\nCommands:")
        print("  status              - Check LM Studio availability")
        print("  spam <text>         - Classify spam")
        print("  error <text>        - Parse error message")
        print("  log <file>          - Summarize log file")
        print("  email <subj> <body> - Categorize email intent")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "status":
        available = lmstudio_available()
        print(f"LM Studio: {'available' if available else 'not available'}")
        if available:
            print(f"Model: {LMSTUDIO_MODEL}")
        sys.exit(0 if available else 1)
    elif cmd == "spam":
        text = " ".join(sys.argv[2:])
        result = classify_spam(text)
        print(json.dumps(result, indent=2))
    elif cmd == "error":
        text = " ".join(sys.argv[2:])
        result = parse_error(text)
        print(json.dumps(result, indent=2))
    elif cmd == "log":
        with open(sys.argv[2], "r") as f:
            text = f.read()
        result = summarize_log(text)
        print(json.dumps(result, indent=2))
    elif cmd == "email":
        subject = sys.argv[2] if len(sys.argv) > 2 else ""
        body = sys.argv[3] if len(sys.argv) > 3 else ""
        result = categorize_email_intent(subject, body)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
