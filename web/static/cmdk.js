// FunPay Hub - Command Palette (Ctrl+K)
// Linear / Raycast / Arc style global search
(function() {
  'use strict';

  // ===== STATIC INDEX: pages + actions =====
  const ITEMS = [
    // Navigation
    { type:'page', title:'Dashboard',       sub:'Главная страница',                url:'dashboard.html',       group:'Навигация', icon:'dashboard' },
    { type:'page', title:'Профиль',         sub:'Подключение FunPay',              url:'account.html',         group:'Навигация', icon:'user' },
    { type:'page', title:'Лоты',            sub:'Каталог твоих лотов',             url:'lots.html',            group:'Навигация', icon:'list' },
    { type:'page', title:'Баланс',          sub:'Доступный баланс и история',      url:'balance.html',         group:'Навигация', icon:'dollar' },
    { type:'page', title:'Заказы',          sub:'Активные и завершённые',          url:'orders.html',          group:'Навигация', icon:'box' },
    { type:'page', title:'Продажи',         sub:'История продаж',                  url:'sales.html',           group:'Навигация', icon:'chart' },
    { type:'page', title:'Покупатели',      sub:'База клиентов',                   url:'customers.html',       group:'Навигация', icon:'users' },
    { type:'page', title:'Уведомления',     sub:'Системные уведомления',           url:'notifications.html',   group:'Навигация', icon:'bell' },

    { type:'page', title:'Анализ рынка',    sub:'Сканирование цен конкурентов',    url:'market.html',          group:'Аналитика', icon:'bar' },
    { type:'page', title:'AI Советник',     sub:'Рекомендации искусственного интеллекта', url:'advisor.html', group:'Аналитика', icon:'brain' },
    { type:'page', title:'Сравнение цен',   sub:'Твои цены vs рынок',              url:'compare.html',         group:'Аналитика', icon:'compare' },
    { type:'page', title:'Оптимальная цена',sub:'Калькулятор оптимальной цены',    url:'optimal.html',         group:'Аналитика', icon:'target' },
    { type:'page', title:'Конкуренты',      sub:'Отслеживание продавцов',          url:'competitors.html',     group:'Аналитика', icon:'eye' },
    { type:'page', title:'Тепловая карта',  sub:'Активность 7×24',                 url:'heatmap.html',         group:'Аналитика', icon:'grid' },
    { type:'page', title:'Ниши',            sub:'Перспективные категории',         url:'niches.html',          group:'Аналитика', icon:'gem' },
    { type:'page', title:'Рейтинги',        sub:'Топ продавцов',                   url:'ratings.html',         group:'Аналитика', icon:'star' },
    { type:'page', title:'Маржа',           sub:'Калькулятор маржи',               url:'margin.html',          group:'Аналитика', icon:'dollar' },
    { type:'page', title:'Поставщики',      sub:'База поставщиков',                url:'suppliers.html',       group:'Аналитика', icon:'truck' },
    { type:'page', title:'Алерты рынка',    sub:'События рынка',                   url:'market_alerts.html',   group:'Аналитика', icon:'alert' },

    { type:'page', title:'Автоответы',      sub:'Шаблоны и правила',               url:'autoreply.html',       group:'Автоматизация', icon:'msg' },
    { type:'page', title:'Автовыдача',      sub:'Автоматическая доставка',         url:'autodelivery.html',    group:'Автоматизация', icon:'send' },
    { type:'page', title:'Планировщик',     sub:'Cron задачи',                     url:'automation.html',      group:'Автоматизация', icon:'zap' },

    { type:'page', title:'Плагины',         sub:'Управление плагинами',            url:'plugins.html',         group:'Система', icon:'puzzle' },
    { type:'page', title:'Системные алерты',sub:'Критические события',             url:'alerts.html',          group:'Система', icon:'alert' },
    { type:'page', title:'Логи',            sub:'Live стрим логов',                url:'logs.html',            group:'Система', icon:'file' },
    { type:'page', title:'Бэкапы',          sub:'Резервные копии',                 url:'system.html',          group:'Система', icon:'save' },

    { type:'page', title:'Внешний вид',     sub:'Темы, фон, звуки',                url:'appearance.html',      group:'Система', icon:'settings' },
    { type:'page', title:'Помощь',          sub:'Справка по разделам',             url:'help.html',            group:'Система', icon:'help' },

    // Actions
    { type:'action', title:'Создать бэкап',        sub:'Сохранить снимок настроек',   action:'createBackup',  group:'Действия', icon:'save' },
    { type:'action', title:'Собрать уведомления',  sub:'Опросить FunPay вручную',     action:'collectNotif',  group:'Действия', icon:'bell' },
    { type:'action', title:'Получить AI советы',   sub:'Запросить рекомендации',      action:'getAI',         group:'Действия', icon:'brain' },
    { type:'action', title:'Перезагрузить страницу', sub:'F5',                        action:'reload',        group:'Действия', icon:'refresh' },
    { type:'action', title:'Открыть FunPay.com',   sub:'Перейти на сайт',             action:'openFunpay',    group:'Действия', icon:'link' },
  ];

  // ===== ICONS (small SVG library) =====
  const ICONS = {
    dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/>',
    user:      '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    list:      '<path d="M4 7h16M4 12h16M4 17h10"/>',
    dollar:    '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    box:       '<path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/>',
    chart:     '<path d="M3 3v18h18"/><path d="M7 16l4-4 4 2 5-6"/>',
    users:     '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>',
    bell:      '<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>',
    bar:       '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
    brain:     '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    compare:   '<path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
    target:    '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    eye:       '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
    grid:      '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    gem:       '<path d="M6 3h12l4 6-10 13L2 9z"/>',
    star:      '<polygon points="12 2 15 8.5 22 9.3 17 14 18.2 21 12 17.8 5.8 21 7 14 2 9.3 9 8.5 12 2"/>',
    truck:     '<path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>',
    alert:     '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>',
    msg:       '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>',
    send:      '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    zap:       '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>',
    puzzle:    '<rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/>',
    file:      '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    save:      '<path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    settings:  '<circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2"/>',
    help:      '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    refresh:   '<path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10"/><path d="M20.49 15A9 9 0 015.64 18.36L1 14"/>',
    link:      '<path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>',
  };

  function ico(name) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor">${ICONS[name] || ICONS.dashboard}</svg>`;
  }

  // ===== ACTIONS =====
  const ACTIONS = {
    createBackup: async () => {
      try {
        const r = await fetch('/api/system/backups', { method:'POST' });
        if (r.ok) window.toast && window.toast('Бэкап создан', 'success');
        else window.toast && window.toast('Ошибка создания бэкапа', 'error');
      } catch(e) { window.toast && window.toast('Ошибка', 'error'); }
    },
    collectNotif: async () => {
      try {
        await fetch('/api/seller/notifications/collect', { method:'POST' });
        window.toast && window.toast('Уведомления собраны', 'success');
      } catch(e) { window.toast && window.toast('Ошибка', 'error'); }
    },
    getAI: async () => {
      try {
        await fetch('/api/ai/recommendations');
        window.toast && window.toast('AI рекомендации обновлены', 'success');
      } catch(e) { window.toast && window.toast('Ошибка', 'error'); }
    },
    reload: () => location.reload(),
    openFunpay: () => window.open('https://funpay.com', '_blank'),
  };

  // ===== BUILD UI =====
  const backdrop = document.createElement('div');
  backdrop.className = 'cmdk-backdrop';
  backdrop.innerHTML = `
    <div class="cmdk-modal" onclick="event.stopPropagation()">
      <div class="cmdk-search">
        <svg class="cmdk-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input id="cmdk-input" placeholder="Поиск страниц, действий..." autocomplete="off" />
        <span class="cmdk-hint">ESC</span>
      </div>
      <div class="cmdk-list" id="cmdk-list"></div>
      <div class="cmdk-footer">
        <span class="cmdk-footer-hint"><kbd>↑↓</kbd> навигация</span>
        <span class="cmdk-footer-hint"><kbd>↵</kbd> выбрать</span>
        <span class="cmdk-footer-hint"><kbd>ESC</kbd> закрыть</span>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  const input = backdrop.querySelector('#cmdk-input');
  const list  = backdrop.querySelector('#cmdk-list');
  let activeIdx = 0;
  let filtered = [];

  // ===== FILTER & RENDER =====
  function filter(q) {
    q = (q || '').trim().toLowerCase();
    if (!q) return ITEMS;

    // Fuzzy: split query into words, all must be found in title+sub
    const words = q.split(/\s+/);
    return ITEMS.filter(item => {
      const hay = (item.title + ' ' + item.sub).toLowerCase();
      return words.every(w => hay.indexOf(w) >= 0);
    });
  }

  function render() {
    if (!filtered.length) {
      list.innerHTML = '<div class="cmdk-empty">Ничего не найдено</div>';
      return;
    }

    // Group by section
    const groups = {};
    filtered.forEach((item, i) => {
      if (!groups[item.group]) groups[item.group] = [];
      groups[item.group].push({ item, i });
    });

    let html = '';
    Object.keys(groups).forEach(g => {
      html += `<div class="cmdk-section-title">${g}</div>`;
      groups[g].forEach(({ item, i }) => {
        const cls = i === activeIdx ? 'cmdk-item active' : 'cmdk-item';
        html += `
          <div class="${cls}" data-idx="${i}">
            <div class="cmdk-item-icon">${ico(item.icon)}</div>
            <div class="cmdk-item-text">
              <div class="cmdk-item-title">${item.title}</div>
              <div class="cmdk-item-sub">${item.sub || ''}</div>
            </div>
            <span class="cmdk-item-kbd">↵</span>
          </div>
        `;
      });
    });
    list.innerHTML = html;

    // Scroll active into view
    const act = list.querySelector('.cmdk-item.active');
    if (act) act.scrollIntoView({ block: 'nearest' });

    // Click handlers
    list.querySelectorAll('.cmdk-item').forEach(el => {
      el.addEventListener('click', () => {
        activeIdx = parseInt(el.dataset.idx);
        execute();
      });
    });
  }

  function execute() {
    const item = filtered[activeIdx];
    if (!item) return;
    close();
    if (item.type === 'page') {
      location.href = item.url;
    } else if (item.type === 'action') {
      const fn = ACTIONS[item.action];
      if (fn) fn();
    }
  }

  function open() {
    backdrop.classList.add('open');
    input.value = '';
    filtered = ITEMS;
    activeIdx = 0;
    render();
    setTimeout(() => input.focus(), 50);
  }

  function close() {
    backdrop.classList.remove('open');
  }

  // ===== EVENT BINDINGS =====
  backdrop.addEventListener('click', close);

  input.addEventListener('input', () => {
    filtered = filter(input.value);
    activeIdx = 0;
    render();
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = Math.min(activeIdx + 1, filtered.length - 1);
      render();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = Math.max(activeIdx - 1, 0);
      render();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      execute();
    } else if (e.key === 'Escape') {
      close();
    }
  });

  // Global hotkey: Ctrl+K (or Cmd+K)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (backdrop.classList.contains('open')) close();
      else open();
    }
  });

  // Expose for external triggers
  window.cmdk = { open, close };
})();