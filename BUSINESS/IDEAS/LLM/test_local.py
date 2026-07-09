#!/usr/bin/env python3
"""
Local test: classify sample emails + generate draft responses via LM Studio.
No PostgreSQL needed — uses training_pairs.jsonl directly.
"""

import json
import pickle
import time
from pathlib import Path
from openai import OpenAI

from response_templates import get_system_prompt, get_fallback

BASE_DIR = Path(__file__).parent
MODEL_FILE = BASE_DIR / "models" / "email_classifier.pkl"
TRAINING_FILE = BASE_DIR / "training_pairs.jsonl"

# --
def load_classifier():
    with open(MODEL_FILE, "rb") as f:
        data = pickle.load(f)
    return data

def classify(model_data, text):
    processed = text[:2000]
    results = {}
    for name in ("intent", "priority", "folder"):
        pipeline = model_data.get(name)
        if not pipeline:
            continue
        pred = pipeline.predict([processed])[0]
        prob = max(pipeline.predict_proba([processed])[0])
        results[name] = {"label": pred, "confidence": round(prob, 3)}
    return results

def draft_response(client, subject, body, intent, lang):
    system = get_system_prompt(lang)
    user_msg = f"Reply to this email. Intent: {intent}\n\nSubject: {subject}\n\n{body[:1500]}"
    try:
        resp = client.chat.completions.create(
            model="google/gemma-3-4b",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        import re
        text = resp.choices[0].message.content.strip()
        if "<think>" in text:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text
    except Exception as e:
        print(f"  LLM error: {e}")
        return get_fallback(intent, lang)

# --
def main():
    print("Loading classifier...")
    model_data = load_classifier()
    print(f"Model trained: {model_data.get('metadata', {}).get('trained_at', '?')}")

    print("Connecting to LM Studio...")
    api_key = Path(Path.home() / ".lmstudio/.internal/lms-key-2").read_text().strip()
    client = OpenAI(base_url="http://localhost:1234/v1", api_key=api_key)

    # Pick sample emails that need responses (inquiry, application, campaign_reply)
    target_intents = {"inquiry", "application", "campaign_reply"}
    samples = []
    with open(TRAINING_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            out = json.loads(rec["output"])
            if out.get("intent") in target_intents:
                samples.append((rec["input"], out))
            if len(samples) >= 5:
                break

    if not samples:
        print("No inquiry/application/campaign_reply emails found in training data")
        return

    print(f"\nTesting {len(samples)} emails:\n")

    for i, (text, label) in enumerate(samples, 1):
        # Extract subject from text
        subject = ""
        for line in text.split("\n"):
            if line.startswith("Subject:"):
                subject = line[8:].strip()
                break

        # Classify
        result = classify(model_data, text)
        intent = result.get("intent", {}).get("label", "other")
        conf = result.get("intent", {}).get("confidence", 0)
        lang = label.get("language", "en")

        print(f"=== Email {i} ===")
        print(f"  From: {label.get('summary', '?')[:60]}")
        print(f"  Intent: {intent} ({conf:.0%}) | Original: {label['intent']}")
        print(f"  Language: {lang}")

        # Generate draft
        t0 = time.time()
        draft = draft_response(client, subject, text[:1000], intent, lang)
        elapsed = time.time() - t0

        print(f"  Draft ({elapsed:.1f}s):")
        for line in draft[:400].split("\n"):
            print(f"    {line}")
        if len(draft) > 400:
            print(f"    ... ({len(draft)} chars total)")
        print()


if __name__ == "__main__":
    main()
