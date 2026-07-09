// FunPay Hub - Floating AI Widget (every page except assistant.html itself)
(function() {
  'use strict';

  // Skip on the dedicated assistant page
  if (location.pathname.indexOf('assistant.html') >= 0) return;

  let widgetConvId = null;
  let widgetMessages = [];
  let isSending = false;

  function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Simple markdown for widget
  function md(text) {
    if (!text) return '';
    let h = escapeHtml(text);
    h = h.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\n/g, '<br>');
    return h;
  }

  // ===== BUILD WIDGET =====
  const btn = document.createElement('button');
  btn.className = 'ai-widget-btn';
  btn.title = 'AI Ассистент (Ctrl+I)';
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 8V4H8"/><rect x="2" y="2" width="20" height="8" rx="2"/><path d="M2 12h20v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/><path d="M6 18h.01M10 18h.01"/></svg>';

  const panel = document.createElement('div');
  panel.className = 'ai-widget-panel';
  panel.innerHTML = `
    <div class="ai-widget-head">
      <div class="ai-widget-title">
        <span class="dot"></span>
        AI Ассистент
      </div>
      <div class="ai-widget-actions">
        <button title="Открыть полный чат" id="aiw-expand">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        </button>
        <button title="Закрыть" id="aiw-close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>
    <div class="ai-widget-body" id="aiw-body">
      <div class="ai-widget-empty">
        <div class="ai-welcome-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 8V4H8"/><rect x="2" y="2" width="20" height="8" rx="2"/><path d="M2 12h20v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/></svg>
        </div>
        <div>Привет! Спроси что-нибудь про FunPay Hub или текущую страницу.</div>
      </div>
    </div>
    <div class="ai-widget-input">
      <textarea id="aiw-input" placeholder="Спроси..." rows="1"></textarea>
      <button id="aiw-send" title="Отправить">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  const body  = panel.querySelector('#aiw-body');
  const input = panel.querySelector('#aiw-input');
  const send  = panel.querySelector('#aiw-send');

  function openPanel()  { panel.classList.add('open');  setTimeout(() => input.focus(), 100); }
  function closePanel() { panel.classList.remove('open'); }
  function togglePanel(){ panel.classList.contains('open') ? closePanel() : openPanel(); }

  btn.addEventListener('click', togglePanel);
  panel.querySelector('#aiw-close').addEventListener('click', closePanel);
  panel.querySelector('#aiw-expand').addEventListener('click', () => {
    location.href = 'assistant.html';
  });

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 80) + 'px';
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
  });

  send.addEventListener('click', doSend);

  // Hotkey: Ctrl+I to open widget
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'i') {
      e.preventDefault();
      togglePanel();
    }
  });

  function renderWidgetMessages() {
    if (!widgetMessages.length) return;
    body.innerHTML = widgetMessages.map(m => {
      const isUser = m.role === 'user';
      return `
        <div class="ai-msg ai-msg-${m.role}" style="margin-bottom:12px;">
          <div class="ai-msg-avatar ${isUser ? 'ai-msg-avatar-user' : 'ai-msg-avatar-bot'}" style="width:26px;height:26px;font-size:11px;">
            ${isUser ? 'Я' : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" style="width:13px;height:13px;"><path d="M12 8V4H8"/><rect x="2" y="2" width="20" height="8" rx="2"/><path d="M2 12h20v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/></svg>'}
          </div>
          <div class="ai-msg-body">
            <div class="ai-msg-content" style="font-size:12.5px;padding:8px 12px;">
              ${isUser ? escapeHtml(m.content).replace(/\n/g, '<br>') : md(m.content)}
            </div>
          </div>
        </div>
      `;
    }).join('');
    body.scrollTop = body.scrollHeight;
  }

  async function doSend() {
    if (isSending) return;
    const text = input.value.trim();
    if (!text) return;

    isSending = true;
    send.disabled = true;
    input.value = '';
    input.style.height = 'auto';

    widgetMessages.push({ role:'user', content:text });
    widgetMessages.push({ role:'assistant', content:'...' });
    renderWidgetMessages();

    try {
      const r = await fetch('/api/assistant/chat', {
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: widgetConvId,
        }),
      });
      const j = await r.json();
      widgetMessages.pop();
      if (j.ok) {
        widgetConvId = j.conversation_id;
        widgetMessages.push({ role:'assistant', content: j.reply });
      } else {
        widgetMessages.push({ role:'assistant', content: '⚠️ ' + (j.error || 'Ошибка') });
      }
      renderWidgetMessages();
    } catch(e) {
      widgetMessages.pop();
      widgetMessages.push({ role:'assistant', content: '⚠️ Ошибка: ' + e.message });
      renderWidgetMessages();
    }

    isSending = false;
    send.disabled = false;
    input.focus();
  }

  // Expose for cmdk
  window.aiWidget = { open: openPanel, close: closePanel, toggle: togglePanel };
})();