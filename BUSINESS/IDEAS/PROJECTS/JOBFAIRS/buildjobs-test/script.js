// BuildJobs.eu — Main Script

// SCROLL REVEAL
function initScrollReveal() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        obs.unobserve(e.target);
      }
    });
  }, {
    threshold: CONFIG.reveal.threshold,
    rootMargin: CONFIG.reveal.rootMargin
  });

  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

// DYNAMIC JOB COUNT
function loadJobCount() {
  fetch(CONFIG.api.jobsJson)
    .then(r => r.json())
    .then(jobs => {
      const elem = document.querySelector(CONFIG.api.jobsCount);
      if (elem) elem.textContent = jobs.length || 0;
    })
    .catch(err => {
      console.warn('Could not load job count:', err);
    });
}

// LANGUAGE SELECTOR ACTIVE STATE
function setActiveLang() {
  const path = window.location.pathname;
  const lang = path.split('/')[1] || 'en';

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.remove('active');
    const href = btn.getAttribute('href');
    if ((lang === 'en' && href === '/') || href.includes(`/${lang}/`)) {
      btn.classList.add('active');
    }
  });
}

// INIT
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  loadJobCount();
  setActiveLang();
});
