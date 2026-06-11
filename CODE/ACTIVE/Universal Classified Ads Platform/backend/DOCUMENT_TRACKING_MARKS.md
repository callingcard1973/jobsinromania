# PostHog Document Tracking Marks

Comprehensive tracking for all document operations (ads, users, media, messages, reviews).

## Overview

Every document in the system gets a unique tracking mark that follows the format:
```
doc_{document_type}_{document_id}_{action}
```

Examples:
- `doc_ad_12345_view` — Ad 12345 viewed
- `doc_ad_12345_contact` — Contact button clicked for ad 12345
- `doc_ad_12346_created` — New ad 12346 created
- `doc_user_789_profile_viewed` — User 789's profile viewed

## Document Types

| Type | Code | Tracked Events |
|------|------|----------------|
| Ad | `ad` | created, viewed, clicked, edited, deleted, contact, shared, flagged, published, archived |
| User | `user` | registered, profile_viewed, profile_edited, followed, unfollowed |
| Media | `media` | uploaded, viewed, deleted, shared |
| Message | `message` | sent, viewed, deleted, replied |
| Review | `review` | created, viewed, helpful, flagged, deleted |

## Backend Implementation

### Python - Document Tracker Class

```python
from app.core.document_tracking import DocumentTracker

# Track ad creation
DocumentTracker.mark_document_created('ad', doc_id=12345, user_id='user123', properties={
    'category': 'vehicles',
    'price': 5000,
    'location': 'NYC',
})

# Track ad view
DocumentTracker.mark_document_viewed('ad', doc_id=12345, user_id='user456', properties={
    'referrer': 'search',
})

# Track ad edit
DocumentTracker.mark_document_edited('ad', doc_id=12345, user_id='user123', properties={
    'fields_changed': ['price', 'description'],
})

# Track ad delete
DocumentTracker.mark_document_deleted('ad', doc_id=12345, user_id='user123')

# Track ad share
DocumentTracker.mark_document_shared('ad', doc_id=12345, user_id='user123', shared_with='facebook')

# Track ad publish
DocumentTracker.mark_document_published('ad', doc_id=12345, user_id='user123')

# Track ad archive
DocumentTracker.mark_document_archived('ad', doc_id=12345, user_id='user123')

# Track document search
DocumentTracker.mark_document_searched('honda civic', doc_type='ad', results_count=42, user_id='user456')

# Track document filter
DocumentTracker.mark_document_filtered('ad', doc_type='ad', filters={
    'category': 'vehicles',
    'price_max': 5000,
}, results_count=15, user_id='user456')

# Track custom interaction
DocumentTracker.mark_document_interaction('ad', doc_id=12345, interaction_type='contact', user_id='user456')

# Get mark identifier
mark = DocumentTracker.get_document_mark('ad', 12345, 'view')
# Returns: 'doc_ad_12345_view'
```

## Frontend Implementation

### HTML - Add Tracking Marks

```html
<!-- Document with tracking marks -->
<div class="ad-card"
     data-posthog-mark="doc_ad_12345_view"
     data-doc-type="ad"
     data-doc-id="12345"
     data-action="viewed"
     data-prop-category="vehicles"
     data-prop-price="5000">
    
    <h2>
        <a href="/ads/12345"
           data-posthog-mark="doc_ad_12345_click"
           data-doc-type="ad"
           data-doc-id="12345"
           data-action="clicked">
            2020 Honda Civic
        </a>
    </h2>

    <button class="contact-btn"
            data-posthog-mark="doc_ad_12345_contact"
            data-doc-type="ad"
            data-doc-id="12345"
            data-action="contact">
        Contact Seller
    </button>
</div>

<!-- Form with tracking -->
<form class="create-ad-form"
      data-posthog-doc-type="ad"
      data-action="created">
    
    <input type="text" name="title" data-posthog-mark="form_field_title">
    <input type="number" name="price" data-posthog-mark="form_field_price">
    <button type="submit" data-posthog-mark="form_submit_ad">Create Ad</button>
</form>
```

### JavaScript - Track with DocumentTracker

```javascript
// Initialize tracker (auto-initializes if analytics is loaded)
const tracker = window.documentTracker;

// Track document view
tracker.trackDocumentView('ad', 12345, { category: 'vehicles' });

// Track document creation
tracker.trackDocumentCreated('ad', 12346, { category: 'vehicles' });

// Track document edit
tracker.trackDocumentEdited('ad', 12345, { fields_changed: ['price'] });

// Track document delete
tracker.trackDocumentDeleted('ad', 12345);

// Track search
tracker.trackDocumentSearch('ad', 'honda civic', 42);

// Track filters
tracker.trackDocumentFilter('ad', { category: 'vehicles', price_max: 5000 }, 15);
```

## Automatic Tracking

These are automatically tracked by the middleware:

1. **All HTTP requests** — Method, path, status, duration
2. **Page views** — When user navigates
3. **Form submissions** — Form name + field values
4. **Element clicks** — Elements with `data-posthog-mark` attribute
5. **Document visibility** — When document enters viewport (Intersection Observer)
6. **Errors** — Uncaught errors + explicit error tracking
7. **Navigation** — History changes

## Events Generated

When you mark a document, PostHog generates these events:

### Ad Events
```
document_ad_created
document_ad_viewed
document_ad_clicked
document_ad_edited
document_ad_deleted
document_ad_contact
document_ad_shared
document_ad_published
document_ad_archived
document_ad_search
document_ad_filter
document_ad_visible_in_viewport
```

### Event Properties
Each event includes:
- `document_mark` — Unique identifier (e.g., `doc_ad_12345_view`)
- `document_type` — Type (ad, user, media, message, review)
- `document_id` — ID of the document
- `action` — Action performed (viewed, created, etc.)
- `timestamp` — ISO 8601 timestamp
- Custom properties from `data-prop-*` attributes

## PostHog Funnels

Use document marks to create funnels:

```
1. Ad viewed (document_ad_viewed)
2. Contact button clicked (document_ad_contact)
3. Message sent to seller (document_message_sent)
4. Transaction completed (document_transaction_completed)
```

## PostHog Dashboards

Create dashboards tracking:
- **Document Lifecycle**: created → viewed → edited/archived
- **Search Performance**: search queries → click-through rate
- **User Engagement**: views → contacts → messages → transactions
- **Document Quality**: created → views → contacts (engagement score)

## Performance

- Marks are **non-blocking** async calls
- **Zero overhead** for unmarked documents
- Local **offline queue** if network fails
- **Batched** network requests (every 30s)

## Best Practices

1. **Mark every document action** — Views, creates, edits, deletes
2. **Use consistent naming** — `doc_{type}_{id}_{action}`
3. **Add custom properties** — Category, price, location, etc.
4. **Track user context** — Include user_id for auth operations
5. **Mark forms** — Include field names for analysis
6. **Use data attributes** — `data-posthog-mark` for automatic tracking

## Example: Complete Ad Lifecycle

```html
<!-- Ad card with all tracking marks -->
<div class="ad-card" data-posthog-mark="doc_ad_12345_view" data-doc-type="ad" data-doc-id="12345" data-action="viewed" data-prop-category="vehicles" data-prop-price="5000">
    <h2><a href="/ads/12345" data-posthog-mark="doc_ad_12345_click" data-doc-type="ad" data-doc-id="12345" data-action="clicked">2020 Honda Civic</a></h2>
    <p>$5,000</p>
    
    <button class="contact-btn" data-posthog-mark="doc_ad_12345_contact" data-doc-type="ad" data-doc-id="12345" data-action="contact">Contact</button>
    <button class="share-btn" data-posthog-mark="doc_ad_12345_share" data-doc-type="ad" data-doc-id="12345" data-action="shared">Share</button>
    <button class="flag-btn" data-posthog-mark="doc_ad_12345_flag" data-doc-type="ad" data-doc-id="12345" data-action="flagged">Flag</button>
</div>
```

Backend logs these marks:
```python
# View
DocumentTracker.mark_document_viewed('ad', 12345, 'user456')

# Contact
DocumentTracker.mark_document_interaction('ad', 12345, 'contact', 'user456')

# Share
DocumentTracker.mark_document_shared('ad', 12345, 'user456', 'facebook')

# Delete (when owner deletes ad)
DocumentTracker.mark_document_deleted('ad', 12345, 'user123')
```

## Debugging

Enable PostHog logging to see marks:
```javascript
posthog.config.debug = true;

// Check local queue
JSON.parse(localStorage.getItem('analytics_queue')).forEach(e => console.log(e.event));
```

View marks in PostHog UI → Events → Filter by mark name.
