# PostHog Analytics Integration

Comprehensive analytics tracking for the Universal Classified Ads Platform.

## Setup

### 1. Get PostHog API Key

1. Create account at https://posthog.com
2. Copy your project API key (starts with `phc_`)
3. Add to `.env`:
   ```
   POSTHOG_API_KEY=phc_your_key_here
   POSTHOG_ENABLED=true
   ```

### 2. Backend Setup

PostHog analytics are automatically tracked via:

#### API Middleware
- Tracks all API requests: method, path, status, duration
- Automatically captures user_id if authenticated

#### Event Tracking
Use the Analytics class for custom events:

```python
from app.core.analytics import Analytics

# Track authentication events
Analytics.track_auth(user_id, "login_success", {"provider": "email"})
Analytics.track_auth(user_id, "logout", {})

# Track ad events
Analytics.track_ad_event(user_id, "ad_created", ad_id=123, {"category": "vehicles"})
Analytics.track_ad_event(user_id, "ad_viewed", ad_id=123)

# Track user actions
Analytics.track_user_action(user_id, "search", {"query": "car", "results": 45})

# Track errors
Analytics.track_error(user_id, "database_error", "Connection failed")

# Identify user with traits
Analytics.identify(user_id, {"email": "user@example.com", "plan": "free"})
```

### 3. Frontend Setup

Include in HTML templates:
```html
<script src="/static/js/analytics.js"></script>
<script>
  const analytics = new Analytics('{{ posthog_api_key }}');
</script>
```

#### Track Events (JavaScript)
```javascript
// Page views (automatic)
analytics.trackPageView('/ads');

// Auth events
analytics.trackAuth('login_attempt', { method: 'email' });
analytics.trackAuth('register_success', { plan: 'free' });

// Ad events
analytics.trackAdEvent('create', 123, { category: 'vehicles', price: 5000 });
analytics.trackAdEvent('view', 123, { duration: 30 });

// User actions
analytics.trackUserAction('search_ads', { query: 'car', filters: 3 });
analytics.trackUserAction('contact_seller', { ad_id: 123 });

// Errors
analytics.trackError(new Error('API failed'), 'api_error');

// Form submissions
analytics.trackFormSubmit('contact_form', { ad_id: 123 });

// Identify user
analytics.identify('user123', { email: 'user@example.com', name: 'John' });
```

## Events Tracked

### Authentication
- `auth_login_success` - Successful login
- `auth_login_failed` - Failed login attempt
- `auth_register` - User registration
- `auth_logout` - User logout
- `auth_password_reset` - Password reset attempt

### Ads
- `ad_create` - Ad created
- `ad_view` - Ad viewed
- `ad_edit` - Ad edited
- `ad_delete` - Ad deleted
- `ad_contact` - User contacted seller
- `ad_flag` - Ad flagged as inappropriate

### Pages
- `page_view` - Page viewed (automatic)
- Page: `home`, `ads`, `login`, `register`, `create_ad`, etc.

### API
- `api_request_GET`, `api_request_POST`, etc.
- Properties: `method`, `path`, `status`, `duration_ms`

### Errors
- `error` - Any error occurred
- Properties: `error_type`, `error_message`

### User Actions
- `search_ads` - Ad search performed
- `filter_ads` - Filters applied
- `sort_ads` - Ads sorted
- `contact_seller` - Seller contacted

## Dashboard Setup (PostHog UI)

### Funnels
1. Login → View Ads → Contact Seller
2. Register → Create Ad → Get Contacts

### Retention
- Daily active users
- Users viewing ads
- Users creating ads

### Cohorts
- New users (last 7 days)
- Active sellers
- Power users (10+ searches/week)

### Dashboards
- Real-time activity
- User engagement
- Ad performance
- Error tracking

## Privacy & GDPR

- PostHog hosted in EU (use `https://eu.posthog.com` for GDPR compliance)
- User IP auto-stripped in PostHog
- Set `POSTHOG_ENABLED=false` to disable tracking

## Performance

- Async event tracking (non-blocking)
- Batched network requests
- Local queue if offline (frontend)
- Minimal overhead (<5ms per request)

## Debugging

Enable PostHog logging:
```javascript
posthog.config.debug = true;
```

Check events in PostHog UI → Toolbar → Events

## Deployment

1. Set `POSTHOG_API_KEY` in production `.env`
2. Set `POSTHOG_ENABLED=true`
3. Deploy code changes
4. Verify events arriving in PostHog dashboard

Events will start flowing immediately.
