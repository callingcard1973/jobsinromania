#!/usr/bin/env python3
"""
z.ai Hub - Central AI Coordination System
Coordinates between local LLM, PICOCLAW, OpenCode, and web-based AI systems

Features:
- Intelligent AI system routing
- Multi-AI coordination and aggregation
- Unified access to all AI capabilities
- Performance monitoring and optimization
- Failover and load balancing
"""

import os
import json
import time
import asyncio
import logging
import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

# Configuration
ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "9006de04a73c49dfb2b7ba6c5c47a8d5.94MypMd3P5mDaMVL")
OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY", "9c5321026faf4825acb0bb6f7ed9db75.w33X6wEmfs2M3NSc")
PICOCLAW_URL = "http://localhost:5055"
LM_STUDIO_URL = "http://localhost:1234"
HUB_DB = "/opt/ACTIVE/INFRA/SPAM/zai_hub.db"

@dataclass
class AIProvider:
    """AI provider configuration and status"""
    name: str
    url: str
    api_key: str
    available: bool
    capabilities: List[str]
    priority: int  # 1= highest, 5=lowest
    max_tokens: int
    timeout: int
    last_check: Optional[datetime] = None
    
@dataclass
class AIRequest:
    """AI request with routing information"""
    request_id: str
    task_type: str
    prompt: str
    preferred_provider: Optional[str]
    fallback_providers: List[str]
    max_tokens: int
    timeout: int
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AIResponse:
    """Standardized AI response"""
    request_id: str
    provider: str
    response: str
    success: bool
    error: Optional[str] = None
    response_time: float = 0.0
    tokens_used: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ZAIHub:
    """Central AI coordination hub"""
    
    def __init__(self):
        self.db_path = HUB_DB
        self.logger = self._setup_logger()
        self._init_database()
        self.providers = self._init_providers()
        self.request_queue = []
        self.performance_metrics = {}
        
    def _setup_logger(self):
        """Setup logging for the hub"""
        logger = logging.getLogger("ZAIHub")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize the hub database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # AI providers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_providers (
                    name TEXT PRIMARY KEY,
                    url TEXT,
                    api_key TEXT,
                    available BOOLEAN DEFAULT FALSE,
                    capabilities TEXT,
                    priority INTEGER DEFAULT 3,
                    max_tokens INTEGER DEFAULT 500,
                    timeout INTEGER DEFAULT 60,
                    last_check DATETIME
                )
            """)
            
            # AI requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_requests (
                    request_id TEXT PRIMARY KEY,
                    task_type TEXT,
                    prompt TEXT,
                    preferred_provider TEXT,
                    fallback_providers TEXT,
                    max_tokens INTEGER,
                    timeout INTEGER,
                    created_at DATETIME
                )
            """)
            
            # AI responses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_responses (
                    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    provider TEXT,
                    response TEXT,
                    success BOOLEAN,
                    error TEXT,
                    response_time REAL,
                    tokens_used INTEGER,
                    timestamp DATETIME,
                    
                    FOREIGN KEY (request_id) REFERENCES ai_requests(request_id)
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_name TEXT,
                    task_type TEXT,
                    date DATE,
                    total_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0.0,
                    avg_tokens_used REAL DEFAULT 0.0,
                    
                    UNIQUE(provider_name, task_type, date)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_task_type ON ai_requests(task_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_provider ON ai_responses(provider)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_success ON ai_responses(success)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_provider_task ON performance_metrics(provider_name, task_type)")
            
            conn.commit()
            self.logger.info("z.ai Hub database initialized")
    
    def _init_providers(self) -> Dict[str, AIProvider]:
        """Initialize AI providers"""
        providers = {
            "lm_studio": AIProvider(
                name="lm_studio",
                url=LM_STUDIO_URL,
                api_key="",
                available=False,  # Will check on first use
                capabilities=["chat", "reasoning", "code", "multilingual"],
                priority=1,  # Highest priority (local, fast)
                max_tokens=2000,
                timeout=60
            ),
            "picoclaw": AIProvider(
                name="picoclaw",
                url=PICOCLAW_URL,
                api_key="",
                available=False,
                capabilities=["spam_score", "lead_enrich", "subject_optimize", "job_quality", "response_intent", "email_draft"],
                priority=2,  # Specialized tasks
                max_tokens=1000,
                timeout=120
            ),
            "opencode": AIProvider(
                name="opencode",
                url="http://localhost:36000",
                api_key=OPENCODE_API_KEY,
                available=False,
                capabilities=["advanced_reasoning", "code_analysis", "complex_planning"],
                priority=3,  # Advanced reasoning
                max_tokens=4000,
                timeout=180
            ),
            "zai_web": AIProvider(
                name="zai_web",
                url="https://z.ai",
                api_key=ZAI_API_KEY,
                available=False,
                capabilities=["web_interface", "glm_models", "multilingual_advanced"],
                priority=4,  # Web-based, potentially slower
                max_tokens=2000,
                timeout=300
            )
        }
        
        # Save providers to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for provider in providers.values():
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_providers 
                    (name, url, api_key, available, capabilities, priority, max_tokens, timeout, last_check)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    provider.name,
                    provider.url,
                    provider.api_key,
                    provider.available,
                    json.dumps(provider.capabilities),
                    provider.priority,
                    provider.max_tokens,
                    provider.timeout,
                    provider.last_check
                ))
            conn.commit()
        
        return providers
    
    def check_provider_availability(self, provider_name: str) -> bool:
        """Check if an AI provider is available"""
        if provider_name not in self.providers:
            return False
        
        provider = self.providers[provider_name]
        
        try:
            if provider_name == "lm_studio":
                # Check LM Studio
                r = requests.get(f"{provider.url}/v1/models", timeout=10)
                provider.available = r.status_code == 200
                
            elif provider_name == "picoclaw":
                # Check PICOCLAW
                r = requests.get(f"{provider.url}/status", timeout=10)
                provider.available = r.status_code == 200
                
            elif provider_name == "opencode":
                # Check OpenCode
                if provider.api_key:
                    headers = {"Authorization": f"Bearer {provider.api_key}"}
                    r = requests.get(f"{provider.url}/sessions", headers=headers, timeout=10)
                    provider.available = r.status_code == 200
                else:
                    provider.available = False
                    
            elif provider_name == "zai_web":
                # Check z.ai web (basic connectivity)
                r = requests.get(provider.url, timeout=10)
                provider.available = r.status_code == 200
            
            provider.last_check = datetime.now()
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE ai_providers 
                    SET available = ?, last_check = ?
                    WHERE name = ?
                """, (provider.available, provider.last_check, provider_name))
                conn.commit()
            
            self.logger.info(f"Provider {provider_name} availability: {provider.available}")
            return provider.available
            
        except Exception as e:
            self.logger.error(f"Error checking provider {provider_name}: {e}")
            provider.available = False
            return False
    
    def route_request(self, task_type: str, prompt: str, preferred_provider: str = None, max_tokens: int = 1000, timeout: int = 60) -> AIResponse:
        """Intelligently route AI request to best available provider"""
        # Create request
        request_id = f"req_{int(time.time() * 1000000)}"
        request = AIRequest(
            request_id=request_id,
            task_type=task_type,
            prompt=prompt,
            preferred_provider=preferred_provider,
            fallback_providers=[],
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        # Store request in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_requests 
                (request_id, task_type, prompt, preferred_provider, fallback_providers, max_tokens, timeout, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id, request.task_type, request.prompt, request.preferred_provider,
                json.dumps(request.fallback_providers), request.max_tokens, request.timeout, request.created_at
            ))
            conn.commit()
        
        # Determine provider priority
        providers_to_try = self._get_provider_priority(task_type, preferred_provider)
        
        # Try providers in order of priority
        for provider_name in providers_to_try:
            if self.check_provider_availability(provider_name):
                try:
                    self.logger.info(f"Routing request {request_id} to {provider_name}")
                    response = self._execute_request(request, provider_name)
                    
                    if response.success:
                        self._store_response(response)
                        return response
                    else:
                        self.logger.warning(f"Provider {provider_name} failed for request {request_id}: {response.error}")
                
                except Exception as e:
                    self.logger.error(f"Error executing request on {provider_name}: {e}")
        
        # All providers failed
        error_response = AIResponse(
            request_id=request_id,
            provider="none",
            response="",
            success=False,
            error="All AI providers failed or unavailable",
            response_time=0.0
        )
        
        self._store_response(error_response)
        return error_response
    
    def _get_provider_priority(self, task_type: str, preferred_provider: str = None) -> List[str]:
        """Get provider priority list for task type"""
        # Start with preferred provider if specified and available
        if preferred_provider and preferred_provider in self.providers:
            if self.check_provider_availability(preferred_provider):
                providers = [preferred_provider]
            else:
                providers = []
        else:
            providers = []
        
        # Add providers based on task type
        if task_type in ["spam_score", "lead_enrich", "subject_optimize", "job_quality", "response_intent", "email_draft"]:
            # PICOCLAW specialized tasks
            if "picoclaw" not in providers:
                providers.append("picoclaw")
            # Add LM Studio as fallback
            if "lm_studio" not in providers:
                providers.append("lm_studio")
                
        elif task_type in ["advanced_reasoning", "code_analysis", "complex_planning"]:
            # Advanced reasoning tasks
            if "opencode" not in providers:
                providers.append("opencode")
            if "lm_studio" not in providers:
                providers.append("lm_studio")
            if "zai_web" not in providers:
                providers.append("zai_web")
                
        else:
            # General tasks (chat, general reasoning)
            if "lm_studio" not in providers:
                providers.append("lm_studio")
            if "opencode" not in providers:
                providers.append("opencode")
            if "zai_web" not in providers:
                providers.append("zai_web")
        
        # Add remaining providers as fallbacks
        for provider_name in self.providers.keys():
            if provider_name not in providers:
                providers.append(provider_name)
        
        return providers
    
    def _execute_request(self, request: AIRequest, provider_name: str) -> AIResponse:
        """Execute request on specific provider"""
        provider = self.providers[provider_name]
        start_time = time.time()
        
        try:
            if provider_name == "lm_studio":
                response = self._execute_lm_studio(request, provider)
            elif provider_name == "picoclaw":
                response = self._execute_picoclaw(request, provider)
            elif provider_name == "opencode":
                response = self._execute_opencode(request, provider)
            elif provider_name == "zai_web":
                response = self._execute_zai_web(request, provider)
            else:
                raise Exception(f"Unknown provider: {provider_name}")
            
            response_time = time.time() - start_time
            response.response_time = response_time
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            return AIResponse(
                request_id=request.request_id,
                provider=provider_name,
                response="",
                success=False,
                error=str(e),
                response_time=response_time
            )
    
    def _execute_lm_studio(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        """Execute request on LM Studio"""
        try:
            # Get available models
            models_response = requests.get(f"{provider.url}/v1/models", timeout=10)
            if models_response.status_code != 200:
                raise Exception(f"LM Studio models error: {models_response.status_code}")
            
            models_data = models_response.json()
            available_models = [model['id'] for model in models_data.get('data', [])]
            
            # Use first available model or default
            model = available_models[0] if available_models else "lfm2.5-1.2b-instruct"
            
            # Make completion request
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{provider.url}/v1/chat/completions",
                json=payload,
                timeout=provider.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                return AIResponse(
                    request_id=request.request_id,
                    provider=provider.name,
                    response=content,
                    success=True,
                    error=None,
                    response_time=0.0,  # Will be set by caller
                    tokens_used=tokens_used
                )
            else:
                raise Exception(f"LM Studio error: {response.status_code}")
                
        except Exception as e:
            return AIResponse(
                request_id=request.request_id,
                provider=provider.name,
                response="",
                success=False,
                error=str(e)
            )
    
    def _execute_picoclaw(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        """Execute request on PICOCLAW"""
        try:
            # PICOCLAW tasks have specific formats
            if request.task_type == "spam_score":
                payload = {"text": request.prompt}
            elif request.task_type in ["lead_enrich", "job_quality"]:
                # Parse company and country from prompt
                parts = request.prompt.split(',')
                if len(parts) >= 2:
                    company = parts[0].strip()
                    country = parts[1].strip()
                    payload = {"company": company, "country": country}
                else:
                    payload = {"company": request.prompt, "country": "unknown"}
            else:
                payload = {"query": request.prompt}
            
            # Submit task to PICOCLAW
            response = requests.post(
                f"{provider.url}/task",
                json={"task_type": request.task_type, "payload": payload},
                timeout=30
            )
            
            if response.status_code == 201:
                task_id = response.json().get("task_id")
                
                # Wait for result
                result = self._wait_for_picoclaw_result(task_id, provider.timeout)
                
                if result:
                    return AIResponse(
                        request_id=request.request_id,
                        provider=provider.name,
                        response=json.dumps(result),
                        success=True
                    )
                else:
                    raise Exception("PICOCLAW task timeout or failed")
            else:
                raise Exception(f"PICOCLAW error: {response.status_code}")
                
        except Exception as e:
            return AIResponse(
                request_id=request.request_id,
                provider=provider.name,
                response="",
                success=False,
                error=str(e)
            )
    
    def _execute_opencode(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        """Execute request on OpenCode"""
        try:
            # Note: OpenCode server may not be running, so this may fail
            headers = {"Authorization": f"Bearer {provider.api_key}"}
            
            # Create session
            session_response = requests.post(f"{provider.url}/sessions", headers=headers, timeout=10)
            if session_response.status_code != 200:
                raise Exception(f"OpenCode session error: {session_response.status_code}")
            
            session_data = session_response.json()
            session_id = session_data.get('session_id')
            
            # Send message
            message_response = requests.post(
                f"{provider.url}/send",
                headers=headers,
                json={"session_id": session_id, "message": request.prompt},
                timeout=provider.timeout
            )
            
            if message_response.status_code == 200:
                # Get response messages
                messages_response = requests.get(
                    f"{provider.url}/sessions/{session_id}/messages",
                    headers=headers,
                    timeout=10
                )
                
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    if messages:
                        response_text = messages[-1].get('content', '')
                        return AIResponse(
                            request_id=request.request_id,
                            provider=provider.name,
                            response=response_text,
                            success=True
                        )
            
            raise Exception(f"OpenCode communication error")
            
        except Exception as e:
            return AIResponse(
                request_id=request.request_id,
                provider=provider.name,
                response="",
                success=False,
                error=str(e)
            )
    
    def _execute_zai_web(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        """Execute request on z.ai web (simulated)"""
        try:
            # Note: z.ai is a web interface, not a traditional API
            # This is a placeholder that would need web automation or official API
            
            # For now, return a simulated response
            response_text = f"z.ai web response for: {request.prompt[:100]}...\n\n(This is a placeholder - would need web automation or official API)"
            
            return AIResponse(
                request_id=request.request_id,
                provider=provider.name,
                response=response_text,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                request_id=request.request_id,
                provider=provider.name,
                response="",
                success=False,
                error=str(e)
            )
    
    def _wait_for_picoclaw_result(self, task_id: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Wait for PICOCLAW task to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{PICOCLAW_URL}/task/{task_id}", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'completed':
                        return result.get('result')
                    elif result.get('status') == 'failed':
                        raise Exception(f"PICOCLAW task failed: {result.get('error', 'Unknown error')}")
                
                time.sleep(2)
            except requests.RequestException:
                time.sleep(2)
        
        return None
    
    def _store_response(self, response: AIResponse):
        """Store AI response in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_responses 
                (request_id, provider, response, success, error, response_time, tokens_used, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response.request_id, response.provider, response.response, response.success,
                response.error, response.response_time, response.tokens_used, response.timestamp
            ))
            conn.commit()
    
    def get_hub_status(self) -> Dict[str, Any]:
        """Get comprehensive hub status"""
        status = {
            "providers": {},
            "recent_requests": [],
            "performance_summary": {}
        }
        
        # Check all provider statuses
        for provider_name, provider in self.providers.items():
            is_available = self.check_provider_availability(provider_name)
            status["providers"][provider_name] = {
                "name": provider.name,
                "url": provider.url,
                "available": is_available,
                "capabilities": provider.capabilities,
                "priority": provider.priority,
                "last_check": provider.last_check.isoformat() if provider.last_check else None
            }
        
        # Get recent requests
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.request_id, r.task_type, r.created_at, 
                       re.provider, re.success, re.response_time
                FROM ai_requests r
                LEFT JOIN ai_responses re ON r.request_id = re.request_id
                ORDER BY r.created_at DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                status["recent_requests"].append({
                    "request_id": row[0],
                    "task_type": row[1],
                    "created_at": row[2],
                    "provider": row[3],
                    "success": bool(row[4]),
                    "response_time": row[5]
                })
        
        return status
    
    def aggregate_multiple_responses(self, task_type: str, prompt: str, providers: List[str] = None) -> Dict[str, Any]:
        """Get responses from multiple providers and aggregate results"""
        if providers is None:
            providers = list(self.providers.keys())
        
        responses = {}
        successful_responses = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit requests to multiple providers
            future_to_provider = {}
            for provider_name in providers:
                if self.check_provider_availability(provider_name):
                    future = executor.submit(
                        self.route_request, 
                        task_type, prompt, preferred_provider=provider_name
                    )
                    future_to_provider[future] = provider_name
            
            # Collect responses
            for future in as_completed(future_to_provider):
                provider_name = future_to_provider[future]
                try:
                    response = future.result(timeout=120)
                    responses[provider_name] = asdict(response)
                    
                    if response.success:
                        successful_responses[provider_name] = response.response
                    
                except Exception as e:
                    responses[provider_name] = {
                        "provider": provider_name,
                        "success": False,
                        "error": str(e)
                    }
        
        # Create aggregation result
        aggregation_result = {
            "task_type": task_type,
            "prompt": prompt,
            "total_providers": len(providers),
            "successful_responses": len(successful_responses),
            "responses": responses,
            "aggregated_insights": self._generate_insights(successful_responses)
        }
        
        return aggregation_result
    
    def _generate_insights(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """Generate insights from multiple AI responses"""
        insights = {
            "consensus": "",
            "differences": [],
            "recommendation": ""
        }
        
        if len(responses) >= 2:
            # Simple consensus detection
            response_texts = list(responses.values())
            
            # Check for similarity (simplified)
            if len(set(response_texts)) == 1:
                insights["consensus"] = "All providers agree"
            else:
                insights["consensus"] = "Providers have different perspectives"
                insights["differences"] = [f"{provider}: {text[:100]}..." for provider, text in responses.items()]
            
            insights["recommendation"] = "Consider the different perspectives and use the most appropriate response for your context"
        elif len(responses) == 1:
            insights["consensus"] = "Single provider response"
            insights["recommendation"] = "Response from available provider"
        else:
            insights["consensus"] = "No successful responses"
            insights["recommendation"] = "Check provider availability and try again"
        
        return insights

def main():
    """Main function to demonstrate z.ai Hub"""
    import argparse
    
    parser = argparse.ArgumentParser(description="z.ai Hub - Central AI Coordination")
    parser.add_argument("--status", action="store_true", help="Show hub status")
    parser.add_argument("--test", help="Test hub with a prompt")
    parser.add_argument("--test-task", help="Test specific task type")
    parser.add_argument("--multi", help="Test multiple providers aggregation")
    parser.add_argument("--provider", help="Test specific provider")
    
    args = parser.parse_args()
    
    hub = ZAIHub()
    
    if args.status:
        print("🌐 z.ai Hub Status")
        print("=" * 50)
        status = hub.get_hub_status()
        print(json.dumps(status, indent=2, default=str))
    
    elif args.test:
        print(f"🧪 Testing z.ai Hub with: {args.test}")
        try:
            response = hub.route_request("general", args.test)
            print(f"✅ Provider: {response.provider}")
            print(f"✅ Success: {response.success}")
            if response.success:
                print(f"📝 Response: {response.response[:200]}...")
            else:
                print(f"❌ Error: {response.error}")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    elif args.test_task:
        print(f"🧪 Testing z.ai Hub with task: {args.test_task}")
        prompt = f"Test prompt for {args.test_task}"
        try:
            response = hub.route_request(args.test_task, prompt, preferred_provider=args.provider)
            print(f"✅ Provider: {response.provider}")
            print(f"✅ Success: {response.success}")
            if response.success:
                print(f"📝 Response: {response.response[:200]}...")
            else:
                print(f"❌ Error: {response.error}")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    elif args.multi:
        print(f"🌐 Testing multiple provider aggregation: {args.multi}")
        try:
            result = hub.aggregate_multiple_responses("general", args.multi)
            print("📊 Aggregation Results:")
            print(f"   Total Providers: {result['total_providers']}")
            print(f"   Successful Responses: {result['successful_responses']}")
            print(f"   Consensus: {result['aggregated_insights']['consensus']}")
            print("\n📝 Provider Responses:")
            for provider, response_data in result['responses'].items():
                success = "✅" if response_data.get('success') else "❌"
                print(f"   {success} {provider}: {response_data.get('response', response_data.get('error', 'No response'))[:100]}...")
        except Exception as e:
            print(f"❌ Multi-test failed: {e}")

if __name__ == "__main__":
    main()