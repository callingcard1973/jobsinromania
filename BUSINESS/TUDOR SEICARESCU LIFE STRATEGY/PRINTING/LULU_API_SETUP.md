# Lulu API Setup Guide

## Getting API Credentials (5 minutes)

### Step 1: Create Developer Account

1. Go to **https://developers.lulu.com/**
2. Create free account (email + password)
3. Verify email address

### Step 2: Generate API Keys

1. Log in to https://developers.lulu.com/
2. Navigate to **User Profile → API Keys**
3. Click **"Generate New Keys"**
4. You will receive:
   - **client_key** (public identifier)
   - **client_secret** (keep secret, like password)

### Step 3: Save Credentials

Store in `.env` file:
```
LULU_CLIENT_KEY=your_client_key_here
LULU_CLIENT_SECRET=your_client_secret_here
LULU_API_BASE=https://api.lulu.com/v1
```

---

## Sandbox vs Production

### Development (Sandbox)

- **URL:** https://developers.sandbox.lulu.com/
- **API Endpoint:** https://api.sandbox.lulu.com/v1
- **Purpose:** Testing without real money
- **Registration:** Separate account (free)

### Production (Live)

- **URL:** https://developers.lulu.com/
- **API Endpoint:** https://api.lulu.com/v1
- **Purpose:** Real print jobs + shipping
- **Account:** Same as sandbox, just switch endpoint

---

## Authentication Flow

### 1. Get Access Token

**POST** `/auth/realms/glasstree/protocol/openid-connect/token`

```bash
curl -X POST https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id={client_key}" \
  -d "client_secret={client_secret}" \
  -d "grant_type=client_credentials"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI...",
  "expires_in": 300,
  "token_type": "Bearer"
}
```

Token expires in 5 minutes (300 seconds). Request new one when needed.

### 2. Use Token in API Calls

**All future requests include:**
```
Authorization: Bearer {access_token}
```

Example:
```bash
curl -X GET https://api.lulu.com/v1/products/ \
  -H "Authorization: Bearer {access_token}"
```

---

## Core API Endpoints

### Get Available Products
```
GET /v1/products/
```
Returns book formats, sizes, binding options

### Upload Files
```
POST /v1/files/
Content: PDF (cover + interior)
```
Returns file ID for use in print jobs

### Create Print Job
```
POST /v1/print-jobs/
```
Submits order for printing + shipping

### Track Order Status
```
GET /v1/print-jobs/{job_id}/
```
Returns current status (processing, printing, shipped, etc.)

---

## Python Implementation

```python
import requests
import json
from datetime import datetime, timedelta

class LuluAPI:
    def __init__(self, client_key, client_secret, sandbox=False):
        self.client_key = client_key
        self.client_secret = client_secret
        
        if sandbox:
            self.base_url = "https://api.sandbox.lulu.com"
            self.token_url = "https://api.sandbox.lulu.com/auth/realms/glasstree/protocol/openid-connect/token"
        else:
            self.base_url = "https://api.lulu.com"
            self.token_url = "https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token"
        
        self.access_token = None
        self.token_expiry = None
    
    def get_token(self):
        """Get OAuth 2.0 access token"""
        response = requests.post(
            self.token_url,
            data={
                "client_id": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
            return self.access_token
        else:
            raise Exception(f"Token error: {response.text}")
    
    def ensure_token(self):
        """Refresh token if expired"""
        if not self.access_token or datetime.now() >= self.token_expiry:
            self.get_token()
    
    def get_headers(self):
        """Return headers with auth token"""
        self.ensure_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_products(self):
        """Get available product packages (book sizes, formats)"""
        response = requests.get(
            f"{self.base_url}/products/",
            headers=self.get_headers()
        )
        return response.json()
    
    def upload_file(self, file_path):
        """Upload PDF file"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/files/",
                headers={"Authorization": f"Bearer {self.access_token}"},
                files=files
            )
        return response.json()
    
    def create_print_job(self, job_data):
        """Create print job (book order)"""
        response = requests.post(
            f"{self.base_url}/print-jobs/",
            headers=self.get_headers(),
            json=job_data
        )
        return response.json()
    
    def get_print_job(self, job_id):
        """Get print job status"""
        response = requests.get(
            f"{self.base_url}/print-jobs/{job_id}/",
            headers=self.get_headers()
        )
        return response.json()
```

### Usage Example

```python
# Initialize
api = LuluAPI(
    client_key="your_client_key",
    client_secret="your_client_secret",
    sandbox=True  # Set to False for production
)

# Create print job
job = api.create_print_job({
    "line_items": [
        {
            "cover_file_id": "cover_file_123",
            "interior_file_id": "interior_file_456",
            "quantity": 10,
            "product_id": "3x5_booklet"  # Check get_products() for options
        }
    ],
    "shipping_address": {
        "name": "John Doe",
        "street1": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "postcode": "12345",
        "country_code": "US"
    }
})

print(f"Print job created: {job['id']}")

# Track status
status = api.get_print_job(job['id'])
print(f"Status: {status['status']}")  # processing, printing, shipped, etc.
```

---

## Key Points

| Item | Details |
|------|---------|
| **Registration** | Free on https://developers.lulu.com/ |
| **Credentials** | client_key + client_secret (API Keys page) |
| **Token expiry** | 5 minutes (refresh automatically) |
| **Sandbox** | Separate endpoint, same keys structure |
| **Cost** | Zero API fees (pay only for print jobs) |
| **Support** | Limited (code examples on GitHub) |

---

## Resources

- [Lulu API Docs](https://api.lulu.com/docs/)
- [Lulu Developer Portal](https://developers.lulu.com/)
- [API Getting Started Guide (PDF)](https://help.api.lulu.com/en/support/solutions/articles/64000294079-how-do-i-get-started-)
- [GitHub API Client Examples](https://github.com/minireference/lulu-api-client)

---

## Next Steps (for Tudor Printing House MVP)

1. **Register:** Create account on https://developers.lulu.com/
2. **Get keys:** Generate client_key + client_secret
3. **Save:** Add to `.env` file
4. **Test:** Run Python code above against sandbox endpoint
5. **Create print job:** Test full flow (file upload → print → track)
6. **Scale:** Switch to production endpoint when ready

**Time to first API call:** 10 minutes
