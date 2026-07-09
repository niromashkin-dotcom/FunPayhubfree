function formatBalance(data) {
    if (typeof data === 'object' && data !== null) {
        if (data.balance && typeof data.balance === 'object') {
            data = data.balance;
        }
        var val = data.total_rub || data.available_rub || data.available || data.balance || data.amount || 0;
        if (!val && data.currencies && typeof data.currencies === 'object') {
            var first = Object.values(data.currencies)[0];
            if (first && first.amount) val = first.amount;
        }
        if (val === undefined) val = 0;
        if (typeof val === 'object') val = 0;
        return Number(val).toLocaleString('ru-RU', {minimumFractionDigits: 0, maximumFractionDigits: 0}) + ' ₽';
    }
    if (typeof data === 'number' || typeof data === 'string') {
        return Number(data).toLocaleString('ru-RU', {minimumFractionDigits: 0, maximumFractionDigits: 0}) + ' ₽';
    }
    return '0 ₽';
}
// FunPay Hub - Live Sync v3
// - Seller-side polling: balance, orders, sales (60s)
// - Background analytics: heatmap, niches, competitors, AI (1 hour)
// - Notifications: 30s
// - Logs: 3s on logs page only
(function() {
  'use strict';
  window.__fph_cache = window.__fph_cache || {};
  const _origFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const isGet = !init || !init.method || init.method === 'GET';
    const cached = window.__fph_cache[url];
    if (cached && Date.now() - cached.ts < 60000) {
      return new Response(JSON.stringify(cached.data), {status: 200, headers: {'Content-Type': 'application/json'}});
    }
    const resp = await _origFetch(input, init);
    if (isGet && resp && resp.ok) {
      try {
        const clone = resp.clone();
        const data = await clone.json();
        window.__fph_cache[url] = {ts: Date.now(), data: data};
      } catch(e) {}
    }
    return resp;
  };

  let pollers = [];
  let isOnline = false;
  let connectionEl = null;

  // ===== CONNECTION INDICATOR =====
  function ensureConnectionIndicator() {
    if (connectionEl) return connectionEl;
    const status = document.querySelector('.topbar-status');
    if (!status) return null;
    if (!document.getElementById('live-dot')) {
      status.innerHTML = '<span class="status-dot" id="live-dot"></span><span id="live-text">Подключение...</span>';
    }
    connectionEl = {
      dot: document.getElementById('live-dot'),
      text: document.getElementById('live-text')
    };
    return connectionEl;
  }

  function setOnline(state) {
    if (state === isOnline) return;
    isOnline = state;
    const c = ensureConnectionIndicator();
    if (!c) return;
    if (state) {
      c.dot.style.background = '#10B981';
      c.dot.style.boxShadow = '0 0 8px rgba(16, 185, 129, 0.5)';
      c.text.textContent = 'Live';
      c.text.style.color = 'var(--text-secondary)';
    } else {
      c.dot.style.background = '#F43F5E';
      c.dot.style.boxShadow = '0 0 8px rgba(244, 63, 94, 0.5)';
      c.text.textContent = 'Offline';
      c.text.style.color = '#F43F5E';
    }
  }

  // ===== AUTO-COLLECT NOTIFICATIONS (60s) =====
  // Triggers backend scan: new orders, new messages, new reviews.
  // Backend will then emit events to bus + write to notifications storage.
  async function collectNotifications() {
    try {
      await fetch('/api/seller/notifications/collect', { method: 'POST' });
    } catch (e) {}
  }

  // ===== UNREAD BADGES (iOS/Telegram style red counters) =====
  async function updateBadges() {
    try {
      const r = await fetch('/api/seller/notifications?only_unack=true&limit=200');
      if (!r.ok) return;
      const data = await r.json().catch(() => ({}));
      const list = (data && data.notifications) || data || [];
      if (!Array.isArray(list)) return;

      const counters = {};
      list.forEach(n => {
        const t = n.type || 'other';
        counters[t] = (counters[t] || 0) + 1;
      });

      const total      = list.length;
      const orderCnt   = (counters['new_order']    || 0) + (counters['sale_closed'] || 0);
      const msgCnt     = counters['chat_message']  || 0;
      const reviewCnt  = counters['new_review']    || 0;
      const buyerCnt   = counters['new_buyer']     || 0;

      // Sidebar badges
      setSidebarBadge('notifications.html', total);
      setSidebarBadge('orders.html',        orderCnt);
      setSidebarBadge('autoreply.html',     msgCnt);
      setSidebarBadge('customers.html',     buyerCnt);

      // Live indicator counter
      const liveText = document.getElementById('live-text');
      if (liveText && isOnline) {
        liveText.textContent = total > 0 ? ('Live · ' + total) : 'Live';
      }
    } catch (e) {}
  }

  // Sidebar badge: red dot with count (iOS-style). Auto-creates if missing.
  function setSidebarBadge(hrefMatch, count) {
    const links = document.querySelectorAll('.sidebar a[href*="' + hrefMatch + '"]');
    links.forEach(link => {
      let badge = link.querySelector('.nav-badge-pill');
      if (count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'nav-badge-pill';
          link.appendChild(badge);
        }
        badge.textContent = count > 99 ? '99+' : String(count);
      } else if (badge) {
        badge.remove();
      }
    });
  }

  // Inject badge styles once
  (function injectBadgeStyles() {
    if (document.getElementById('nav-badge-style')) return;
    const style = document.createElement('style');
    style.id = 'nav-badge-style';
    style.textContent = `
      .sidebar a { position: relative; }
      .nav-badge-pill {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        min-width: 18px;
        height: 18px;
        padding: 0 6px;
        background: linear-gradient(135deg, #F43F5E 0%, #E11D48 100%);
        color: #fff;
        font-size: 11px;
        font-weight: 700;
        line-height: 18px;
        text-align: center;
        border-radius: 9px;
        box-shadow: 0 0 8px rgba(244, 63, 94, 0.6), 0 2px 4px rgba(0,0,0,0.2);
        animation: nav-badge-pulse 2s ease-in-out infinite;
        z-index: 10;
        pointer-events: none;
      }
      @keyframes nav-badge-pulse {
        0%, 100% { box-shadow: 0 0 8px rgba(244, 63, 94, 0.6), 0 2px 4px rgba(0,0,0,0.2); }
        50%      { box-shadow: 0 0 14px rgba(244, 63, 94, 0.9), 0 2px 6px rgba(0,0,0,0.3); }
      }
    `;
    document.head.appendChild(style);
  })();

    // ===== NOTIFICATIONS (30s) =====
  let lastNotifIds = new Set();
  let firstNotifLoad = true;

  async function pollNotifications() {
    try {
      const r = await fetch('/api/seller/notifications');
      if (!r.ok) { setOnline(false); return; }
      setOnline(true);
      const data = await r.json().catch(() => ({}));
      const list = (data && data.notifications) || data || [];
      if (!Array.isArray(list)) return;

      const currentIds = new Set(list.map(n => n.id || n.timestamp));
      if (!firstNotifLoad) {
        list.forEach(n => {
          const id = n.id || n.timestamp;
          if (!lastNotifIds.has(id)) {
            window.toast && window.toast(n.title || n.message || 'Новое уведомление', n.type || 'info');
            if (window.playSound) {
              const sound = n.severity === 'error' ? 'error'
                          : n.severity === 'warning' ? 'warn'
                          : n.type === 'sale' ? 'success'
                          : 'message';
              window.playSound(sound);
            }
          }
        });
      }
      lastNotifIds = currentIds;
      firstNotifLoad = false;
    } catch (e) { setOnline(false); }
  }

  // ===== ALERTS (60s) =====
  let lastAlertIds = new Set();
  let firstAlertsLoad = true;
  async function pollAlerts() {
    try {
      const d = await fetch('/api/alerts').then(r => r.ok ? r.json() : null);
      const list = (d && d.alerts) || d || [];
      if (!Array.isArray(list)) return;
      const ids = new Set(list.map(a => a.id));
      if (!firstAlertsLoad) {
        list.forEach(a => {
          if (!lastAlertIds.has(a.id)) {
            const sev = a.severity || a.level || 'info';
            const type = sev === 'critical' || sev === 'error' ? 'error'
                       : sev === 'warning' || sev === 'warn' ? 'warn' : 'info';
            window.toast && window.toast(a.message || a.title || 'Алерт', type);
            if (window.playSound) window.playSound(type);
          }
        });
      }
      lastAlertIds = ids;
      firstAlertsLoad = false;
    } catch(e) {}
  }

// ===== SELLER DATA (60s) — balance + orders + sales =====
   let lastOrderIds = new Set();
   let firstOrderLoad = true;

    async function syncSeller() {
      // BALANCE (live update on balance.html)
      try {
        if (document.getElementById('m-current')) {
          const b = await fetch('/api/seller/balance/full').then(r => r.ok ? r.json() : null);
          if (b) {
            const bal = (b.balance && typeof b.balance === 'object') ? b.balance : (typeof b === 'object' ? b : {});
            const total = bal.total_rub ?? 0;
            let avail = bal.available_rub ?? bal.total_rub ?? 0;
            const frozen = bal.frozen ?? 0;
            if (!total && bal.currencies && typeof bal.currencies === 'object') {
              const firstCur = Object.values(bal.currencies)[0];
              if (firstCur && firstCur.amount) avail = firstCur.amount;
            }
            const cur = document.getElementById('m-current');
            const newVal = formatBalance(total);
            if (cur.textContent !== newVal && cur.textContent !== '—') {
              const oldNum = parseFloat(cur.textContent);
              const newNum = parseFloat(total);
              if (!isNaN(oldNum) && !isNaN(newNum)) {
                cur.style.transition = 'color 0.3s';
                cur.style.color = newNum > oldNum ? '#10B981' : '#F43F5E';
                setTimeout(() => { cur.style.color = ''; }, 1500);
              }
            }
            cur.textContent = newVal;
            const av = document.getElementById('m-avail'); if (av) av.textContent = formatBalance(avail);
            const fr = document.getElementById('m-frozen'); if (fr) fr.textContent = formatBalance(frozen);
            const up = document.getElementById('m-updated'); if (up) up.textContent = b.updated_at ? new Date(b.updated_at * 1000).toLocaleString('ru-RU', {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'}).replace(',', '') : '—';
          }
        }
      } catch(e) {}

    // ORDERS (notify on new, refresh table on orders.html)
    try {
      const o = await fetch('/api/seller/orders').then(r => r.ok ? r.json() : null);
      const list = (o && o.orders) || o || [];
      if (!Array.isArray(list)) return;

      const ids = new Set(list.map(x => x.id));
      if (!firstOrderLoad) {
        list.forEach(x => {
          if (!lastOrderIds.has(x.id)) {
            window.toast && window.toast('Новый заказ #' + x.id + (x.title ? ' — ' + x.title : ''), 'success');
            if (window.playSound) window.playSound('success');
          }
        });
      }
      lastOrderIds = ids;
      firstOrderLoad = false;

      // Refresh orders table if on orders.html
      const ordersBody = document.getElementById('orders-body');
      if (ordersBody && list.length) {
        ordersBody.innerHTML = list.map(x => `
          <tr>
            <td class="mono muted">${x.id || '—'}</td>
            <td>${x.title || x.lot_title || '—'}</td>
            <td>${x.buyer || x.buyer_username || '—'}</td>
            <td class="mono">${x.price ?? '—'} ${x.currency || ''}</td>
            <td><span class="badge badge-${(x.status==='paid'||x.status==='closed')?'success':(x.status==='refund'?'danger':'info')}">${x.status || '—'}</span></td>
            <td class="row-actions">
              <button class="btn btn-sm btn-danger" onclick="if(typeof refund==='function')refund('${x.id}')">Возврат</button>
            </td>
          </tr>
        `).join('');
      }
    } catch(e) {}

    // Refresh seller profile in dashboard hero (if loader exists)
    if (window.__loadSeller) window.__loadSeller();
  }

  // ===== LOGS (3s, only on logs.html) =====
  let lastLogsCount = 0;
  async function pollLogs() {
    const body = document.getElementById('logs-body');
    if (!body) return;
    try {
      const d = await fetch('/api/logs').then(r => r.ok ? r.json() : null);
      const list = (d && d.logs) || d || [];
      if (!Array.isArray(list)) return;
      if (list.length === lastLogsCount) return;
      lastLogsCount = list.length;
      const humanize = typeof window.humanizeLog === 'function' ? window.humanizeLog : (m => m || '—');
      body.innerHTML = list.map(l => `
        <div class="log-line">
          <span class="log-time">${(l.timestamp||l.time||'').toString().slice(11,19)}</span>
          <span class="log-level-${(l.level||'info').toLowerCase()}">${(l.level||'INFO').toUpperCase()}</span>
          <span>${humanize(l.message || l.msg || '—')}</span>
        </div>
      `).join('');
      body.scrollTop = body.scrollHeight;
    } catch(e) {}
  }

  // ===== BACKGROUND ANALYTICS (1 hour) =====
  // Pre-fetches heavy analytics so when user opens the page — data is ready
  async function refreshAnalytics() {
    const endpoints = [
      '/api/market/heatmap',
      '/api/market/niches',
      '/api/market/competitors',
      '/api/market/ratings',
      '/api/ai/recommendations',
      '/api/margin/overview'
    ];
    for (const ep of endpoints) {
      try {
        await fetch(ep);
        // Small gap between requests to avoid server load
        await new Promise(r => setTimeout(r, 800));
      } catch(e) {}
    }
    console.log('[live] analytics warmed up');
  }

  // ===== BACKGROUND ANALYTICS (3 hours) =====
  // Auto-scans market if stale, then warms dependent pages
  async function refreshMarket() {
    const last = localStorage.getItem('__market_last_scan');
    const now = Date.now();
    const stale = !last || (now - parseInt(last, 10)) > 3 * 60 * 60 * 1000;
    if (!stale) return;
    window.__market_scanning = true;
    try {
      await fetch('/api/market/heatmap', {method: 'POST'});
      localStorage.setItem('__market_last_scan', String(Date.now()));
      await fetch('/api/market/niches');
      await fetch('/api/market/competitors');
      await fetch('/api/market/ratings');
      console.log('[live] market refreshed');
    } catch (e) {}
    window.__market_scanning = false;
  }

  // ===== MASTER START =====
  // ===== UNIVERSAL PAGE AUTO-REFRESH (60s) =====
  // Re-fetches all visible data on current page so user sees fresh state without F5.
  // Triggers a thin top progress bar to show system is alive.

  const PageAutoRefresher = {
    started: false,
    timer: null,

    refreshFor(page) {
      const map = {
        'dashboard.html': [
          '/api/seller/overview',
          '/api/seller/balance/full',
          '/api/seller/orders',
          '/api/seller/sales',
          '/api/market/alerts',
        ],
        'orders.html': ['/api/seller/orders?force=true'],
        'sales.html': ['/api/seller/sales?force=true'],
        'customers.html': ['/api/seller/customers?force=true', '/api/seller/orders'],
        'notifications.html': ['/api/seller/notifications'],
        'lots.html': ['/api/seller/lots?force=true'],
        'balance.html': ['/api/seller/balance/full?force=true', '/api/seller/balance/history'],
        'plugins.html': ['/api/plugins'],
        'autoreply.html': ['/api/autoreply/rules', '/api/autoreply/templates', '/api/autoreply/log'],
        'autodelivery.html': ['/api/autodelivery/bindings', '/api/autodelivery/settings', '/api/autodelivery/log'],
        'automation.html': ['/api/automation/tasks', '/api/automation/log'],
        'alerts.html': ['/api/alerts'],
        'backups.html': ['/api/system/backups'],
        'account.html': ['/api/seller/overview', '/api/seller/status'],
      };
      return map[page] || [];
    },

    detectPage() {
      const path = window.location.pathname;
      const m = path.match(/\/([^\/]+\.html)/);
      return m ? m[1] : null;
    },

    showProgress() {
      let bar = document.getElementById('page-refresh-bar');
      if (!bar) {
        bar = document.createElement('div');
        bar.id = 'page-refresh-bar';
        bar.style.cssText = 'position:fixed;top:0;left:0;height:2px;width:0;background:linear-gradient(90deg,#06B6D4,#3B82F6,#8B5CF6);box-shadow:0 0 8px rgba(59,130,246,0.6);z-index:99999;transition:width 0.4s ease;pointer-events:none;';
        document.body.appendChild(bar);
      }
      bar.style.width = '0';
      requestAnimationFrame(() => { bar.style.width = '70%'; });
    },

    finishProgress() {
      const bar = document.getElementById('page-refresh-bar');
      if (!bar) return;
      bar.style.width = '100%';
      setTimeout(() => { bar.style.width = '0'; }, 350);
    },

    async refresh() {
      const page = this.detectPage();
      if (!page) return;
      const urls = this.refreshFor(page);
      if (!urls.length) return;

      this.showProgress();

      // Fetch all in parallel
      await Promise.allSettled(urls.map(u => fetch(u).then(r => r.ok ? r.json() : null).catch(() => null)));

      // Trigger page-specific re-render hooks if defined
      const hooks = [
        'refreshPage',         // generic hook every page can define
        'loadOrders',          // orders.html
        'loadSales',           // sales.html
        'loadCustomers',       // customers.html
        'loadNotifications',   // notifications.html
        'loadLots',            // lots.html
        'loadBalance',         // balance.html
        'loadPlugins',         // plugins.html
        'loadRules',           // autoreply.html
        'loadTemplates',       // autoreply.html
        'loadBindings',        // autodelivery.html
        'loadTasks',           // automation.html
        'loadAlerts',          // alerts.html
        'loadBackups',         // backups.html
        '__loadSeller',        // dashboard hero
        'renderDashboard',     // dashboard
      ];
      for (const h of hooks) {
        try {
          if (typeof window[h] === 'function') {
            window[h]();
          }
        } catch (e) {}
      }

      this.finishProgress();
    },

    start() {
      if (this.started) return;
      this.started = true;
      // First refresh after 60s (page just loaded — fresh data already)
      this.timer = setInterval(() => {
        if (!document.hidden) this.refresh();
      }, 60000);
    },

    stop() {
      if (this.timer) clearInterval(this.timer);
      this.timer = null;
      this.started = false;
    },
  };

  // Expose globally for debugging
  window.PageAutoRefresher = PageAutoRefresher;

function start() {
     ensureConnectionIndicator();

     // initial
     collectNotifications();
     pollNotifications();
     pollAlerts();
     syncSeller();
     pollLogs();
     updateBadges();
     refreshMarket();

     // Intervals
     pollers.push(setInterval(collectNotifications, 60000));
     pollers.push(setInterval(updateBadges,         15000));
     pollers.push(setInterval(pollNotifications,    30000));
     pollers.push(setInterval(pollAlerts,           60000));
     pollers.push(setInterval(syncSeller,           60000));
     pollers.push(setInterval(pollLogs,             3000));
     pollers.push(setInterval(refreshMarket,        10800000));

     // Universal page auto-refresh — every 60s re-renders current page data
     PageAutoRefresher.start();

     // Pause when tab hidden
     document.addEventListener('visibilitychange', () => {
       if (document.hidden) {
         pollers.forEach(p => clearInterval(p));
         pollers = [];
       } else if (pollers.length === 0) {
         start();
       }
     });
   }

   if (document.readyState === 'loading') {
     document.addEventListener('DOMContentLoaded', start);
   } else {
     start();
   }

   window.addEventListener('beforeunload', () => {
     lastLogsCount = 0;
   });

 })();

// B17 badges renderer
(function(){
    'use strict';
    
    function ensureStyles() {
        if (document.getElementById('b17-styles')) return;
        var st = document.createElement('style');
        st.id = 'b17-styles';
        st.textContent = [
            '.nav-badge-b17 {',
            '  display: inline-block;',
            '  background: #ff3b30;',
            '  color: white;',
            '  font-size: 11px;',
            '  font-weight: 700;',
            '  border-radius: 10px;',
            '  padding: 1px 7px;',
            '  margin-left: 8px;',
            '  min-width: 18px;',
            '  text-align: center;',
            '  line-height: 16px;',
            '  vertical-align: middle;',
            '  box-shadow: 0 0 8px rgba(255,59,48,0.6);',
            '  animation: b17pulse 2s ease-in-out infinite;',
            '}',
            '@keyframes b17pulse {',
            '  0%, 100% { transform: scale(1); }',
            '  50% { transform: scale(1.1); }',
            '}',
            '.nav-active-b17 {',
            '  background: rgba(64, 156, 255, 0.2) !important;',
            '  border-left: 3px solid #409cff !important;',
            '  color: #fff !important;',
            '}'
        ].join('\n');
        document.head.appendChild(st);
    }
    
    function findLink(hrefPart) {
        var links = document.querySelectorAll('a[href]');
        for (var i = 0; i < links.length; i++) {
            var h = links[i].getAttribute('href') || '';
            if (h.indexOf(hrefPart) !== -1) return links[i];
        }
        return null;
    }
    
    function setBadge(el, count) {
        if (!el) return;
        var b = el.querySelector('.nav-badge-b17');
        if (count > 0) {
            var txt = count > 99 ? '99+' : String(count);
            if (b) {
                b.textContent = txt;
            } else {
                var s = document.createElement('span');
                s.className = 'nav-badge-b17';
                s.textContent = txt;
                el.appendChild(s);
            }
        } else if (b) {
            b.remove();
        }
    }
    
    function refreshBadges() {
        fetch('/api/seller/badges')
            .then(function(r){ return r.json(); })
            .then(function(d){
                if (!d || !d.ok) return;
                var c = d.counts || {};
                ensureStyles();
                setBadge(findLink('notifications.html'), c.notifications || 0);
                setBadge(findLink('orders.html'), c.orders || 0);
                setBadge(findLink('customers.html'), c.customers || 0);
                setBadge(findLink('alerts.html'), c.alerts || 0);
            })
            .catch(function(){});
    }
    
    function markRead(section) {
        fetch('/api/seller/badges/mark_read', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({section: section})
        })
        .then(function(){ setTimeout(refreshBadges, 400); })
        .catch(function(){});
    }
    
    function highlightActive() {
        var path = (location.pathname.split('/').pop() || 'dashboard.html').toLowerCase();
        var links = document.querySelectorAll('a[href]');
        links.forEach(function(a){
            var h = (a.getAttribute('href') || '').toLowerCase();
            if (h && h.indexOf(path) !== -1) {
                a.classList.add('nav-active-b17');
                if (h.indexOf('notifications.html') !== -1) markRead('notifications');
                else if (h.indexOf('orders.html') !== -1) markRead('orders');
                else if (h.indexOf('customers.html') !== -1) markRead('customers');
                else if (h.indexOf('alerts.html') !== -1) markRead('alerts');
            }
        });
    }
    
    function init() {
        ensureStyles();
        highlightActive();
        refreshBadges();
        setInterval(refreshBadges, 15000);
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.__B17 = { refresh: refreshBadges, markRead: markRead };
})();

// Обновление бейджей каждые 30 секунд
setInterval(fetchBadges, 30000);

// Перехватчик для автоматического форматирования баланса
(function() {
    const originalSet = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML').set;
    Object.defineProperty(Element.prototype, 'innerHTML', {
        set: function(value) {
            if (this.id && this.id.toLowerCase().includes('balance') || 
                this.className && this.className.toLowerCase().includes('balance')) {
                value = formatBalance(value);
            }
            originalSet.call(this, value);
        },
        configurable: true,
        enumerable: true
    });
    const originalTextSet = Object.getOwnPropertyDescriptor(Element.prototype, 'textContent').set;
    Object.defineProperty(Element.prototype, 'textContent', {
        set: function(value) {
            if (this.id && this.id.toLowerCase().includes('balance') || 
                this.className && this.className.toLowerCase().includes('balance')) {
                value = formatBalance(value);
            }
            originalTextSet.call(this, value);
        },
        configurable: true,
        enumerable: true
    });
})();


