#!/usr/bin/env python3
"""
Train sklearn email classifier from labeled training pairs.

Trains TF-IDF + LogisticRegression for:
  - intent (9 classes)
  - priority (3 classes)
  - folder (4 classes)

Usage: python3 train_classifier.py [--test-size 0.2] [--verbose]
"""

import json
import os
import pickle
import sys
import time
import re
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

# Paths
DATA_DIR = Path(__file__).parent
TRAINING_FILE = DATA_DIR / "training_pairs.jsonl"
MODEL_DIR = DATA_DIR / "models"
MODEL_FILE = MODEL_DIR / "email_classifier.pkl"


def load_training_data(path):
    """Load training pairs from JSONL file."""
    inputs = []
    labels = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            inp = rec["input"]
            out = json.loads(rec["output"])
            inputs.append(inp)
            labels.append(out)

    print(f"Loaded {len(inputs)} training examples")
    return inputs, labels


def preprocess_email(text):
    """Clean email text for classification."""
    # Normalize whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove very long base64/encoded blocks
    text = re.sub(r'[A-Za-z0-9+/=]{100,}', ' [encoded_block] ', text)

    # Normalize email addresses to keep domain info
    text = re.sub(r'[\w.+-]+@([\w.-]+)', r'EMAIL_\1', text)

    # Truncate very long emails (keep first 2000 chars)
    if len(text) > 2000:
        text = text[:2000] + " [truncated]"

    return text


def extract_targets(labels):
    """Extract intent, priority, and folder arrays from label dicts."""
    intents = [l.get("intent", "other") for l in labels]
    priorities = [l.get("priority", "normal") for l in labels]
    folders = [l.get("folder", "INBOX") for l in labels]
    languages = [l.get("language", "en") for l in labels]

    return intents, priorities, folders, languages


def train_model(X_texts, y_labels, label_name, test_size=0.2):
    """Train a TF-IDF + LogisticRegression pipeline for one target."""

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_texts, y_labels, test_size=test_size, random_state=42, stratify=y_labels
    )

    # Pipeline: TF-IDF + Logistic Regression
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=15000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents='unicode',
            lowercase=True,
        )),
        ('clf', LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            C=1.0,
            solver='lbfgs',
            
        ))
    ])

    # Train
    t0 = time.time()
    pipeline.fit(X_train, y_train)
    train_time = time.time() - t0

    # Predict
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n{'='*60}")
    print(f"Model: {label_name}")
    print(f"{'='*60}")
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    print(f"Training time: {train_time:.2f}s")
    print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Confidence stats on test set
    y_proba = pipeline.predict_proba(X_test)
    confidences = np.max(y_proba, axis=1)
    print(f"Confidence stats: mean={confidences.mean():.3f}, "
          f"min={confidences.min():.3f}, median={np.median(confidences):.3f}")
    low_conf = (confidences < 0.6).sum()
    print(f"Low confidence (<0.6): {low_conf}/{len(X_test)} ({low_conf/len(X_test)*100:.1f}%)")

    return pipeline, accuracy


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train email classifier")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split ratio")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Load data
    print("Loading training data...")
    inputs, labels = load_training_data(TRAINING_FILE)

    # Preprocess
    print("Preprocessing emails...")
    processed = [preprocess_email(text) for text in inputs]

    # Extract targets
    intents, priorities, folders, languages = extract_targets(labels)

    # Show class distributions
    print("\nIntent distribution:")
    for k, v in Counter(intents).most_common():
        print(f"  {k}: {v} ({v/len(intents)*100:.1f}%)")

    print("\nPriority distribution:")
    for k, v in Counter(priorities).most_common():
        print(f"  {k}: {v} ({v/len(priorities)*100:.1f}%)")

    print("\nFolder distribution:")
    for k, v in Counter(folders).most_common():
        print(f"  {k}: {v} ({v/len(folders)*100:.1f}%)")

    # Handle classes with too few examples for stratified split
    intent_counts = Counter(intents)
    min_for_split = max(2, int(1 / args.test_size) + 1)

    intents_adjusted = []
    merged_classes = []
    for intent in intents:
        if intent_counts[intent] < min_for_split:
            intents_adjusted.append("_rare")
            if intent not in merged_classes:
                merged_classes.append(intent)
        else:
            intents_adjusted.append(intent)

    from collections import Counter as _C2
    _rare_count = _C2(intents_adjusted).get("_rare", 0)
    if _rare_count > 0 and _rare_count < min_for_split:
        intents_adjusted = ["other" if x == "_rare" else x for x in intents_adjusted]
        print(f"Merged {_rare_count} rare examples into other")
    elif merged_classes:
        print(f"Merged rare classes into _rare: {merged_classes}")

    # Train intent classifier
    models = {}

    intent_pipeline, intent_acc = train_model(
        processed, intents_adjusted, "Intent Classifier", args.test_size
    )
    models['intent'] = {
        'pipeline': intent_pipeline,
        'accuracy': intent_acc,
    }

    # Train priority classifier
    priority_pipeline, priority_acc = train_model(
        processed, priorities, "Priority Classifier", args.test_size
    )
    models['priority'] = {
        'pipeline': priority_pipeline,
        'accuracy': priority_acc,
    }

    # Train folder classifier
    folder_pipeline, folder_acc = train_model(
        processed, folders, "Folder Classifier", args.test_size
    )
    models['folder'] = {
        'pipeline': folder_pipeline,
        'accuracy': folder_acc,
    }

    # Save all models
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_data = {
        'intent': models['intent']['pipeline'],
        'priority': models['priority']['pipeline'],
        'folder': models['folder']['pipeline'],
        'metadata': {
            'trained_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'training_examples': len(inputs),
            'test_size': args.test_size,
            'accuracies': {
                'intent': models['intent']['accuracy'],
                'priority': models['priority']['accuracy'],
                'folder': models['folder']['accuracy'],
            },
            'merged_rare_classes': merged_classes,
            'intent_classes': sorted(set(intents)),
            'priority_classes': sorted(set(priorities)),
            'folder_classes': sorted(set(folders)),
        }
    }

    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model_data, f)

    file_size = os.path.getsize(MODEL_FILE) / 1024 / 1024
    print(f"\n{'='*60}")
    print(f"Model saved to: {MODEL_FILE}")
    print(f"File size: {file_size:.1f} MB")
    print(f"{'='*60}")

    # Speed test
    print("\nSpeed test: classifying 100 emails...")
    t0 = time.time()
    sample = processed[:100]
    intent_pipeline.predict(sample)
    priority_pipeline.predict(sample)
    folder_pipeline.predict(sample)
    speed_time = time.time() - t0
    print(f"100 emails classified in {speed_time:.3f}s ({speed_time/100*1000:.1f}ms per email)")

    # Summary
    print(f"\n{'='*60}")
    print("TRAINING SUMMARY")
    print(f"{'='*60}")
    print(f"Intent accuracy:   {models['intent']['accuracy']*100:.1f}%")
    print(f"Priority accuracy: {models['priority']['accuracy']*100:.1f}%")
    print(f"Folder accuracy:   {models['folder']['accuracy']*100:.1f}%")
    print(f"Speed:             {speed_time/100*1000:.1f}ms per email (all 3 classifiers)")
    print(f"Model size:        {file_size:.1f} MB")
    if merged_classes:
        print(f"Rare classes:      {merged_classes} (merged, will be handled by LLM fallback)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
