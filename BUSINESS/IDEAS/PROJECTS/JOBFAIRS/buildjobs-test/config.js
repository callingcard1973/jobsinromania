// BuildJobs.eu Configuration
const CONFIG = {
  // API Endpoints
  api: {
    jobsJson: '/jobs/jobs.json',
    jobsCount: '#jobs-count'
  },

  // External URLs
  urls: {
    apply: 'https://interjob.ro/apply.html',
    pdfArchive: 'https://archive.org/details/eures-jobs-buildjobs-eu-en',
    pdfDirect: '/jobs/jobs_catalog.pdf',
    telegram: 'https://t.me/BuildJobsEU_bot'
  },

  // Theme (override :root CSS vars)
  theme: {
    accent: '#f59e0b',
    accentHot: '#fbbf24',
    bg: '#08080d',
    surface: '#0f0f17',
    text: '#e8e8ec',
    textMuted: '#7e7e96',
    textDim: '#4a4a62',
    border: '#1e1e30',
    green: '#22c55e',
    blue: '#3b82f6'
  },

  // Scroll reveal threshold
  reveal: {
    threshold: 0.08,
    rootMargin: '0px 0px -40px 0px'
  },

  // Analytics (add later)
  analytics: {
    enabled: false,
    trackingId: ''
  }
};

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
