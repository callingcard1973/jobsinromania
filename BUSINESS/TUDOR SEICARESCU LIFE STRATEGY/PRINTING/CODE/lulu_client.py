#!/usr/bin/env python3
"""Lulu Print API Client - Core Authentication & File Operations"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LuluAPI:
    """Lulu Print API OAuth 2.0 client"""

    def __init__(self, client_key: str, client_secret: str, sandbox: bool = False):
        self.client_key = client_key
        self.client_secret = client_secret
        self.sandbox = sandbox

        if sandbox:
            self.base_url = "https://api.sandbox.lulu.com"
            self.token_url = "https://api.sandbox.lulu.com/auth/realms/glasstree/protocol/openid-connect/token"
        else:
            self.base_url = "https://api.lulu.com"
            self.token_url = "https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token"

        self.access_token = None
        self.token_expiry = None
        self.session = requests.Session()

    def get_token(self) -> str:
        """Get OAuth 2.0 access token"""
        try:
            response = self.session.post(
                self.token_url,
                data={
                    "client_id": self.client_key,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                },
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"Token error {response.status_code}: {response.text}")

            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info(f"Token generated (expires in {expires_in}s)")
            return self.access_token

        except Exception as e:
            logger.error(f"Token error: {str(e)}")
            raise

    def ensure_token(self) -> str:
        """Refresh token if expired"""
        if not self.access_token or datetime.now() >= self.token_expiry:
            self.get_token()
        return self.access_token

    def _headers(self) -> Dict[str, str]:
        """Get auth headers"""
        token = self.ensure_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def upload_file(self, file_path: str) -> str:
        """Upload PDF file to Lulu"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                token = self.ensure_token()
                headers = {"Authorization": f"Bearer {token}"}

                response = self.session.post(
                    f"{self.base_url}/files/",
                    headers=headers,
                    files=files,
                    timeout=30
                )

            if response.status_code not in [200, 201]:
                raise Exception(f"Upload error {response.status_code}")

            file_id = response.json().get("id")
            logger.info(f"File uploaded: {file_path} -> {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise

    def create_print_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create print job (submit order)"""
        try:
            response = self.session.post(
                f"{self.base_url}/print-jobs/",
                headers=self._headers(),
                json=job_data,
                timeout=30
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Job error {response.status_code}")

            job = response.json()
            logger.info(f"Job created: {job.get('id')}")
            return job

        except Exception as e:
            logger.error(f"Job creation failed: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get print job status"""
        try:
            response = self.session.get(
                f"{self.base_url}/print-jobs/{job_id}/",
                headers=self._headers(),
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"Status error {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            raise

    def list_print_jobs(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """List print jobs with pagination"""
        try:
            response = self.session.get(
                f"{self.base_url}/print-jobs/",
                headers=self._headers(),
                params={"limit": limit, "offset": offset},
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"List error {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"List failed: {str(e)}")
            raise
