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

  identify(userId, traits = {}) {
    this.userId = userId;
    localStorage.setItem('user_id', userId);
    if (window.posthog) {
      posthog.identify(userId, { ...traits, session_id: this.sessionId });
    }
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
