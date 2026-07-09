// FunPay Hub - Theme Engine v4
// FIX 1: Video reused (not recreated) on slider changes
// FIX 2: Background applied via MutationObserver if DOM not ready
(function() {
  'use strict';

  const KEY = 'fph-theme';
  const SOUNDS_KEY = 'fph-sounds';

  const DEFAULTS = {
    accent: '#00D4FF',
    accentRgb: '0,212,255',
    bgPreset: 'aurora',
    bgUrl: null,
    bgIsVideo: false,
    glassOpacity: 0.55,
    blur: 20,
    glow: 0.15,
    radius: 12,
    animSpeed: 1,
    fontFamily: "'Inter', -apple-system, sans-serif",
    auroraEnabled: true
  };

  const BG_PRESETS = {
    aurora:    'linear-gradient(180deg, #050A14 0%, #081120 50%, #050A14 100%)',
    midnight:  'linear-gradient(180deg, #0A0A1A, #141442)',
    nebula:    'linear-gradient(180deg, #0A0618, #1A1040)',
    deepspace: 'linear-gradient(180deg, #020408, #060C18)',
    forest:    'linear-gradient(180deg, #0a1f14, #142d22)',
    sunset:    'linear-gradient(180deg, #1a0a14, #2d142a)'
  };

  function hexToRgb(hex) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return '0,212,255';
    return [parseInt(m[1],16), parseInt(m[2],16), parseInt(m[3],16)].join(',');
  }

  function absolutize(url) {
    if (!url) return null;
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('//')) return location.protocol + url;
    if (url.startsWith('/')) return location.origin + url;
    return location.origin + '/' + url;
  }

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return Object.assign({}, DEFAULTS);
      const parsed = JSON.parse(raw);
      if (parsed.bgImage && !parsed.bgUrl) delete parsed.bgImage;
      return Object.assign({}, DEFAULTS, parsed);
    } catch(e) { return Object.assign({}, DEFAULTS); }
  }

  function save(theme) {
    try {
      // Merge with existing localStorage value to prevent accidental data loss
      let existing = {};
      try {
        const raw = localStorage.getItem(KEY);
        if (raw) existing = JSON.parse(raw);
      } catch(e) {}
      const merged = Object.assign({}, existing, theme);
      delete merged.bgImage;
      localStorage.setItem(KEY, JSON.stringify(merged));
    } catch(e) { console.error('Theme save failed:', e); }
  }

  // ============================================================
  // CRITICAL: Apply background SMARTLY
  // - If video URL didn't change -> DON'T recreate <video>
  // - If aurora missing -> wait for it
  // ============================================================

  function applyBackground(theme) {
    const aurora = document.querySelector('.aurora');
    if (!aurora) return false;

    const absUrl = theme.bgUrl ? absolutize(theme.bgUrl) : null;
    const wantVideo = !!(theme.bgUrl && theme.bgIsVideo);
    const wantImage = !!(theme.bgUrl && !theme.bgIsVideo);

    const existingVideo = document.getElementById('bg-video');

    // VIDEO MODE
    if (wantVideo) {
      aurora.style.background = 'transparent';
      aurora.style.opacity = '1';

      // REUSE existing video if URL matches - DO NOT TOUCH IT
      if (existingVideo && existingVideo.dataset.src === absUrl) {
        return true;  // <-- key fix: don't recreate
      }

      if (existingVideo) existingVideo.remove();

      const v = document.createElement('video');
      v.id = 'bg-video';
      v.src = absUrl;
      v.dataset.src = absUrl;
      v.autoplay = true;
      v.loop = true;
      v.muted = true;
      v.playsInline = true;
      v.setAttribute('playsinline', '');
      Object.assign(v.style, {
        position: 'fixed',
        inset: '0',
        width: '100vw',
        height: '100vh',
        objectFit: 'cover',
        zIndex: '-2',
        pointerEvents: 'none'
      });
      document.body.appendChild(v);
      return true;
    }

    // Not video -> remove existing video if any
    if (existingVideo) existingVideo.remove();

    // IMAGE MODE
    if (wantImage) {
      aurora.style.background = `url("${absUrl}") center/cover no-repeat fixed`;
      aurora.style.opacity = '1';
      return true;
    }

    // PRESET MODE
    if (BG_PRESETS[theme.bgPreset]) {
      aurora.style.background = BG_PRESETS[theme.bgPreset];
      aurora.style.opacity = '1';
      return true;
    }

    return false;
  }

  function applyCssVars(theme) {
    const root = document.documentElement;
    const rgb = hexToRgb(theme.accent);

    root.style.setProperty('--accent-cyan', theme.accent);
    root.style.setProperty('--accent-rgb', rgb);
    root.style.setProperty('--glass-bg', `rgba(11, 22, 48, ${theme.glassOpacity})`);
    root.style.setProperty('--glass-hover', `rgba(${rgb}, 0.14)`);
    root.style.setProperty('--glass-border', `rgba(${rgb}, 0.10)`);
    root.style.setProperty('--glow-cyan', `0 0 ${30 * (theme.glow / 0.15)}px rgba(${rgb}, ${theme.glow})`);
    root.style.setProperty('--blur-amount', theme.blur + 'px');
    root.style.setProperty('--radius-md', theme.radius + 'px');
    root.style.setProperty('--radius-lg', (theme.radius + 4) + 'px');
    root.style.setProperty('--radius-xl', (theme.radius + 8) + 'px');
    root.style.setProperty('--anim-speed', theme.animSpeed);
    root.style.setProperty('font-family', theme.fontFamily);
  }

  // Wait for .aurora element to appear in DOM
  let pendingApply = null;
  let observer = null;

  function ensureAurora(theme) {
    if (document.querySelector('.aurora')) {
      return applyBackground(theme);
    }
    // Set up observer once
    if (!observer) {
      observer = new MutationObserver(() => {
        if (document.querySelector('.aurora') && pendingApply) {
          applyBackground(pendingApply);
          pendingApply = null;
          observer.disconnect();
          observer = null;
        }
      });
      // Wait for body if not exists yet
      if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
      } else {
        document.addEventListener('DOMContentLoaded', () => {
          observer.observe(document.body, { childList: true, subtree: true });
        }, { once: true });
      }
    }
    pendingApply = theme;
    return false;
  }

  function apply(theme) {
    applyCssVars(theme);

    if (!document.body) {
      document.addEventListener('DOMContentLoaded', () => apply(theme), { once: true });
      return;
    }

    ensureAurora(theme);

    const aurora = document.querySelector('.aurora');
    if (aurora) {
      const animEnabled = theme.auroraEnabled && !theme.bgUrl;
      aurora.style.animation = animEnabled
        ? `aurora-drift ${30 / (theme.animSpeed || 1)}s ease-in-out infinite alternate`
        : 'none';
    }

    document.querySelectorAll('.sidebar-item, .card, .btn').forEach(el => {
      el.style.transitionDuration = (0.15 / (theme.animSpeed || 1)) + 's';
    });
  }

  function loadSounds() {
    try { return JSON.parse(localStorage.getItem(SOUNDS_KEY) || '{}'); }
    catch(e) { return {}; }
  }
  function saveSounds(s) {
    try { localStorage.setItem(SOUNDS_KEY, JSON.stringify(s)); } catch(e) {}
  }
  window.playSound = function(name) {
    const s = loadSounds();
    const url = s[name];
    if (!url) return;
    try {
      const a = new Audio(absolutize(url));
      a.volume = 0.6;
      a.play().catch(()=>{});
    } catch(e) {}
  };

  async function uploadFile(file, kind) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('type', kind);
    const r = await fetch('/api/userdata/upload', { method: 'POST', body: fd });
    const j = await r.json().catch(() => ({ ok: false, error: 'bad json' }));
    if (!j.ok) throw new Error(j.error || 'upload failed');
    return j;
  }

  async function deleteFile(kind, name) {
    const r = await fetch('/api/userdata/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: kind, name })
    });
    return r.ok;
  }

  window.theme = {
    load, save, apply,
    DEFAULTS, BG_PRESETS,
    uploadFile, deleteFile,
    reset() {
      localStorage.removeItem(KEY);
      localStorage.removeItem(SOUNDS_KEY);
      const v = document.getElementById('bg-video');
      if (v) v.remove();
      apply(DEFAULTS);
    },
    loadSounds, saveSounds
  };

  // Apply immediately
  const t = load();
  apply(t);
  // Re-apply on DOMContentLoaded (just in case)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => apply(t), { once: true });
  }
})();