// PostHog Analytics Integration
class Analytics {
  constructor(apiKey = '', options = {}) {
    this.apiKey = apiKey || localStorage.getItem('posthog_api_key') || '';
    this.host = options.host || 'https://us.posthog.com';
    this.enabled = options.enabled !== false;
    this.userId = localStorage.getItem('user_id') || null;
    this.sessionId = this.getOrCreateSessionId();

    if (this.apiKey && this.enabled) {
      this.initPostHog();
    }
  }

  initPostHog() {
    if (window.posthog) return;

    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=this.host+"/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.capture=function(){u.push(["capture"].concat(Array.prototype.slice.call(arguments,0)))},u.capturePageView=function(){u.push(["capturePageView"].concat(Array.prototype.slice.call(arguments,0)))},u.identify=function(){u.push(["identify"].concat(Array.prototype.slice.call(arguments,0)))},u.setPersonProperties=function(){u.push(["setPersonProperties"].concat(Array.prototype.slice.call(arguments,0)))},u.reset=function(){u.push(["reset"])},o=["capture","capturePageView","identify","setPersonProperties","reset"],n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

    posthog.init(this.apiKey, {
      api_host: this.host,
      capture_pageview: true,
      capture_pageleave: true,
    });
  }

  getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('session_id');
    if (!sessionId) {
      sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
      sessionStorage.setItem('session_id', sessionId);
    }
    return sessionId;
  }

  // GDPR: PII (email/name) only reaches PostHog after explicit consent.
  // Honors a generic opt-in cookie and Complianz's statistics category.
  hasConsent() {
    const c = document.cookie || '';
    return /(?:^|;\s*)ph_consent=1\b/.test(c) || /(?:^|;\s*)cmplz_statistics=allow\b/.test(c);
  }

  identify(userId, traits = {}) {
    this.userId = userId;
    localStorage.setItem('user_id', userId);
    if (window.posthog && this.hasConsent()) {
      posthog.identify(String(userId), { ...traits, session_id: this.sessionId });
    }
  }

  reset() {
    this.userId = null;
    localStorage.removeItem('user_id');
    if (window.posthog) posthog.reset();
  }

  // Minimal consent bar for static/non-WP pages (WP uses Complianz instead).
  maybeShowConsentBanner() {
    const decided = /(?:^|;\s*)ph_consent=[01]\b/.test(document.cookie || '');
    if (decided || document.getElementById('ph-consent-bar')) return;
    const set = (v) => {
      document.cookie = 'ph_consent=' + v + ';path=/;max-age=31536000;SameSite=Lax';
      const b = document.getElementById('ph-consent-bar'); if (b) b.remove();
      if (v === '1' && this.userId) this.identify(this.userId);
    };
    const bar = document.createElement('div');
    bar.id = 'ph-consent-bar';
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#0f2942;color:#fff;padding:12px 16px;font:14px/1.4 -apple-system,Segoe UI,Roboto,Arial,sans-serif;display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap';
    bar.innerHTML = '<span>We use analytics to improve this service. Allow analytics cookies?</span>' +
      '<button id="ph-acc" style="background:#f5a000;color:#fff;border:0;padding:8px 18px;border-radius:5px;font-weight:700;cursor:pointer">Allow</button>' +
      '<button id="ph-dec" style="background:transparent;color:#fff;border:1px solid #fff;padding:8px 18px;border-radius:5px;cursor:pointer">Decline</button>';
    document.body.appendChild(bar);
    bar.querySelector('#ph-acc').addEventListener('click', () => set('1'));
    bar.querySelector('#ph-dec').addEventListener('click', () => set('0'));
  }

  trackEvent(event, properties = {}) {
    const eventProperties = {
      ...properties,
      session_id: this.sessionId,
      timestamp: new Date().toISOString(),
    };
    if (window.posthog) {
      posthog.capture(event, eventProperties);
    } else {
      this.queueEvent(event, eventProperties);
    }
  }

  trackPageView(page, properties = {}) {
    this.trackEvent('page_view', { page, ...properties });
  }

  trackAuth(event, properties = {}) {
    this.trackEvent(`auth_${event}`, { category: 'auth', ...properties });
  }

  trackAdEvent(event, adId, properties = {}) {
    this.trackEvent(`ad_${event}`, { ad_id: adId, category: 'ad', ...properties });
  }

  trackUserAction(action, properties = {}) {
    this.trackEvent(action, { category: 'user_action', ...properties });
  }

  trackError(error, errorType = 'unknown', properties = {}) {
    this.trackEvent('error', {
      error_message: error instanceof Error ? error.message : String(error),
      error_type: errorType,
      category: 'error',
      ...properties,
    });
  }

  trackFormSubmit(formName, properties = {}) {
    this.trackEvent('form_submit', { form_name: formName, ...properties });
  }

  queueEvent(event, properties) {
    const queue = JSON.parse(localStorage.getItem('analytics_queue') || '[]');
    queue.push({ event, properties, timestamp: Date.now() });
    localStorage.setItem('analytics_queue', JSON.stringify(queue));
  }

  flushQueue() {
    const queue = JSON.parse(localStorage.getItem('analytics_queue') || '[]');
    queue.forEach(({ event, properties }) => {
      if (window.posthog) {
        posthog.capture(event, properties);
      }
    });
    localStorage.setItem('analytics_queue', '[]');
  }
}

// Initialize global analytics instance
window.analytics = new Analytics();

// Track page views
window.analytics.trackPageView(window.location.pathname);

// Show consent bar once DOM is ready (static pages; WP relies on Complianz)
if (document.readyState !== 'loading') window.analytics.maybeShowConsentBanner();
else document.addEventListener('DOMContentLoaded', () => window.analytics.maybeShowConsentBanner());

// Track unhandled errors
window.addEventListener('error', (event) => {
  window.analytics.trackError(event.error, 'uncaught_error', {
    filename: event.filename,
    lineno: event.lineno,
  });
});

// Track navigation
window.addEventListener('popstate', () => {
  window.analytics.trackPageView(window.location.pathname);
});
