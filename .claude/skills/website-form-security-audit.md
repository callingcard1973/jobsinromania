---
name: website-form-security-audit
description: Comprehensive security audit + fix + test + deploy pipeline for contact/submission forms across any website. CSRF, rate limiting, input sanitization. 5-step process (audit→code→sandbox→verify→produce). ~10 hours per site.
type: skill
---

# Website Form Security Audit & Deployment

For any website with a contact/submission form, run this 5-step pipeline to fix security vulnerabilities and safely deploy to production.

## When to Use

- Website has contact/submission form
- No CSRF protection
- Weak input sanitization (strip_tags instead of htmlspecialchars)
- No rate limiting on form endpoint
- No client-side validation

## 5-Step Process

### Step 1: Audit (4 hours)

**Find the form endpoint**:
1. Locate form HTML (contact, audit, quotation, etc.)
2. Find form action: `<form action="send_email.php" method="POST">`
3. Read the handler file (send_email.php)
4. Identify security gaps

**Security checklist**:
- ❌ CSRF token validation?
- ❌ Input sanitization (htmlspecialchars vs strip_tags)?
- ❌ Email validation (filter_var)?
- ❌ Phone validation (regex)?
- ❌ Rate limiting (session throttle)?
- ❌ Client-side validation (JavaScript)?
- ❌ Error handling (try/catch)?

**Document findings**:
Create AUDIT_REPORT_YYYY-MM-DD.md with:
- List of 18+ issues (critical, high, medium, low)
- Fixes needed
- Timeline (hours per issue)
- Success criteria

### Step 2: Code (2 hours)

Create 3 files:

**1. send_offer_secure.php (5-6 KB)**

```php
<?php
session_start();

// === CSRF TOKEN GENERATION ===
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    header('Content-Type: application/json');
    echo json_encode(['csrf_token' => $_SESSION['csrf_token']]);
    exit;
}

// === RATE LIMITING ===
if (isset($_SESSION['last_form_submit'])) {
    $elapsed = time() - $_SESSION['last_form_submit'];
    if ($elapsed < 10) {
        http_response_code(429);
        header('Content-Type: application/json');
        echo json_encode(['ok' => false, 'error' => 'Prea repede. Așteptă ' . (10 - $elapsed) . ' secunde.']);
        exit;
    }
}

// === CSRF VERIFICATION ===
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (empty($_POST['csrf_token']) || $_POST['csrf_token'] !== $_SESSION['csrf_token']) {
        http_response_code(403);
        header('Content-Type: application/json');
        echo json_encode(['ok' => false, 'error' => 'Token de siguranță expirat.']);
        exit;
    }
    $_SESSION['last_form_submit'] = time();
}

// === INPUT SANITIZATION ===
$name = htmlspecialchars($_POST['name'] ?? '', ENT_QUOTES, 'UTF-8');
$email = htmlspecialchars($_POST['email'] ?? '', ENT_QUOTES, 'UTF-8');
$phone = htmlspecialchars($_POST['phone'] ?? '', ENT_QUOTES, 'UTF-8');
$message = htmlspecialchars($_POST['message'] ?? '', ENT_QUOTES, 'UTF-8');

// === VALIDATION ===
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    header('Content-Type: application/json');
    echo json_encode(['ok' => false, 'error' => 'Email invalid']);
    exit;
}

// === EMAIL SENDING ===
$to = 'cereredeoferta@hyperbndf.com';  // Change to your email
$subject = "Cerere Audit: $name";
$headers = "From: noreply@" . $_SERVER['HTTP_HOST'] . "\r\nReply-To: $email\r\nContent-Type: text/plain; charset=UTF-8";
$body = "Nume: $name\nEmail: $email\nTelefon: $phone\nMesaj:\n$message";

mail($to, $subject, $body, $headers);

header('Content-Type: application/json');
echo json_encode(['ok' => true, 'message' => 'Cerere trimisă!']);
exit;
?>
```

**2. form_handler.js (8-10 KB)**

```javascript
class FormValidator {
  constructor(form) {
    this.form = form;
    this.errors = {};
  }

  validate() {
    this.errors = {};
    const formData = new FormData(this.form);

    // Validate name
    const name = formData.get('name')?.trim();
    if (!name) {
      this.errors.name = 'Nume obligatoriu';
    } else if (name.length < 2 || name.length > 100) {
      this.errors.name = 'Nume: 2-100 caractere';
    }

    // Validate email
    const email = formData.get('email')?.trim();
    if (!email) {
      this.errors.email = 'Email obligatoriu';
    } else if (!this.isValidEmail(email)) {
      this.errors.email = 'Email invalid';
    }

    // Validate phone
    const phone = formData.get('phone')?.trim();
    if (!phone) {
      this.errors.phone = 'Telefon obligatoriu';
    } else if (!this.isValidPhone(phone)) {
      this.errors.phone = 'Telefon invalid (ex: +40123456789)';
    }

    return Object.keys(this.errors).length === 0;
  }

  isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  isValidPhone(phone) {
    const cleaned = phone.replace(/[^\d+]/g, '');
    return /^(\+40|0)[0-9]{9}$/.test(cleaned);
  }

  displayErrors() {
    Object.keys(this.errors).forEach(field => {
      const errorEl = this.form.querySelector(`[data-error="${field}"]`);
      if (errorEl) {
        errorEl.textContent = this.errors[field];
        errorEl.style.display = 'block';
      }
    });
  }
}

class SecureFormSubmitter {
  constructor(form, options = {}) {
    this.form = form;
    this.validator = new FormValidator(form);
    this.timeout = options.timeout || 5000;
    this.csrfToken = null;
    this.init();
  }

  async init() {
    try {
      const resp = await fetch(this.form.action);
      const json = await resp.json();
      this.csrfToken = json.csrf_token;
    } catch (error) {
      console.error('Failed to load CSRF token', error);
    }

    this.form.addEventListener('submit', (e) => this.handleSubmit(e));
  }

  async handleSubmit(event) {
    event.preventDefault();

    if (!this.validator.validate()) {
      this.validator.displayErrors();
      return;
    }

    const button = this.form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Se trimite...';

    try {
      const formData = new FormData(this.form);
      formData.append('csrf_token', this.csrfToken);

      const resp = await fetch(this.form.action, {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(this.timeout)
      });

      const json = await resp.json();

      if (resp.ok && json.ok) {
        const successEl = this.form.querySelector('[data-form-success]');
        if (successEl) {
          successEl.textContent = json.message || 'Cerere trimisă!';
          successEl.style.display = 'block';
        }
        this.form.reset();
        setTimeout(() => {
          button.disabled = false;
          button.textContent = 'Trimite';
        }, 3000);
      } else {
        this.displayError(json.error || 'Eroare la submitere');
        button.disabled = false;
        button.textContent = 'Trimite';
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        this.displayError('Cererea a durat prea mult. Încearcă din nou.');
      } else {
        this.displayError('Eroare rețea: Verifică conexiunea la internet...');
      }
      button.disabled = false;
      button.textContent = 'Trimite';
    }
  }

  displayError(message) {
    const errorEl = this.form.querySelector('[data-form-error]');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  }
}

// Usage: new SecureFormSubmitter(form)
```

**3. form_validation.css (3-4 KB)**

```css
/* Form Container */
form[data-secure-form] {
  max-width: 500px;
  margin: 2rem auto;
  padding: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fff;
}

/* Input Fields */
input[data-field],
textarea[data-field] {
  width: 100%;
  padding: 0.75rem;
  margin: 0.5rem 0;
  border: 2px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

input[data-field]:focus,
textarea[data-field]:focus {
  outline: none;
  border-color: #1a5c2a;
}

/* Error State */
input[data-field].error,
textarea[data-field].error {
  border-color: #e53935;
  background-color: rgba(229, 57, 53, 0.05);
}

/* Error Messages */
[data-error] {
  display: none;
  color: #e53935;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  animation: slideDown 0.2s ease;
}

/* Success Message */
[data-form-success] {
  display: none;
  padding: 1rem;
  margin: 1rem 0;
  background: rgba(26, 92, 42, 0.1);
  color: #1a5c2a;
  border-left: 4px solid #1a5c2a;
  border-radius: 4px;
  animation: success-pop 0.4s ease;
}

/* Button States */
button[type="submit"] {
  width: 100%;
  padding: 0.75rem;
  background: #1a5c2a;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

button[type="submit"]:hover:not(:disabled) {
  opacity: 0.9;
}

button[type="submit"]:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Animations */
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes success-pop {
  from { opacity: 0; scale: 0.95; }
  to { opacity: 1; scale: 1; }
}

/* Responsive */
@media (max-width: 768px) {
  form[data-secure-form] {
    padding: 1rem;
  }
  input[data-field],
  textarea[data-field] {
    font-size: 16px; /* Prevent zoom on iOS */
  }
}
```

### Step 3: Sandbox Setup (1 hour)

1. Create directory: SANDBOX/www/
2. Copy files: send_offer.php, js/form_handler.js, css/form_validation.css
3. Create test form: index_secure.html (with data-secure-form attributes)
4. Document: deployment guides for all 5 steps

### Step 4: Verify Tests (30 minutes)

Run 7 tests on sandbox:

```markdown
1. ✅ Form Validation — empty field → red error
2. ✅ Email Validation — invalid format → rejected
3. ✅ Phone Validation — non-format → rejected
4. ✅ Successful Submission — valid form → email sent, green message
5. ✅ Rate Limiting — rapid submit → blocked, error shown
6. ✅ Network Error — offline → friendly error message
7. ✅ CSRF Token — present in Network tab POST payload
```

If all 7 PASS → proceed to Step 5 (production).

### Step 5: Produce (30 minutes)

1. **Backup** — Save original files
2. **Upload** — Replace old handler with secure version
3. **Update HTML** — Add script/link tags for JS/CSS
4. **Test** — Same 7 tests on production
5. **Monitor** — Check logs for 24 hours
6. **Announce** — Email stakeholders

## Applied To

- ✅ hyperbndf.com (2026-04-27, Step 2 in progress)

## For Next Sites

Apply this skill to:
1. cumparlegume.com (existing contact form)
2. agroevolution.com (catalog forms)
3. All 15 job sites (apply/inquiry forms)
4. All WordPress sites (contact forms)

## Time Estimate

**Per site**: ~10 hours (4h audit, 2h code, 1h sandbox, 1h verify, 2h docs + deployment)

**For all 34 sites**: ~340 hours (spread across phases)

## Success Criteria

- ✅ 7/7 tests PASS
- ✅ 0 console errors
- ✅ 0 server errors
- ✅ CSRF token verified in Network tab
- ✅ Rate limiting prevents rapid submissions
- ✅ Emails received
- ✅ Mobile responsive
- ✅ No data breaches

## Files Location

Each site gets:
```
WEBSITE_NAME/
├── AUDIT_REPORT_YYYY-MM-DD.md
├── CODE/
│   ├── send_offer_secure.php
│   ├── form_handler.js
│   └── form_validation.css
├── SANDBOX/
│   ├── www/ (deployment-ready)
│   ├── 1_MANUAL_TEST.sh
│   ├── 2_DEPLOY_SANDBOX.md
│   ├── 3_RUN_TESTS.md
│   ├── 4_DEPLOY_PRODUCTION.md
│   ├── 5_COMPLETION.md
│   └── TEST_RESULTS_YYYY-MM-DD.md
└── .planning/
    └── AUDIT_FIXES_YYYY-MM-DD.md (4-phase roadmap)
```

## References

- HYPER BNDF example: `D:\MEMORY\BUSINESS\PERSONAL\BOGDAN GAVRA\HYPER BNDF\`
- Memory: `hyper_bndf_phase1_deployment.md`
