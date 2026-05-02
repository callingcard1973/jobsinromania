#!/usr/bin/env python3
"""
OpenCode + PICOCLAW Integration Bridge
Connects OpenCode's advanced reasoning with PICOCLAW's task execution

Features:
- OpenCode can trigger PICOCLAW tasks
- PICOCLAW can use OpenCode for complex reasoning
- Unified interface for both systems
- Session-based task management
- Result caching and optimization
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
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from threading import Thread
import subprocess

# Configuration
OPENCODE_URL = os.environ.get("OPENCODE_URL", "http://localhost:36000")
OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY", "9c5321026faf4825acb0bb6f7ed9db75.w33X6wEmfs2M3NSc")
PICOCLAW_URL = "http://localhost:5055"
BRIDGE_DB = "/opt/ACTIVE/INFRA/SPAM/opencode_picoclaw_bridge.db"

@dataclass
class BridgeTask:
    """Task that bridges OpenCode and PICOCLAW"""
    task_id: str
    session_id: str
    task_type: str
    source: str  # "opencode" or "picoclaw"
    target: str  # "picoclaw" or "opencode"
    payload: Dict[str, Any]
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class OpenCodePICOCLAWBridge:
    """Main bridge integrating OpenCode and PICOCLAW"""
    
    def __init__(self):
        self.db_path = BRIDGE_DB
        self.logger = self._setup_logger()
        self._init_database()
        self.active_sessions = {}
        self.task_cache = {}
        
    def _setup_logger(self):
        """Setup logging for the bridge"""
        logger = logging.getLogger("OpenCodePICOCLAWBridge")
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
        """Initialize the bridge database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Bridge tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bridge_tasks (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    task_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    payload TEXT,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    error TEXT,
                    created_at DATETIME,
                    completed_at DATETIME
                )
            """)
            
            # Create indexes separately
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bridge_session_id ON bridge_tasks(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bridge_status ON bridge_tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bridge_task_type ON bridge_tasks(task_type)")
            
            # Session tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bridge_sessions (
                    session_id TEXT PRIMARY KEY,
                    source_system TEXT,
                    created_at DATETIME,
                    last_activity DATETIME,
                    task_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bridge_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    task_type TEXT,
                    source_system TEXT,
                    target_system TEXT,
                    total_tasks INTEGER DEFAULT 0,
                    successful_tasks INTEGER DEFAULT 0,
                    avg_duration REAL DEFAULT 0.0,
                    
                    UNIQUE(date, task_type, source_system, target_system)
                )
            """)
            
            conn.commit()
            self.logger.info("OpenCode-PICOCLAW bridge database initialized")
    
    def create_bridge_session(self, source_system: str) -> str:
        """Create a new bridge session"""
        import uuid
        session_id = str(uuid.uuid4())[:8]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bridge_sessions (session_id, source_system, created_at, last_activity, task_count)
                VALUES (?, ?, ?, ?, 0)
            """, (session_id, source_system, datetime.now(), datetime.now()))
            conn.commit()
        
        self.active_sessions[session_id] = {
            'source_system': source_system,
            'created_at': datetime.now(),
            'task_count': 0
        }
        
        self.logger.info(f"Created bridge session: {session_id} from {source_system}")
        return session_id
    
    def opencode_to_picoclaw(self, task_type: str, payload: Dict[str, Any], session_id: str = None) -> str:
        """Execute OpenCode task using PICOCLAW"""
        if session_id is None:
            session_id = self.create_bridge_session("opencode")
        
        # Create bridge task
        task_id = f"bridge_{task_type}_{int(time.time() * 1000000)}"
        bridge_task = BridgeTask(
            task_id=task_id,
            session_id=session_id,
            task_type=task_type,
            source="opencode",
            target="picoclaw",
            payload=payload
        )
        
        # Store task in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bridge_tasks 
                (task_id, session_id, task_type, source, target, payload, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, session_id, task_type, "opencode", "picoclaw",
                json.dumps(payload), "pending", datetime.now()
            ))
            conn.commit()
        
        # Update session activity
        self._update_session_activity(session_id)
        
        # Execute PICOCLAW task
        try:
            self.logger.info(f"Executing OpenCode->PICOCLAW task: {task_type}")
            
            # Submit task to PICOCLAW
            response = requests.post(
                f"{PICOCLAW_URL}/task",
                json={"task_type": task_type, "payload": payload},
                timeout=30
            )
            
            if response.status_code == 201:
                picoclaw_task_id = response.json().get("task_id")
                
                # Wait for result (with timeout)
                result = self._wait_for_picoclaw_result(picoclaw_task_id, timeout=60)
                
                if result:
                    # Update bridge task
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE bridge_tasks 
                            SET status = 'completed', result = ?, completed_at = ?
                            WHERE task_id = ?
                        """, (json.dumps(result), datetime.now(), task_id))
                        conn.commit()
                    
                    self.logger.info(f"OpenCode->PICOCLAW task completed: {task_id}")
                    return result
                else:
                    raise Exception("Task timeout or failed")
            else:
                raise Exception(f"PICOCLAW error: {response.status_code}")
                
        except Exception as e:
            # Update bridge task with error
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bridge_tasks 
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE task_id = ?
                """, (str(e), datetime.now(), task_id))
                conn.commit()
            
            self.logger.error(f"OpenCode->PICOCLAW task failed: {task_id} - {e}")
            raise
    
    def picoclaw_to_opencode(self, task_type: str, payload: Dict[str, Any], prompt: str, session_id: str = None) -> str:
        """Use OpenCode reasoning for PICOCLAW task"""
        if session_id is None:
            session_id = self.create_bridge_session("picoclaw")
        
        # Create bridge task
        task_id = f"bridge_{task_type}_{int(time.time() * 1000000)}"
        bridge_task = BridgeTask(
            task_id=task_id,
            session_id=session_id,
            task_type=task_type,
            source="picoclaw",
            target="opencode",
            payload=payload
        )
        
        # Store task in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bridge_tasks 
                (task_id, session_id, task_type, source, target, payload, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, session_id, task_type, "picoclaw", "opencode",
                json.dumps(payload), "pending", datetime.now()
            ))
            conn.commit()
        
        # Update session activity
        self._update_session_activity(session_id)
        
        # Execute OpenCode reasoning
        try:
            self.logger.info(f"Executing PICOCLAW->OpenCode task: {task_type}")
            
            # Create or get OpenCode session
            if session_id not in self.active_sessions:
                oc_session_id = self._create_opencode_session()
                self.active_sessions[session_id]['oc_session_id'] = oc_session_id
            else:
                oc_session_id = self.active_sessions[session_id].get('oc_session_id')
                if not oc_session_id:
                    oc_session_id = self._create_opencode_session()
                    self.active_sessions[session_id]['oc_session_id'] = oc_session_id
            
            # Send reasoning request to OpenCode
            reasoning_prompt = f"""
            Task Type: {task_type}
            Payload: {json.dumps(payload, indent=2)}
            
            Request: {prompt}
            
            Please analyze this PICOCLAW task and provide enhanced reasoning, suggestions, or improvements.
            """
            
            result = self._send_to_opencode(oc_session_id, reasoning_prompt)
            
            # Update bridge task
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bridge_tasks 
                    SET status = 'completed', result = ?, completed_at = ?
                    WHERE task_id = ?
                """, (json.dumps(result), datetime.now(), task_id))
                conn.commit()
            
            self.logger.info(f"PICOCLAW->OpenCode task completed: {task_id}")
            return result
            
        except Exception as e:
            # Update bridge task with error
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bridge_tasks 
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE task_id = ?
                """, (str(e), datetime.now(), task_id))
                conn.commit()
            
            self.logger.error(f"PICOCLAW->OpenCode task failed: {task_id} - {e}")
            raise
    
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
    
    def _create_opencode_session(self) -> str:
        """Create a new OpenCode session"""
        try:
            headers = {"Authorization": f"Bearer {OPENCODE_API_KEY}"}
            response = requests.post(f"{OPENCODE_URL}/sessions", headers=headers, timeout=10)
            if response.status_code == 200:
                session_data = response.json()
                return session_data.get('session_id')
            else:
                raise Exception(f"Failed to create OpenCode session: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error creating OpenCode session: {e}")
            raise
    
    def _send_to_opencode(self, session_id: str, message: str) -> Dict[str, Any]:
        """Send message to OpenCode session"""
        try:
            headers = {"Authorization": f"Bearer {OPENCODE_API_KEY}"}
            data = {"session_id": session_id, "message": message}
            
            response = requests.post(f"{OPENCODE_URL}/send", headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                # Get session messages to get the response
                messages_response = requests.get(
                    f"{OPENCODE_URL}/sessions/{session_id}/messages",
                    headers=headers,
                    timeout=10
                )
                
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    if messages:
                        # Return the last message (assistant's response)
                        return messages[-1]
                
                return {"response": "Message sent successfully"}
            else:
                raise Exception(f"OpenCode error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error sending to OpenCode: {e}")
            raise
    
    def _update_session_activity(self, session_id: str):
        """Update session activity timestamp and task count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bridge_sessions 
                SET last_activity = ?, task_count = task_count + 1
                WHERE session_id = ?
            """, (datetime.now(), session_id))
            conn.commit()
        
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['task_count'] += 1
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge status and statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Overall stats
                cursor.execute("""
                    SELECT source, target, COUNT(*) as count
                    FROM bridge_tasks
                    GROUP BY source, target
                """)
                flow_stats = {f"{row[0]}->{row[1]}": row[2] for row in cursor.fetchall()}
                
                # Status breakdown
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM bridge_tasks
                    GROUP BY status
                """)
                status_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Recent activity
                cursor.execute("""
                    SELECT task_type, status, created_at
                    FROM bridge_tasks
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                recent_tasks = [
                    {
                        'task_type': row[0],
                        'status': row[1],
                        'created_at': row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'flow_statistics': flow_stats,
                    'status_breakdown': status_stats,
                    'recent_tasks': recent_tasks,
                    'active_sessions': len(self.active_sessions),
                    'picoclaw_available': self._check_picoclaw_status(),
                    'opencode_available': self._check_opencode_status()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting bridge status: {e}")
            return {}
    
    def _check_picoclaw_status(self) -> bool:
        """Check if PICOCLAW is available"""
        try:
            response = requests.get(f"{PICOCLAW_URL}/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _check_opencode_status(self) -> bool:
        """Check if OpenCode is available"""
        try:
            headers = {"Authorization": f"Bearer {OPENCODE_API_KEY}"}
            response = requests.get(f"{OPENCODE_URL}/sessions", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get bridge task history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, session_id, task_type, source, target, 
                           status, created_at, completed_at, error
                    FROM bridge_tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                tasks = []
                for row in cursor.fetchall():
                    task = {
                        'task_id': row[0],
                        'session_id': row[1],
                        'task_type': row[2],
                        'flow': f"{row[3]}->{row[4]}",
                        'status': row[5],
                        'created_at': row[6],
                        'completed_at': row[7],
                        'error': row[8]
                    }
                    tasks.append(task)
                
                return tasks
                
        except Exception as e:
            self.logger.error(f"Error getting task history: {e}")
            return []

def main():
    """Main function to demonstrate the bridge"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenCode + PICOCLAW Bridge")
    parser.add_argument("--status", action="store_true", help="Show bridge status")
    parser.add_argument("--history", action="store_true", help="Show task history")
    parser.add_argument("--test-opencode", action="store_true", help="Test OpenCode integration")
    parser.add_argument("--test-picoclaw", action="store_true", help="Test PICOCLAW integration")
    parser.add_argument("--bridge-spam", help="Test bridge with spam scoring")
    
    args = parser.parse_args()
    
    bridge = OpenCodePICOCLAWBridge()
    
    if args.status:
        print("🌉 OpenCode + PICOCLAW Bridge Status")
        print("=" * 50)
        status = bridge.get_bridge_status()
        print(json.dumps(status, indent=2, default=str))
    
    elif args.history:
        print("📋 Bridge Task History")
        print("=" * 50)
        history = bridge.get_task_history()
        for task in history:
            print(f"{task['created_at']} - {task['flow']} - {task['task_type']} - {task['status']}")
    
    elif args.test_opencode:
        print("🧪 Testing OpenCode Integration...")
        try:
            session_id = bridge.create_bridge_session("test")
            print(f"✅ Created session: {session_id}")
            
            result = bridge.picoclaw_to_opencode(
                "test_task",
                {"test": "data"},
                "Please respond with 'OpenCode integration test successful'",
                session_id
            )
            print("✅ OpenCode test successful")
        except Exception as e:
            print(f"❌ OpenCode test failed: {e}")
    
    elif args.test_picoclaw:
        print("🧪 Testing PICOCLAW Integration...")
        try:
            session_id = bridge.create_bridge_session("test")
            print(f"✅ Created session: {session_id}")
            
            result = bridge.opencode_to_picoclaw(
                "spam_score",
                {"text": "This is a test message for spam scoring"},
                session_id
            )
            print("✅ PICOCLAW test successful")
            print(f"Result: {result}")
        except Exception as e:
            print(f"❌ PICOCLAW test failed: {e}")
    
    elif args.bridge_spam:
        print("🌉 Testing Bridge with Spam Scoring...")
        try:
            # Test OpenCode -> PICOCLAW
            print("1. OpenCode -> PICOCLAW (Spam Scoring)")
            result1 = bridge.opencode_to_picoclaw(
                "spam_score",
                {"text": args.bridge_spam},
                None
            )
            print(f"   Result: {result1}")
            
            # Test PICOCLAW -> OpenCode
            print("\n2. PICOCLAW -> OpenCode (Reasoning about spam result)")
            result2 = bridge.picoclaw_to_opencode(
                "spam_score",
                {"text": args.bridge_spam},
                f"Analyze this spam score result and provide enhanced reasoning: {result1}",
                None
            )
            print(f"   Enhanced reasoning: {result2}")
            
        except Exception as e:
            print(f"❌ Bridge test failed: {e}")

if __name__ == "__main__":
    main()