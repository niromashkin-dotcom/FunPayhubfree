// FunPay Hub - main UI controller
(function() {
  'use strict';

  // ============= SIDEBAR ACTIVE HIGHLIGHT =============
  function highlightActive() {
    const path = window.location.pathname.toLowerCase();
    document.querySelectorAll('.sidebar-item').forEach(item => {
      const href = (item.getAttribute('href') || '').toLowerCase();
      if (href && path.endsWith(href.split('/').pop())) {
        item.classList.add('active');
      }
    });
  }

  // ============= TOAST SYSTEM =============
  let toastContainer = null;
  function ensureToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement('div');
    toastContainer.className = 'toasts';
    document.body.appendChild(toastContainer);
    return toastContainer;
  }

  window.toast = function(message, type = 'info', duration = 4000) {
    const c = ensureToastContainer();
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = message;
    c.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'all 0.25s ease';
      setTimeout(() => el.remove(), 300);
    }, duration);
  };

  // ============= API HELPER =============
  window.api = async function(endpoint, options = {}) {
    try {
      const r = await fetch(endpoint, options);
      if (!r.ok) {
        console.warn('API error', endpoint, r.status);
        return null;
      }
      const ct = r.headers.get('content-type') || '';
      if (ct.includes('json')) return await r.json();
      return await r.text();
    } catch (e) {
      console.error('API failed', endpoint, e);
      return null;
    }
  };

  // ============= MARKET SCAN EMPTY STATE =============
  window.marketScanEmpty = function(colspan, msg) {
    if (window.__market_scanning) {
      return '<tr><td colspan="' + colspan + '" class="empty-state"><span class="spinner"></span> Сканирование...</td></tr>';
    }
    return '<tr><td colspan="' + colspan + '" class="empty-state">' + msg + '</td></tr>';
  };

  // ============= INIT =============
  document.addEventListener('DOMContentLoaded', () => {
    highlightActive();
    console.log('FunPay Hub UI ready');
  });

})();
// FPH theme hook - reload theme when changed in another tab
window.addEventListener('storage', (e) => {
  if (e.key === 'fph-theme' && window.theme) {
    try { window.theme.apply(window.theme.load()); } catch(_) {}
  }
});
// marker: theme already loaded
// ===== Theme migration v1 -> v2 (remove old base64 from localStorage) =====
(function migrateThemeStorage() {
  try {
    const raw = localStorage.getItem('fph-theme');
    if (!raw) return;
    const parsed = JSON.parse(raw);
    let changed = false;

    if (parsed.bgImage && parsed.bgImage.startsWith && parsed.bgImage.startsWith('data:')) {
      delete parsed.bgImage;
      changed = true;
    }
    // Also clear large legacy sound base64 entries
    const sraw = localStorage.getItem('fph-sounds');
    if (sraw) {
      try {
        const sounds = JSON.parse(sraw);
        let sChanged = false;
        for (const k of Object.keys(sounds)) {
          if (typeof sounds[k] === 'string' && sounds[k].startsWith('data:')) {
            delete sounds[k];
            sChanged = true;
          }
        }
        if (sChanged) {
          localStorage.setItem('fph-sounds', JSON.stringify(sounds));
        }
      } catch(e) {}
    }

    if (changed) {
      localStorage.setItem('fph-theme', JSON.stringify(parsed));
    }
  } catch(e) {}
})();
// ============================================
// SIDEBAR: click-to-expand sticky groups
// ============================================
(function initSidebarExpand() {
  function setup() {
    // 1. Mark groups that contain the current active page
    const currentPath = location.pathname.split('/').pop();
    document.querySelectorAll('.sidebar-group').forEach(group => {
      const subs = group.querySelectorAll('.sidebar-sub');
      let hasActive = false;
      subs.forEach(s => {
        const href = (s.getAttribute('href') || '').split('/').pop();
        if (href === currentPath) {
          s.classList.add('active');
          hasActive = true;
        }
      });
      if (hasActive) group.classList.add('has-active', 'open');
    });

    // 2. Restore expand state from localStorage
    try {
      const expanded = JSON.parse(localStorage.getItem('fph-sidebar-expanded') || '[]');
      document.querySelectorAll('.sidebar-group').forEach((g, idx) => {
        if (expanded.includes(idx)) g.classList.add('open');
      });
    } catch(e) {}

// 3. Click handler — toggle expand and prevent navigation when has submenu
     document.querySelectorAll('.sidebar-group > .sidebar-item').forEach((item, idx) => {
       const group = item.closest('.sidebar-group');
       const submenu = group.querySelector('.sidebar-submenu');
       if (!submenu) return;

        item.addEventListener('click', (e) => {
          e.preventDefault();
          const wasOpen = group.classList.contains('open');
          if (!wasOpen) {
            group.classList.add('open');
          } else {
            group.classList.remove('open');
          }

         // Save state
         try {
           const all = Array.from(document.querySelectorAll('.sidebar-group'));
           const openIdx = all
             .map((g, i) => g.classList.contains('open') ? i : -1)
             .filter(i => i >= 0);
           localStorage.setItem('fph-sidebar-expanded', JSON.stringify(openIdx));
         } catch(e) {}
       });
     });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();