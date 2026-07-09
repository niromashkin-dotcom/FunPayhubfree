// FunPay Hub - Onboarding flow
// Checks if user has connected FunPay account.
// If not, redirects to account.html with a helpful hint.
(function() {
  'use strict';

  // Don't redirect if already on account/help/appearance/onboarding pages
  const SAFE_PAGES = ['account.html', 'help.html', 'appearance.html'];
  const currentPage = location.pathname.split('/').pop().toLowerCase();
  if (SAFE_PAGES.indexOf(currentPage) >= 0) return;

  // Don't redirect if we already showed onboarding this session
  if (sessionStorage.getItem('fph-onboarded') === 'true') return;

  // Don't redirect from sub-pages we want to be accessible
  if (location.search.indexOf('skip-onboarding') >= 0) {
    sessionStorage.setItem('fph-onboarded', 'true');
    return;
  }

  async function checkAndRedirect() {
    try {
      const r = await fetch('/api/seller/status', { cache: 'no-store' });
      if (!r.ok) return;
      const j = await r.json();
      const connected = j && (j.has_credentials || j.connected);

      if (!connected) {
        // First-time user — redirect to account page
        sessionStorage.setItem('fph-onboarding-needed', 'true');
        location.replace('account.html?onboarding=1');
      } else {
        sessionStorage.setItem('fph-onboarded', 'true');
      }
    } catch(e) {
      // API not ready — try again in 2s
      setTimeout(checkAndRedirect, 2000);
    }
  }

  // Wait a moment so other scripts initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(checkAndRedirect, 300));
  } else {
    setTimeout(checkAndRedirect, 300);
  }
})();