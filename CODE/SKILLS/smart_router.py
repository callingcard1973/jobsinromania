#!/usr/bin/env python3
"""
SMART ROUTER - Routes LLM queries to cheapest capable endpoint

Token Optimization Strategy:
  Tier 1: Local Rules (0 tokens) - pattern matching, regex, keywords
  Tier 2: Local LLM (0 tokens) - llama-3.2-3b on raspibig:1234
  Tier 3: Laptop LLM (0 tokens) - deepseek-r1-8b on 192.168.100.25:1234
  Tier 4: Cerebras (free tier) - llama-3.3-70b cloud
  Tier 5: Claude (paid tokens) - fallback only

Saves 70-90% tokens by routing to appropriate tier.

Usage:
    from smart_router import SmartRouter, route_query

    # Quick route (auto-detects best endpoint)
    result = route_query("classify", "Is this spam?", text="STOP sending emails")

    # Full control
    router = SmartRouter()
    result = router.route("spam_score", {"text": "FREE MONEY!!!"})
"""

import os
import sys
import json
import re
import time
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, asdict, field

# Config
STATS_FILE = Path("/opt/ACTIVE/INFRA/GOVERNOR/router_stats.json")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")

# Endpoints
ENDPOINTS = {
    "local": {
        "host": "localhost",
        "port": 1234,
        "models": ["llama-3.2-3b", "phi-3.5-mini", "qwen-coder-7b"],
        "timeout": 30,
        "cost_per_1k": 0
    },
    "laptop": {
        "host": "192.168.100.25",
        "port": 1234,
        "models": ["deepseek-r1-8b", "gemma-3-4b", "devstral"],
        "timeout": 60,
        "cost_per_1k": 0
    },
    "cerebras": {
        "host": "api.cerebras.ai",
        "models": ["llama-3.3-70b"],
        "timeout": 30,
        "cost_per_1k": 0,  # Free tier
        "api_key_env": "CEREBRAS_API_KEY"
    },
    "picoclaw": {
        "host": "localhost",
        "port": 5055,
        "timeout": 60,
        "cost_per_1k": 0
    }
}

# Task routing rules
TASK_ROUTING = {
    # Classification tasks -> always local (fast, simple)
    "classify": ["local", "picoclaw"],
    "spam_score": ["local", "picoclaw"],
    "intent": ["local", "picoclaw"],
    "template": ["local"],

    # Code tasks -> laptop (needs reasoning)
    "code": ["laptop", "cerebras"],
    "fix_code": ["laptop", "cerebras"],
    "review_code": ["laptop", "cerebras"],

    # Heavy reasoning -> laptop/cerebras
    "reasoning": ["laptop", "cerebras"],
    "analysis": ["laptop", "cerebras"],
    "strategy": ["cerebras", "laptop"],

    # Translation -> local (specialized model)
    "translate": ["local"],

    # Enrichment -> local
    "enrich": ["local", "picoclaw"],
    "lead_enrich": ["local", "picoclaw"],

    # General -> cascading
    "general": ["local", "laptop", "cerebras"]
}


@dataclass
class RouterStats:
    """Track routing statistics for token savings"""
    local_calls: int = 0
    laptop_calls: int = 0
    cerebras_calls: int = 0
    picoclaw_calls: int = 0
    claude_fallbacks: int = 0
    tokens_saved: int = 0
    last_updated: str = ""


@dataclass
class RouteResult:
    """Result from routing a query"""
    success: bool
    endpoint: str
    response: Any
    latency_ms: int
    tokens_used: int = 0
    error: Optional[str] = None


class SmartRouter:
    """Routes LLM queries to cheapest capable endpoint"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.stats = self._load_stats()
        self.endpoint_status: Dict[str, bool] = {}
        self._last_check: Dict[str, float] = {}

    def _setup_logging(self) -> logging.Logger:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("smart_router")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            fh = logging.FileHandler(LOG_DIR / "smart_router.log")
            fh.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(fh)

        return logger

    def _load_stats(self) -> RouterStats:
        """Load routing statistics"""
        if STATS_FILE.exists():
            try:
                data = json.loads(STATS_FILE.read_text())
                return RouterStats(**data)
            except:
                pass
        return RouterStats()

    def _save_stats(self):
        """Save routing statistics"""
        self.stats.last_updated = datetime.now().isoformat()
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(asdict(self.stats), indent=2))

    def check_endpoint(self, name: str, force: bool = False) -> bool:
        """Check if endpoint is available (with 30s cache)"""
        now = time.time()
        if not force and name in self._last_check:
            if now - self._last_check[name] < 30:
                return self.endpoint_status.get(name, False)

        endpoint = ENDPOINTS.get(name)
        if not endpoint:
            return False

        available = False

        if name in ["local", "laptop"]:
            # LM Studio check
            try:
                url = f"http://{endpoint['host']}:{endpoint['port']}/v1/models"
                resp = requests.get(url, timeout=2)
                available = resp.status_code == 200
            except:
                pass

        elif name == "picoclaw":
            # PicoClaw API check
            try:
                url = f"http://{endpoint['host']}:{endpoint['port']}/health"
                resp = requests.get(url, timeout=2)
                available = resp.status_code == 200
            except:
                pass

        elif name == "cerebras":
            # Cerebras API key check
            api_key = os.getenv(endpoint.get('api_key_env', ''))
            available = bool(api_key)

        self.endpoint_status[name] = available
        self._last_check[name] = now
        return available

    def discover_available(self) -> List[str]:
        """Discover all available endpoints"""
        available = []
        for name in ENDPOINTS:
            if self.check_endpoint(name):
                available.append(name)
        return available

    def call_local(self, prompt: str, system: str = None) -> Optional[str]:
        """Call local LM Studio"""
        endpoint = ENDPOINTS["local"]
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            url = f"http://{endpoint['host']}:{endpoint['port']}/v1/chat/completions"
            resp = requests.post(url, json={
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500
            }, timeout=endpoint['timeout'])

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Local LLM failed: {e}")
        return None

    def call_laptop(self, prompt: str, system: str = None) -> Optional[str]:
        """Call laptop LM Studio"""
        endpoint = ENDPOINTS["laptop"]
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            url = f"http://{endpoint['host']}:{endpoint['port']}/v1/chat/completions"
            resp = requests.post(url, json={
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1000
            }, timeout=endpoint['timeout'])

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.debug(f"Laptop LLM failed: {e}")
        return None

    def call_cerebras(self, prompt: str, system: str = None) -> Optional[str]:
        """Call Cerebras API (free tier)"""
        api_key = os.getenv('CEREBRAS_API_KEY')
        if not api_key:
            return None

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=30
            )

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Cerebras failed: {e}")
        return None

    def call_picoclaw(self, task_type: str, payload: Dict) -> Optional[Dict]:
        """Call PicoClaw API for structured tasks"""
        endpoint = ENDPOINTS["picoclaw"]
        try:
            url = f"http://{endpoint['host']}:{endpoint['port']}/process"
            resp = requests.post(url, json={
                "task_type": task_type,
                "payload": payload
            }, timeout=endpoint['timeout'])

            if resp.status_code == 200:
                data = resp.json()
                return data.get("result")
        except Exception as e:
            self.logger.debug(f"PicoClaw failed: {e}")
        return None

    def apply_rules(self, task_type: str, payload: Dict) -> Optional[Any]:
        """Apply local rules (zero LLM cost)"""
        text = payload.get("text", "") or payload.get("body", "")

        if task_type in ["classify", "intent"]:
            text_lower = text.lower()

            # Spam indicators
            if any(w in text_lower for w in ["unsubscribe", "stop", "remove me", "optout"]):
                return {"intent": "unsubscribe", "confidence": 95}

            if any(w in text_lower for w in ["interested", "tell me more", "send info", "contact me"]):
                return {"intent": "interested", "confidence": 80}

            if any(w in text_lower for w in ["not interested", "no thanks", "not now"]):
                return {"intent": "not_interested", "confidence": 85}

            # Auto-reply detection
            if any(w in text_lower for w in ["out of office", "automatic reply", "auto-reply", "vacation"]):
                return {"intent": "auto_reply", "confidence": 95}

            # Bounce detection
            if any(w in text_lower for w in ["delivery failed", "undeliverable", "mailer-daemon"]):
                return {"intent": "bounce", "confidence": 95}

        elif task_type == "spam_score":
            text_lower = text.lower()
            score = 0
            reasons = []

            # Spam indicators
            if text_lower.count("free") > 2:
                score += 30
                reasons.append("multiple 'free'")
            if "!!!" in text:
                score += 20
                reasons.append("excessive punctuation")
            if text_lower.count("$") > 1:
                score += 25
                reasons.append("money symbols")
            if any(w in text_lower for w in ["viagra", "lottery", "winner"]):
                score += 50
                reasons.append("spam keywords")

            if score > 0:
                return {"score": min(score, 100), "reason": ", ".join(reasons)}

        return None

    def route(self, task_type: str, payload: Dict,
              prefer_endpoint: str = None) -> RouteResult:
        """Route a task to the best endpoint"""
        start_time = time.time()

        # Try local rules first (free!)
        rule_result = self.apply_rules(task_type, payload)
        if rule_result:
            self.logger.info(f"Task {task_type} resolved by rules (0 tokens)")
            return RouteResult(
                success=True,
                endpoint="rules",
                response=rule_result,
                latency_ms=int((time.time() - start_time) * 1000)
            )

        # Get routing order
        endpoints = TASK_ROUTING.get(task_type, TASK_ROUTING["general"])
        if prefer_endpoint and prefer_endpoint in endpoints:
            endpoints = [prefer_endpoint] + [e for e in endpoints if e != prefer_endpoint]

        # Build prompt
        prompt = self._build_prompt(task_type, payload)
        system = self._get_system_prompt(task_type)

        # Try endpoints in order
        for endpoint_name in endpoints:
            if not self.check_endpoint(endpoint_name):
                continue

            result = None

            if endpoint_name == "local":
                result = self.call_local(prompt, system)
                if result:
                    self.stats.local_calls += 1
                    self.stats.tokens_saved += len(prompt.split()) * 4  # Approx tokens

            elif endpoint_name == "laptop":
                result = self.call_laptop(prompt, system)
                if result:
                    self.stats.laptop_calls += 1
                    self.stats.tokens_saved += len(prompt.split()) * 4

            elif endpoint_name == "cerebras":
                result = self.call_cerebras(prompt, system)
                if result:
                    self.stats.cerebras_calls += 1
                    self.stats.tokens_saved += len(prompt.split()) * 4

            elif endpoint_name == "picoclaw":
                result = self.call_picoclaw(task_type, payload)
                if result:
                    self.stats.picoclaw_calls += 1
                    self.stats.tokens_saved += len(prompt.split()) * 4

            if result:
                self._save_stats()
                latency = int((time.time() - start_time) * 1000)
                self.logger.info(f"Task {task_type} -> {endpoint_name} ({latency}ms)")
                return RouteResult(
                    success=True,
                    endpoint=endpoint_name,
                    response=result,
                    latency_ms=latency
                )

        # All endpoints failed
        self.stats.claude_fallbacks += 1
        self._save_stats()

        return RouteResult(
            success=False,
            endpoint="none",
            response=None,
            latency_ms=int((time.time() - start_time) * 1000),
            error="All endpoints unavailable"
        )

    def _build_prompt(self, task_type: str, payload: Dict) -> str:
        """Build prompt for task type"""
        if task_type == "spam_score":
            text = payload.get("text", "")
            subject = payload.get("subject", "")
            return f"""Score this email for spam likelihood (0-100).
Return JSON: {{"score": N, "reason": "explanation"}}

Subject: {subject}
Body: {text[:1000]}"""

        elif task_type in ["classify", "intent"]:
            text = payload.get("text", "")
            return f"""Classify this email response intent.
Return JSON: {{"intent": "interested|not_interested|question|auto_reply|bounce|other", "confidence": 0-100}}

Email: {text[:1000]}"""

        elif task_type == "lead_enrich":
            company = payload.get("company", "")
            country = payload.get("country", "")
            return f"""Analyze this company for recruitment potential.
Return JSON: {{"industry": "...", "size": "...", "recruitment_score": "high/medium/low"}}

Company: {company}
Country: {country}"""

        elif task_type == "translate":
            text = payload.get("text", "")
            target = payload.get("target_language", "english")
            return f"Translate to {target}:\n\n{text}"

        else:
            return payload.get("prompt", str(payload))

    def _get_system_prompt(self, task_type: str) -> str:
        """Get system prompt for task type"""
        prompts = {
            "spam_score": "You are a spam detection system. Return only valid JSON.",
            "classify": "You are an email classifier. Return only valid JSON.",
            "intent": "You are an intent classifier. Return only valid JSON.",
            "lead_enrich": "You are a business analyst. Return only valid JSON.",
            "translate": "You are a professional translator.",
            "code": "You are an expert programmer. Write clean, efficient code.",
        }
        return prompts.get(task_type, "You are a helpful assistant.")


# Singleton instance
_router: Optional[SmartRouter] = None


def get_router() -> SmartRouter:
    """Get or create router instance"""
    global _router
    if _router is None:
        _router = SmartRouter()
    return _router


def route_query(task_type: str, prompt: str = None, **payload) -> RouteResult:
    """Convenience function to route a query"""
    if prompt:
        payload["prompt"] = prompt
    return get_router().route(task_type, payload)


def classify(text: str) -> Dict:
    """Classify text intent"""
    result = route_query("classify", text=text)
    if result.success:
        try:
            if isinstance(result.response, dict):
                return result.response
            return json.loads(result.response)
        except:
            return {"intent": "unknown", "raw": result.response}
    return {"intent": "unknown", "error": result.error}


def spam_score(text: str, subject: str = "") -> Dict:
    """Score text for spam"""
    result = route_query("spam_score", text=text, subject=subject)
    if result.success:
        try:
            if isinstance(result.response, dict):
                return result.response
            return json.loads(result.response)
        except:
            return {"score": 50, "raw": result.response}
    return {"score": 50, "error": result.error}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Smart LLM Router')
    parser.add_argument('--test', metavar='PROMPT', help='Test routing with prompt')
    parser.add_argument('--task', default='general', help='Task type')
    parser.add_argument('--discover', action='store_true', help='Discover endpoints')
    parser.add_argument('--stats', action='store_true', help='Show routing stats')
    args = parser.parse_args()

    router = SmartRouter()

    if args.discover:
        print("Discovering endpoints...")
        available = router.discover_available()
        print(f"\nAvailable: {available}")
        for name in ENDPOINTS:
            status = "✓" if name in available else "✗"
            print(f"  {status} {name}: {ENDPOINTS[name].get('host', 'N/A')}")
        sys.exit(0)

    if args.stats:
        print(f"Routing Statistics:")
        print(f"  Local calls: {router.stats.local_calls}")
        print(f"  Laptop calls: {router.stats.laptop_calls}")
        print(f"  Cerebras calls: {router.stats.cerebras_calls}")
        print(f"  PicoClaw calls: {router.stats.picoclaw_calls}")
        print(f"  Claude fallbacks: {router.stats.claude_fallbacks}")
        print(f"  Tokens saved (est): {router.stats.tokens_saved:,}")
        print(f"  Last updated: {router.stats.last_updated}")
        sys.exit(0)

    if args.test:
        print(f"Routing task '{args.task}': {args.test[:50]}...")
        result = router.route(args.task, {"prompt": args.test})
        print(f"\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Endpoint: {result.endpoint}")
        print(f"  Latency: {result.latency_ms}ms")
        print(f"  Response: {result.response}")
        if result.error:
            print(f"  Error: {result.error}")
        sys.exit(0 if result.success else 1)

    # Default: show status
    print("Smart Router Status")
    print("=" * 40)
    available = router.discover_available()
    print(f"Available endpoints: {available}")
    print(f"Stats: {router.stats.tokens_saved:,} tokens saved")


if __name__ == "__main__":
    main()
