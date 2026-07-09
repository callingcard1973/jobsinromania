# DROID VERIFICATION FIX PLAN

## CRITICAL ISSUES (APP WON'T START)

### [C1] JWT Exception Import Error - FIXED
**Problem**: `JWTExpiredSignatureError` doesn't exist in python-jose
**Status**: ✅ Already tested - correct exception is `ExpiredSignatureError`
**Fix Required**: Update import in `backend/app/core/security.py`

```python
# Current (broken):
from jose.exceptions import JWTExpiredSignatureError

# Fixed:
from jose.exceptions import ExpiredSignatureError
```

### [C2] SECRET_KEY Validation Error - CRITICAL
**Problem**: `.env` has placeholder key that fails validation
**Current Value**: `SECRET_KEY=your-secret-key-change-in-production`
**Validation Rule**: Must be >= 32 characters and not the placeholder
**Fix Required**: Generate real secret key in `.env`

```bash
# Generate secure secret key:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

## HIGH PRIORITY ISSUES

### [H1] Optional Authentication Always Returns None - CRITICAL
**Problem**: `Depends(lambda: None)` always returns None, breaking moderator access
**Location**: `backend/app/api/routes/ads.py` line 43
**Impact**: Moderators can't see non-published ads, owners can't see their drafts

**Fix Required**: Implement proper optional auth dependency
```python
# Current (broken):
current_user: Optional[User] = Depends(lambda: None)

# Fixed:
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload:
            user_id = int(payload.get("sub"))
            return db.query(User).filter(User.id == user_id).first()
    return None
```

### [H2] Status Filter Conflict for Public Users
**Problem**: Public users forced to see only published, then status filter applied
**Impact**: Confusing results for public users
**Fix Required**: Remove forced published filter when status parameter provided

### [H3] Rejected Ads Cannot Be Resubmitted
**Problem**: Only draft ads can be submitted
**Fix Required**: Allow both `DRAFT` and `REJECTED` status to submit

## MEDIUM PRIORITY ISSUES

### [M1] CORS Misconfiguration
**Problem**: `allow_origins=["*"]` with `allow_credentials=True` is invalid
**Fix Required**: Set specific origins or remove credentials

### [M2] Requirements.txt Not Pinned
**Problem**: Version numbers cause compatibility issues
**Fix Required**: Pin exact versions used during testing

### [M3] SQLite Database Committed
**Problem**: Development database in source tree
**Fix Required**: Add to .gitignore and remove from repo

## LOW PRIORITY ISSUES

### [L1] JWT Subject Type Coercion
**Problem**: String comparison with integer IDs
**Fix Required**: Explicitly cast to int: `user_id = int(payload.get("sub"))`

### [L2] Upload Size Validation Bypass
**Problem**: Client-side size check can be bypassed
**Fix Required**: Validate actual file content length

### [L3] Thumbnail Errors Silently Swallowed
**Problem**: `except Exception: pass` hides errors
**Fix Required**: Log errors and inform user

### [L4] Inconsistent Import Style
**Problem**: Mix of absolute and relative imports
**Fix Required**: Standardize to absolute imports

## RECOMMENDED FIX ORDER

### Phase 1: Make App Boot (Critical)
1. Fix SECRET_KEY in `.env`
2. Fix JWT exception import in `security.py`
3. Test app starts: `python run.py`

### Phase 2: Fix Core Functionality (High)
4. Implement proper optional auth dependency
5. Fix rejected ad resubmission
6. Fix status filter conflict

### Phase 3: Security & Quality (Medium)
7. Fix CORS configuration
8. Pin requirements.txt versions
9. Remove database from git tracking

### Phase 4: Robustness (Low)
10. Fix JWT subject type coercion
11. Improve upload validation
12. Add error logging for thumbnails
13. Standardize imports

## TESTING AFTER EACH FIX

After each fix, run:
```bash
cd backend
python run.py
# Test basic functionality
curl http://localhost:8000/health
```

## ESTIMATED TIME

- **Phase 1**: 5 minutes (critical fixes)
- **Phase 2**: 15 minutes (core functionality)
- **Phase 3**: 10 minutes (security)
- **Phase 4**: 15 minutes (robustness)

**Total**: ~45 minutes to fix all issues