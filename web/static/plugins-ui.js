// FunPay Hub - Plugins page with Auto-UI configurator
(function() {
  'use strict';

  let currentPlugin = null;
  let currentSchema = [];
  let currentConfig = {};
  let categoriesCache = null;

  async function loadPlugins() {
    try {
      const r = await fetch('/api/plugins');
      const j = await r.json();
      renderList(j.plugins || []);
    } catch (e) { console.error('load plugins failed', e); }
  }

  function renderList(plugins) {
    const tbody = document.querySelector('table tbody');
    if (!tbody) return;
    if (!plugins.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Плагинов нет</td></tr>';
      return;
    }
    tbody.innerHTML = plugins.map(p => {
      const enabled = p.state === 'active' || p.state === 'running' || p.enabled;
      const stateBadge = stateBadgeHtml(p.state);
      return `
        <tr data-plugin="${escapeHtml(p.name)}">
          <td>
            <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(p.display_name || p.name)}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${escapeHtml(p.name)}</div>
          </td>
          <td class="mono">${escapeHtml(p.version || '0.0.0')}</td>
          <td>${stateBadge}</td>
          <td style="text-align:right;">
            <button class="plg-cfg-btn" onclick="openPluginSettings('${escapeHtml(p.name)}')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              Настроить
            </button>
            ${enabled
              ? `<button class="btn btn-sm btn-danger" onclick="togglePlugin('${escapeHtml(p.name)}', false)">Off</button>`
              : `<button class="btn btn-sm btn-primary" onclick="togglePlugin('${escapeHtml(p.name)}', true)">On</button>`
            }
            <button class="btn btn-sm btn-secondary" onclick="restartPlugin('${escapeHtml(p.name)}')">Restart</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  function stateBadgeHtml(state) {
    if (state === 'active' || state === 'running') return '<span class="badge badge-success">running</span>';
    if (state === 'disabled' || state === 'stopped') return '<span class="badge badge-muted">stopped</span>';
    if (state === 'error') return '<span class="badge badge-danger">error</span>';
    if (state === 'quarantined') return '<span class="badge badge-warn">quarantined</span>';
    return `<span class="badge badge-info">${escapeHtml(state || 'unknown')}</span>`;
  }

  async function loadCategories() {
    if (categoriesCache) return categoriesCache;
    try {
      const r = await fetch('/api/seller/lots');
      const j = await r.json();
      const lots = (j.lots || j || []);
      const map = {};
      lots.forEach(l => {
        const id = l.category_id || l.subcategory_id || l.cat_id;
        if (id) {
          const name = l.category_name || l.subcategory_name || `Категория ${id}`;
          map[id] = name;
        }
      });
      categoriesCache = Object.entries(map).map(([id, name]) => ({ id: parseInt(id), name }));
    } catch(e) { categoriesCache = []; }
    return categoriesCache;
  }

  window.openPluginSettings = async function(name) {
    currentPlugin = name;
    const backdrop = ensureModal();
    backdrop.classList.add('open');
    const body = backdrop.querySelector('.plg-modal-body');
    body.innerHTML = '<div class="empty-state">Загрузка...</div>';
    backdrop.querySelector('.plg-modal-title h3').textContent = name;
    try {
      const r = await fetch(`/api/plugins/${name}/schema`);
      const j = await r.json();
      currentSchema = j.schema || [];
      currentConfig = j.config || {};
      const info = j.plugin_info || {};
      backdrop.querySelector('.plg-modal-title h3').textContent = info.name || name;
      backdrop.querySelector('.plg-modal-title .sub').textContent = info.description || '';
      if (!currentSchema.length) {
        body.innerHTML = `<div class="empty-state">У этого плагина нет CONFIG_SCHEMA.<br>Настраивается через файл <code>configs/plugins/${name}.json</code>.</div>`;
        await appendStatsAndLogs(body, name);
        return;
      }
      body.innerHTML = await renderSchema(currentSchema, currentConfig);
      bindFieldEvents(body);
      await appendStatsAndLogs(body, name);
    } catch(e) {
      body.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">Ошибка: ${e.message}</div>`;
    }
  };

  function closeModal() {
    const b = document.querySelector('.plg-modal-backdrop');
    if (b) b.classList.remove('open');
  }
  window.closePluginSettings = closeModal;

  function ensureModal() {
    let backdrop = document.querySelector('.plg-modal-backdrop');
    if (backdrop) return backdrop;
    backdrop = document.createElement('div');
    backdrop.className = 'plg-modal-backdrop';
    backdrop.innerHTML = `
      <div class="plg-modal" onclick="event.stopPropagation()">
        <div class="plg-modal-head">
          <div class="plg-modal-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>
          </div>
          <div class="plg-modal-title">
            <h3>Plugin</h3>
            <div class="sub"></div>
          </div>
          <button class="plg-modal-close" onclick="closePluginSettings()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" style="width:16px;height:16px;"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="plg-modal-body"></div>
        <div class="plg-modal-foot">
          <button class="btn btn-secondary btn-sm" onclick="resetPluginConfig()">Сбросить к defaults</button>
          <div style="flex:1;"></div>
          <button class="btn btn-secondary btn-sm" onclick="closePluginSettings()">Закрыть</button>
          <button class="btn btn-primary btn-sm" onclick="savePluginConfig()">Сохранить</button>
        </div>
      </div>`;
    backdrop.addEventListener('click', closeModal);
    document.body.appendChild(backdrop);
    return backdrop;
  }

  async function renderSchema(schema, config) {
    const parts = [];
    for (const field of schema) parts.push(await renderField(field, config));
    return parts.join('');
  }

  async function renderField(f, cfg) {
    const key = f.key;
    const val = cfg[key] !== undefined ? cfg[key] : f.default;
    const hint = f.hint ? `<div class="plg-field-hint">${escapeHtml(f.hint)}</div>` : '';
    const label = `<div class="plg-field-label">${escapeHtml(f.label || key)}</div>`;

    switch ((f.type || 'text').toLowerCase()) {
      case 'toggle': {
        const checked = val ? 'checked' : '';
        return `<div class="plg-field" data-key="${key}" data-type="toggle">${label}${hint}<label class="plg-toggle"><input type="checkbox" ${checked}><span class="plg-toggle-track"><span class="plg-toggle-thumb"></span></span><span class="plg-toggle-status">${val ? 'Включено' : 'Выключено'}</span></label></div>`;
      }
      case 'slider':
      case 'range': {
        const min = f.min != null ? f.min : 0;
        const max = f.max != null ? f.max : 100;
        const step = f.step != null ? f.step : 1;
        const suffix = f.suffix || '';
        return `<div class="plg-field" data-key="${key}" data-type="slider" data-suffix="${escapeHtml(suffix)}">${label}${hint}<div class="plg-slider-wrap"><input type="range" class="plg-slider range" min="${min}" max="${max}" step="${step}" value="${val}"><span class="plg-slider-val">${val}${escapeHtml(suffix)}</span></div></div>`;
      }
      case 'number':
        return `<div class="plg-field" data-key="${key}" data-type="number">${label}${hint}<input class="plg-input" type="number" value="${val ?? ''}" ${f.min!=null?`min="${f.min}"`:''} ${f.max!=null?`max="${f.max}"`:''} ${f.step!=null?`step="${f.step}"`:''}></div>`;
      case 'text':
      case 'string':
        return `<div class="plg-field" data-key="${key}" data-type="text">${label}${hint}<input class="plg-input" type="text" value="${escapeHtml(val || '')}" placeholder="${escapeHtml(f.placeholder || '')}"></div>`;
      case 'password':
        return `<div class="plg-field" data-key="${key}" data-type="password">${label}${hint}<input class="plg-input" type="password" value="${escapeHtml(val || '')}"></div>`;
      case 'textarea':
        return `<div class="plg-field" data-key="${key}" data-type="textarea">${label}${hint}<textarea class="plg-textarea" rows="${f.rows || 4}">${escapeHtml(val || '')}</textarea></div>`;
      case 'select': {
        const opts = (f.options || []).map(o => {
          const v = typeof o === 'object' ? o.value : o;
          const lbl = typeof o === 'object' ? o.label : o;
          const sel = v == val ? 'selected' : '';
          return `<option value="${escapeHtml(v)}" ${sel}>${escapeHtml(lbl)}</option>`;
        }).join('');
        return `<div class="plg-field" data-key="${key}" data-type="select">${label}${hint}<select class="plg-select">${opts}</select></div>`;
      }
            case 'lot_mapping': {
        // val = { "lot_id": {"service_id": 1, "quantity": 100, "service_name": "..."} }
        const entries = val && typeof val === 'object' ? Object.entries(val) : [];
        const rowsHtml = entries.map(([lotId, m], idx) => `
          <div class="plg-map-row" data-idx="${idx}">
            <input class="plg-input plg-map-lot"      placeholder="FunPay Lot ID" value="${escapeHtml(lotId)}" />
            <input class="plg-input plg-map-svc"      placeholder="Twiboost Service ID" value="${escapeHtml(String(m.service_id || ''))}" />
            <input class="plg-input plg-map-qty"      placeholder="Кол-во" value="${escapeHtml(String(m.quantity || ''))}" />
            <input class="plg-input plg-map-name"     placeholder="Название (для логов)" value="${escapeHtml(m.service_name || '')}" />
            <button type="button" class="plg-map-del" onclick="this.parentElement.remove()">×</button>
          </div>
        `).join('');
        return `
          <div class="plg-field" data-key="${key}" data-type="lot_mapping">
            ${label}${hint}
            <div class="plg-map-list" id="plg-map-${key}">
              ${rowsHtml}
            </div>
            <div style="display:flex;gap:8px;margin-top:8px;">
              <button type="button" class="btn btn-sm btn-secondary" onclick="addMapRow('${key}')">
                + Добавить связку
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="showServicesList()">
                📋 Показать услуги Twiboost
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="showMyLots()">
                📦 Мои лоты FunPay
              </button>
            </div>
            <div class="plg-field-hint" style="margin-top:6px;">
              FunPay Lot ID берёшь из URL лота, Service ID — из списка Twiboost
            </div>
          </div>`;
      }
      case 'categories': {
        const cats = await loadCategories();
        const selected = new Set((val || []).map(x => parseInt(x)));
        if (!cats.length) {
          return `<div class="plg-field" data-key="${key}" data-type="categories">${label}${hint}<div class="plg-cats"><div class="muted" style="padding:8px;font-size:12px;">Категории не найдены. Подключи аккаунт FunPay.</div></div></div>`;
        }
        const chips = cats.map(c => {
          const active = selected.has(c.id) ? 'active' : '';
          return `<span class="plg-cat-chip ${active}" data-id="${c.id}">${escapeHtml(c.name)} <span class="muted" style="opacity:0.6;">#${c.id}</span></span>`;
        }).join('');
        return `<div class="plg-field" data-key="${key}" data-type="categories">${label}${hint}<div class="plg-cats">${chips}</div><div class="plg-field-hint" style="margin-top:6px;">Клик по категории — добавить/убрать. Пусто = все.</div></div>`;
      }
      default:
        return `<div class="plg-field" data-key="${key}" data-type="text">${label}${hint}<input class="plg-input" type="text" value="${escapeHtml(String(val ?? ''))}"></div>`;
    }
  }

  function bindFieldEvents(root) {
    root.querySelectorAll('[data-type="toggle"] input').forEach(el => {
      el.addEventListener('change', () => {
        const status = el.parentElement.querySelector('.plg-toggle-status');
        if (status) status.textContent = el.checked ? 'Включено' : 'Выключено';
      });
    });
    root.querySelectorAll('[data-type="slider"]').forEach(field => {
      const slider = field.querySelector('.plg-slider');
      const val = field.querySelector('.plg-slider-val');
      const suffix = field.dataset.suffix || '';
      slider.addEventListener('input', () => { val.textContent = slider.value + suffix; });
    });
    root.querySelectorAll('[data-type="categories"] .plg-cat-chip').forEach(chip => {
      chip.addEventListener('click', () => chip.classList.toggle('active'));
    });
  }

  function collectConfig(root) {
    const result = {};
    root.querySelectorAll('.plg-field').forEach(field => {
      const key = field.dataset.key;
      const type = field.dataset.type;
      switch (type) {
        case 'toggle': result[key] = field.querySelector('input').checked; break;
        case 'slider':
        case 'number': {
          const v = parseFloat(field.querySelector('input').value);
          result[key] = isNaN(v) ? null : v;
          break;
        }
        case 'text':
        case 'password': result[key] = field.querySelector('input').value; break;
        case 'textarea': result[key] = field.querySelector('textarea').value; break;
        case 'select': result[key] = field.querySelector('select').value; break;
              case 'lot_mapping': {
        // val = { "lot_id": {"service_id": 1, "quantity": 100, "service_name": "..."} }
        const entries = val && typeof val === 'object' ? Object.entries(val) : [];
        const rowsHtml = entries.map(([lotId, m], idx) => `
          <div class="plg-map-row" data-idx="${idx}">
            <input class="plg-input plg-map-lot"      placeholder="FunPay Lot ID" value="${escapeHtml(lotId)}" />
            <input class="plg-input plg-map-svc"      placeholder="Twiboost Service ID" value="${escapeHtml(String(m.service_id || ''))}" />
            <input class="plg-input plg-map-qty"      placeholder="Кол-во" value="${escapeHtml(String(m.quantity || ''))}" />
            <input class="plg-input plg-map-name"     placeholder="Название (для логов)" value="${escapeHtml(m.service_name || '')}" />
            <button type="button" class="plg-map-del" onclick="this.parentElement.remove()">×</button>
          </div>
        `).join('');
        return `
          <div class="plg-field" data-key="${key}" data-type="lot_mapping">
            ${label}${hint}
            <div class="plg-map-list" id="plg-map-${key}">
              ${rowsHtml}
            </div>
            <div style="display:flex;gap:8px;margin-top:8px;">
              <button type="button" class="btn btn-sm btn-secondary" onclick="addMapRow('${key}')">
                + Добавить связку
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="showServicesList()">
                📋 Показать услуги Twiboost
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="showMyLots()">
                📦 Мои лоты FunPay
              </button>
            </div>
            <div class="plg-field-hint" style="margin-top:6px;">
              FunPay Lot ID берёшь из URL лота, Service ID — из списка Twiboost
            </div>
          </div>`;
      }
      case 'categories': {
          const ids = [];
          field.querySelectorAll('.plg-cat-chip.active').forEach(c => ids.push(parseInt(c.dataset.id)));
          result[key] = ids;
          break;
        }
      }
    });
    return result;
  }

  window.savePluginConfig = async function() {
    if (!currentPlugin) return;
    const backdrop = document.querySelector('.plg-modal-backdrop');
    const body = backdrop.querySelector('.plg-modal-body');
    const userCfg = collectConfig(body);

    // Merge with current config to preserve system fields (priority, enabled, etc.)
    const merged = Object.assign({}, currentConfig || {}, userCfg);

    // Ensure required system fields are present
    if (merged.priority === undefined) merged.priority = 10;
    if (merged.enabled === undefined) merged.enabled = false;

    try {
      const r = await fetch(`/api/plugins/${currentPlugin}/config`, {
        method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(merged),
      });
      if (r.ok) {
        window.toast && window.toast('Сохранено', 'success');
        currentConfig = merged;  // update local cache
      } else {
        const err = await r.json().catch(() => ({}));
        window.toast && window.toast('Ошибка: ' + (err.error || r.status), 'error');
      }
    } catch(e) { window.toast && window.toast('Ошибка: ' + e.message, 'error'); }
  };

  window.resetPluginConfig = async function() {
    if (!currentPlugin) return;
    if (!confirm('Сбросить настройки к defaults?')) return;
    try {
      const r = await fetch(`/api/plugins/${currentPlugin}/reset`, { method:'POST' });
      if (r.ok) {
        window.toast && window.toast('Сброшено', 'info');
        openPluginSettings(currentPlugin);
      }
    } catch(e) {}
  };

  window.callPluginAction = async function(actionName) {
    if (!currentPlugin) return;
    try {
      const r = await fetch(`/api/plugins/${currentPlugin}/action/${actionName}`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({}),
      });
      const j = await r.json();
      if (j.ok) {
        window.toast && window.toast(j.result?.message || 'OK', 'success');
        const body = document.querySelector('.plg-modal-body');
        if (body) {
          body.querySelectorAll('[data-section="stats"]').forEach(el => el.remove());
          await appendStatsAndLogs(body, currentPlugin);
        }
      } else { window.toast && window.toast(j.error || 'Ошибка', 'error'); }
    } catch(e) { window.toast && window.toast(e.message, 'error'); }
  };

  async function appendStatsAndLogs(body, name) {
    try {
      const r = await fetch(`/api/plugins/${name}/logs`);
      const j = await r.json();
      const stats = j.stats || {};
      const logs = j.logs || [];

      const statsHtml = Object.keys(stats).length ? `
        <div class="plg-section-title" data-section="stats">Статистика</div>
        <div class="plg-stats-grid" data-section="stats">
          ${Object.entries(stats).filter(([k,v]) => typeof v !== 'object').map(([k, v]) => `
            <div class="plg-stat">
              <div class="plg-stat-label">${escapeHtml(k)}</div>
              <div class="plg-stat-value">${escapeHtml(String(v == null ? '—' : v))}</div>
            </div>`).join('')}
        </div>` : '';

      const actionsHtml = name === 'autobump_plugin' ? `
        <div class="plg-section-title" data-section="stats">Действия</div>
        <div data-section="stats" style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" onclick="callPluginAction('test_bump')">▶ Test bump</button>
          <button class="btn btn-sm btn-secondary" onclick="callPluginAction('reset_stats')">Сбросить статистику</button>
        </div>` : '';

      const logsHtml = logs.length ? `
        <div class="plg-section-title" data-section="stats">Последние действия</div>
        <div class="plg-logs" data-section="stats">
          ${logs.slice().reverse().map(l => `
            <div class="plg-log-row">
              <span class="plg-log-time">${escapeHtml(l.time || '')}</span>
              <span class="plg-log-${l.level === 'warn' ? 'warn' : l.level === 'error' ? 'err' : 'info'}">${escapeHtml(l.message || '')}</span>
            </div>`).join('')}
        </div>` : '';

      body.insertAdjacentHTML('beforeend', actionsHtml + statsHtml + logsHtml);
    } catch(e) {}
  }

  window.togglePlugin = async function(name, enable) {
    const ep = enable ? 'enable' : 'disable';
    const r = await fetch(`/api/plugins/${name}/${ep}`, { method:'POST' });
    if (r.ok) {
      window.toast && window.toast(enable ? 'Включён' : 'Выключен', 'success');
      loadPlugins();
    } else { window.toast && window.toast('Ошибка', 'error'); }
  };

  window.restartPlugin = async function(name) {
    const r = await fetch(`/api/plugins/${name}/restart`, { method:'POST' });
    if (r.ok) { window.toast && window.toast('Перезапущен', 'info'); loadPlugins(); }
  };


  // ====== Lot mapping helpers ======
  window.addMapRow = function(key) {
    const list = document.getElementById('plg-map-' + key);
    if (!list) return;
    const idx = list.querySelectorAll('.plg-map-row').length;
    const row = document.createElement('div');
    row.className = 'plg-map-row';
    row.dataset.idx = idx;
    row.innerHTML = `
      <input class="plg-input plg-map-lot"  placeholder="FunPay Lot ID" />
      <input class="plg-input plg-map-svc"  placeholder="Twiboost Service ID" />
      <input class="plg-input plg-map-qty"  placeholder="Кол-во" />
      <input class="plg-input plg-map-name" placeholder="Название (для логов)" />
      <button type="button" class="plg-map-del" onclick="this.parentElement.remove()">×</button>
    `;
    list.appendChild(row);
  };

  window.showServicesList = async function() {
    if (!currentPlugin) return;
    if (window.toast) window.toast('Загружаю список услуг Twiboost...', 'info');
    try {
      const r = await fetch(`/api/plugins/${currentPlugin}/action/load_services`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'
      });
      const j = await r.json();
      if (!j.ok || !j.result?.services) {
        window.toast && window.toast('Ошибка: ' + (j.result?.error || 'unknown'), 'error');
        return;
      }
      const services = j.result.services;
      showServicesModal(services);
    } catch(e) {
      window.toast && window.toast('Ошибка: ' + e.message, 'error');
    }
  };

  function showServicesModal(services) {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const box = document.createElement('div');
    box.style.cssText = 'background:rgba(8,17,32,0.98);border:1px solid var(--panel-border);border-radius:14px;padding:20px;max-width:1000px;width:100%;max-height:85vh;display:flex;flex-direction:column;';

    const search = document.createElement('input');
    search.className = 'plg-input';
    search.placeholder = 'Поиск по названию/категории (vk, telegram, instagram...)';
    search.style.cssText = 'margin-bottom:12px;';

    const listDiv = document.createElement('div');
    listDiv.style.cssText = 'overflow-y:auto;flex:1;font-family:monospace;font-size:12px;';

    function render(filter) {
      const f = filter.trim().toLowerCase();
      const filtered = f
        ? services.filter(s => (s.name + ' ' + (s.category||'')).toLowerCase().includes(f))
        : services.slice(0, 200);
      listDiv.innerHTML = filtered.map(s => `
        <div style="display:grid;grid-template-columns:60px 1fr 80px 100px;gap:8px;padding:6px 4px;border-bottom:1px solid rgba(100,180,255,0.05);cursor:pointer;"
             onclick="copyServiceId(${s.service})">
          <span style="color:var(--accent-cyan);font-weight:bold;">#${s.service}</span>
          <span>${escapeHtml(s.name)}</span>
          <span style="color:var(--text-muted);">${s.rate}/1k</span>
          <span style="color:var(--text-muted);">min ${s.min}</span>
        </div>
      `).join('') || '<div style="padding:20px;text-align:center;color:var(--text-muted);">Ничего не найдено</div>';
    }

    search.oninput = () => render(search.value);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-secondary';
    closeBtn.textContent = 'Закрыть';
    closeBtn.style.marginTop = '10px';
    closeBtn.onclick = () => overlay.remove();

    box.appendChild(search);
    box.appendChild(listDiv);
    box.appendChild(closeBtn);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    render('');
    setTimeout(() => search.focus(), 50);
  }

  window.copyServiceId = function(id) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(String(id)).then(() => {
        window.toast && window.toast(`Скопирован Service ID: ${id}`, 'success');
      });
    } else {
      window.toast && window.toast(`Service ID: ${id}`, 'info');
    }
  };

  window.showMyLots = async function() {
    if (window.toast) window.toast('Загружаю твои лоты...', 'info');
    try {
      const r = await fetch('/api/seller/lots');
      const j = await r.json();
      const lots = j.lots || j || [];
      if (!Array.isArray(lots) || !lots.length) {
        window.toast && window.toast('Лотов не найдено', 'warn');
        return;
      }
      showLotsModal(lots);
    } catch(e) {
      window.toast && window.toast('Ошибка: ' + e.message, 'error');
    }
  };

  function showLotsModal(lots) {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const box = document.createElement('div');
    box.style.cssText = 'background:rgba(8,17,32,0.98);border:1px solid var(--panel-border);border-radius:14px;padding:20px;max-width:900px;width:100%;max-height:85vh;display:flex;flex-direction:column;';

    const listDiv = document.createElement('div');
    listDiv.style.cssText = 'overflow-y:auto;flex:1;font-family:monospace;font-size:12px;';

    listDiv.innerHTML = lots.map(l => `
      <div style="display:grid;grid-template-columns:90px 1fr 100px;gap:8px;padding:6px 4px;border-bottom:1px solid rgba(100,180,255,0.05);cursor:pointer;"
           onclick="copyLotId('${escapeHtml(String(l.id || l.lot_id || ''))}')">
        <span style="color:var(--accent-cyan);font-weight:bold;">#${escapeHtml(String(l.id || l.lot_id || ''))}</span>
        <span>${escapeHtml(l.title || l.description || '—')}</span>
        <span style="color:var(--text-muted);">${escapeHtml(String(l.price || ''))}</span>
      </div>
    `).join('') || '<div style="padding:20px;text-align:center;">Лотов нет</div>';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-secondary';
    closeBtn.textContent = 'Закрыть';
    closeBtn.style.marginTop = '10px';
    closeBtn.onclick = () => overlay.remove();

    box.innerHTML = '<h3 style="margin:0 0 12px 0;">Твои лоты на FunPay (клик = копировать ID)</h3>';
    box.appendChild(listDiv);
    box.appendChild(closeBtn);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  }

  window.copyLotId = function(id) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(String(id)).then(() => {
        window.toast && window.toast(`Скопирован Lot ID: ${id}`, 'success');
      });
    } else {
      window.toast && window.toast(`Lot ID: ${id}`, 'info');
    }
  };

    function escapeHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadPlugins();
    setInterval(loadPlugins, 10000);
    const refreshBtn = document.querySelector('button[onclick*="loadPlugins"]');
    if (refreshBtn) refreshBtn.onclick = loadPlugins;
  });

  window.loadPlugins = loadPlugins;
})();