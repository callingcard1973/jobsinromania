// Document Tracking - PostHog markers for all document operations
class DocumentTracker {
  constructor(analytics) {
    this.analytics = analytics;
    this.initTrackingMarkers();
  }

  initTrackingMarkers() {
    // Track all document views with data-posthog-mark attribute
    document.addEventListener('click', (e) => {
      const target = e.target.closest('[data-posthog-mark]');
      if (target) {
        this.trackDocumentAction(target);
      }
    });

    // Track form submissions on document operations
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (form.dataset.posthogDocType) {
        this.trackDocumentFormSubmit(form);
      }
    });

    // Track visibility/scroll of documents
    this.initDocumentVisibilityTracking();
  }

  trackDocumentAction(element) {
    const mark = element.dataset.posthogMark;
    const docType = element.dataset.docType || 'unknown';
    const docId = element.dataset.docId || null;
    const action = element.dataset.action || 'interaction';
    const properties = this.extractProperties(element);

    this.analytics.trackEvent(`document_${docType}_${action}`, {
      document_mark: mark,
      document_type: docType,
      document_id: docId,
      action: action,
      element_type: element.tagName,
      ...properties,
    });
  }

  trackDocumentFormSubmit(form) {
    const docType = form.dataset.posthogDocType;
    const docId = form.dataset.docId || null;
    const action = form.dataset.action || 'submit';
    const properties = this.extractFormData(form);

    this.analytics.trackEvent(`document_${docType}_${action}`, {
      document_type: docType,
      document_id: docId,
      action: action,
      form_fields: Object.keys(properties),
      ...properties,
    });
  }

  trackDocumentView(docType, docId, properties = {}) {
    const mark = `doc_${docType}_${docId}_view`;
    this.analytics.trackEvent(`document_${docType}_viewed`, {
      document_mark: mark,
      document_type: docType,
      document_id: docId,
      action: 'viewed',
      ...properties,
    });
  }

  trackDocumentCreated(docType, docId, properties = {}) {
    const mark = `doc_${docType}_${docId}_created`;
    this.analytics.trackEvent(`document_${docType}_created`, {
      document_mark: mark,
      document_type: docType,
      document_id: docId,
      action: 'created',
      ...properties,
    });
  }

  trackDocumentEdited(docType, docId, properties = {}) {
    const mark = `doc_${docType}_${docId}_edited`;
    this.analytics.trackEvent(`document_${docType}_edited`, {
      document_mark: mark,
      document_type: docType,
      document_id: docId,
      action: 'edited',
      ...properties,
    });
  }

  trackDocumentDeleted(docType, docId, properties = {}) {
    const mark = `doc_${docType}_${docId}_deleted`;
    this.analytics.trackEvent(`document_${docType}_deleted`, {
      document_mark: mark,
      document_type: docType,
      document_id: docId,
      action: 'deleted',
      ...properties,
    });
  }

  trackDocumentSearch(docType, query, resultsCount, properties = {}) {
    this.analytics.trackEvent(`document_${docType}_search`, {
      document_type: docType,
      search_query: query,
      results_count: resultsCount,
      action: 'searched',
      ...properties,
    });
  }

  trackDocumentFilter(docType, filters, resultsCount, properties = {}) {
    this.analytics.trackEvent(`document_${docType}_filter`, {
      document_type: docType,
      filters_applied: Object.keys(filters),
      results_count: resultsCount,
      action: 'filtered',
      ...properties,
    });
  }

  initDocumentVisibilityTracking() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && entry.target.dataset.posthogMark) {
          const element = entry.target;
          const mark = element.dataset.posthogMark;
          const docType = element.dataset.docType || 'unknown';
          const docId = element.dataset.docId || null;

          this.analytics.trackEvent(`document_${docType}_visible`, {
            document_mark: mark,
            document_type: docType,
            document_id: docId,
            action: 'visible_in_viewport',
          });

          observer.unobserve(element);
        }
      });
    });

    document.querySelectorAll('[data-posthog-mark]').forEach((el) => {
      observer.observe(el);
    });
  }

  extractProperties(element) {
    const props = {};
    Array.from(element.attributes).forEach((attr) => {
      if (attr.name.startsWith('data-prop-')) {
        const key = attr.name.replace('data-prop-', '');
        props[key] = attr.value;
      }
    });
    return props;
  }

  extractFormData(form) {
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => {
      data[key] = value;
    });
    return data;
  }

  getDocumentMark(docType, docId, action) {
    return `doc_${docType}_${docId}_${action}`;
  }
}

// Initialize document tracker with analytics
if (window.analytics) {
  window.documentTracker = new DocumentTracker(window.analytics);
}
