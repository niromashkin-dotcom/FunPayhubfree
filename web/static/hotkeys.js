// FunPay Hub - Global Hotkeys
// Ctrl+1..5  -> navigate sections
// Ctrl+,     -> appearance
// Ctrl+/     -> help
// Ctrl+K     -> command palette (handled in cmdk.js)
// Ctrl+B     -> toggle sidebar groups
// Esc        -> close any modal
(function() {
  'use strict';

  const SHORTCUTS = {
    '1': 'dashboard.html',
    '2': 'account.html',         // Seller -> Profile
    '3': 'market.html',          // Market
    '4': 'autoreply.html',       // Automation
    '5': 'plugins.html',         // System
  };

  function isTypingInInput(e) {
    const t = e.target;
    if (!t) return false;
    const tag = (t.tagName || '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (t.isContentEditable) return true;
    return false;
  }

  document.addEventListener('keydown', (e) => {
    // Don't intercept hotkeys while typing
    if (isTypingInInput(e) && !(e.ctrlKey || e.metaKey)) return;

    const ctrl = e.ctrlKey || e.metaKey;

    // Ctrl+1..5 -> navigate
    if (ctrl && SHORTCUTS[e.key]) {
      e.preventDefault();
      const url = SHORTCUTS[e.key];
      if (location.pathname.indexOf(url) < 0) {
        location.href = url;
      }
      return;
    }

    // Ctrl+, -> appearance
    if (ctrl && e.key === ',') {
      e.preventDefault();
      location.href = 'appearance.html';
      return;
    }

    // Ctrl+/ -> help
    if (ctrl && e.key === '/') {
      e.preventDefault();
      location.href = 'help.html';
      return;
    }

    // Ctrl+B -> toggle all sidebar groups
    if (ctrl && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      const groups = document.querySelectorAll('.sidebar-group');
      // Check if any open -> close all. Otherwise open all.
      let anyOpen = false;
      groups.forEach(g => { if (g.classList.contains('open')) anyOpen = true; });
      groups.forEach(g => {
        if (anyOpen) g.classList.remove('open');
        else g.classList.add('open');
      });
      try {
        const all = Array.from(groups);
        const idx = anyOpen ? [] : all.map((g, i) => i);
        localStorage.setItem('fph-sidebar-expanded', JSON.stringify(idx));
      } catch(_) {}
      return;
    }

    // Esc -> close any open modal (cmdk handles its own)
    if (e.key === 'Escape') {
      const cmdk = document.querySelector('.cmdk-backdrop.open');
      if (cmdk) return; // cmdk has own handler
      // close any other modals if needed
    }
  });

  console.log('[hotkeys] ready: Ctrl+1..5, Ctrl+,/, Ctrl+B, Ctrl+K');
})();