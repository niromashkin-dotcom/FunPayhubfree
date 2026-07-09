// FunPay Hub - AI Assistant Frontend
(function() {
  'use strict';

  let currentConvId = null;
  let conversations = [];
  let isSending = false;

  // ===== MARKDOWN RENDERING (simple) =====
  function md(text) {
    if (!text) return '';
    let html = text
      // escape
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // code blocks ```...```
    html = html.replace(/```([\s\S]*?)```/g, (_, code) =>
      `<pre><code>${code.trim()}</code></pre>`);

    // inline code `...`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // bold **text**
    html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');

    // italic *text*
    html = html.replace(/(?<!\*)\*([^\*\n]+)\*(?!\*)/g, '<em>$1</em>');

    // links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // headings
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');

    // bullet lists
    html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>(\n?<li>.*?<\/li>)*)/gs,
      '<ul>$1</ul>');

    // numbered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<oli>$1</oli>');
    html = html.replace(/(<oli>.*?<\/oli>(\n?<oli>.*?<\/oli>)*)/gs,
      m => '<ol>' + m.replace(/<\/?oli>/g, m2 => m2 === '<oli>' ? '<li>' : '</li>') + '</ol>');

    // paragraphs (split by double newline)
    const blocks = html.split(/\n\n+/).map(b => {
      b = b.trim();
      if (!b) return '';
      if (b.startsWith('<')) return b;
      return '<p>' + b.replace(/\n/g, '<br>') + '</p>';
    });

    return blocks.join('\n');
  }

  // ===== TIME =====
  function timeAgo(ts) {
    const diff = Math.floor(Date.now() / 1000) - ts;
    if (diff < 60) return 'только что';
    if (diff < 3600) return Math.floor(diff / 60) + ' мин';
    if (diff < 86400) return Math.floor(diff / 3600) + ' ч';
    const d = new Date(ts * 1000);
    return d.toLocaleDateString('ru-RU');
  }

  // ===== HISTORY =====
  async function loadHistory() {
    try {
      const r = await fetch('/api/assistant/history');
      const j = await r.json();
      conversations = j.conversations || [];
      renderConvList();
    } catch(e) {
      console.warn('history load failed', e);
    }
  }

  function renderConvList() {
    const list = document.getElementById('ai-conv-list');
    if (!list) return;
    if (!conversations.length) {
      list.innerHTML = '<div class="ai-empty">Нет чатов</div>';
      return;
    }
    list.innerHTML = conversations.map(c => `
      <div class="ai-conv-item ${c.id === currentConvId ? 'active' : ''}" data-id="${c.id}">
        <div class="ai-conv-title">${escapeHtml(c.title || 'Без названия')}</div>
        <div class="ai-conv-time">${timeAgo(c.updated_at || c.created_at)}</div>
        <button class="ai-conv-del" data-id="${c.id}" title="Удалить">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    `).join('');

    list.querySelectorAll('.ai-conv-item').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('.ai-conv-del')) return;
        openConversation(el.dataset.id);
      });
    });
    list.querySelectorAll('.ai-conv-del').forEach(el => {
      el.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Удалить этот чат?')) return;
        const id = el.dataset.id;
        await fetch(`/api/assistant/conversation/${id}`, { method:'DELETE' });
        if (id === currentConvId) newConversation();
        loadHistory();
      });
    });
  }

  function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function openConversation(id) {
    const conv = conversations.find(c => c.id === id);
    if (!conv) return;
    currentConvId = id;
    renderMessages(conv.messages || []);
    renderConvList();
  }

  function newConversation() {
    currentConvId = null;
    renderMessages([]);
    renderConvList();
    const input = document.getElementById('ai-input');
    if (input) input.focus();
  }
  window.newConversation = newConversation;

  // ===== MESSAGES =====
  function renderMessages(messages) {
    const cont = document.getElementById('ai-messages');
    if (!cont) return;

    if (!messages.length) {
      // Show welcome screen
      cont.innerHTML = document.getElementById('ai-welcome-tpl')?.innerHTML || welcomeHtml();
      bindSuggestions();
      return;
    }

    cont.innerHTML = messages.map(m => renderMessage(m)).join('');
    cont.scrollTop = cont.scrollHeight;
  }

  function renderMessage(m) {
    const isUser = m.role === 'user';
    const avatar = isUser
      ? '<div class="ai-msg-avatar ai-msg-avatar-user">Я</div>'
      : '<div class="ai-msg-avatar ai-msg-avatar-bot"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 8V4H8"/><rect x="2" y="2" width="20" height="8" rx="2"/><path d="M2 12h20v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/></svg></div>';

    const provider = m.provider ? `<span class="ai-msg-provider">${m.provider}</span>` : '';
    const content = isUser ? `<p>${escapeHtml(m.content).replace(/\n/g, '<br>')}</p>` : md(m.content);

    return `
      <div class="ai-msg ai-msg-${m.role}">
        ${avatar}
        <div class="ai-msg-body">
          <div class="ai-msg-content">${content}</div>
          ${provider}
        </div>
      </div>
    `;
  }

  function welcomeHtml() {
    return `
      <div class="ai-welcome">
        <div class="ai-welcome-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 8V4H8"/><rect x="2" y="2" width="20" height="8" rx="2"/><path d="M2 12h20v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/><path d="M6 18h.01M10 18h.01"/></svg>
        </div>
        <h2>Привет! Я AI ассистент FunPay Hub</h2>
        <p>Спроси меня о настройках, плагинах, ценах, конкурентах.</p>
        <div class="ai-suggestions">
          <button class="ai-suggest">Как настроить автоответы?</button>
          <button class="ai-suggest">Как подключить FunPay аккаунт?</button>
          <button class="ai-suggest">Какие плагины посоветуешь?</button>
          <button class="ai-suggest">Как настроить автовыдачу?</button>
        </div>
      </div>
    `;
  }

  function bindSuggestions() {
    document.querySelectorAll('.ai-suggest').forEach(b => {
      b.addEventListener('click', () => askSuggested(b));
    });
  }

  function askSuggested(btn) {
    const text = btn.textContent.trim();
    const input = document.getElementById('ai-input');
    if (input) {
      input.value = text;
      sendMessage();
    }
  }
  window.askSuggested = askSuggested;

  // ===== SEND MESSAGE =====
  async function sendMessage() {
    if (isSending) return;
    const input = document.getElementById('ai-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    isSending = true;
    const sendBtn = document.getElementById('ai-send');
    if (sendBtn) sendBtn.disabled = true;

    // Get or create current messages array
    let conv = conversations.find(c => c.id === currentConvId);
    let messages = conv ? conv.messages.slice() : [];

    // Optimistic UI
    messages.push({ role:'user', content:text, ts:Math.floor(Date.now()/1000) });
    messages.push({ role:'assistant', content:'...', ts:Math.floor(Date.now()/1000), _typing:true });
    renderMessages(messages);

    input.value = '';
    autoResize(input);

    try {
      const r = await fetch('/api/assistant/chat', {
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: currentConvId,
        }),
      });
      const j = await r.json();

      if (!j.ok) {
        messages.pop(); // remove typing indicator
        messages.push({ role:'assistant', content:'⚠️ Ошибка: ' + (j.error || 'unknown'), ts:Math.floor(Date.now()/1000) });
        renderMessages(messages);
      } else {
        currentConvId = j.conversation_id;
        await loadHistory();
        // Reload current conv
        conv = conversations.find(c => c.id === currentConvId);
        if (conv) renderMessages(conv.messages || []);
      }
    } catch(e) {
      messages.pop();
      messages.push({ role:'assistant', content:'⚠️ Ошибка соединения: ' + e.message, ts:Math.floor(Date.now()/1000) });
      renderMessages(messages);
    }

    isSending = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
  window.sendMessage = sendMessage;

  // ===== INPUT HANDLING =====
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
  window.handleKey = handleKey;

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }

  // ===== AI SETTINGS MODAL =====
  async function openAiSettings() {
    const modal = document.getElementById('ai-settings-modal');
    if (!modal) return;
    try {
      const r = await fetch('/api/assistant/keys');
      const j = await r.json();
      // Mask keys (just show if set)
      document.getElementById('ai-openai-key').value = j.openai_set ? '••••••••••••' : '';
      document.getElementById('ai-groq-key').value   = j.groq_set   ? '••••••••••••' : '';
      const orEl = document.getElementById('ai-openrouter-key');
      if (orEl) orEl.value = j.openrouter_set ? '••••••••••••' : '';
      document.getElementById('ai-provider').value   = j.provider || 'auto';
      document.getElementById('ai-model').value      = j.model || '';
    } catch(e) {}
    modal.classList.add('open');
  }
  window.openAiSettings = openAiSettings;

  function closeAiSettings(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('ai-settings-modal').classList.remove('open');
  }
  window.closeAiSettings = closeAiSettings;

  async function saveAiSettings() {
    const openai = document.getElementById('ai-openai-key').value;
    const groq   = document.getElementById('ai-groq-key').value;
    const orEl   = document.getElementById('ai-openrouter-key');
    const openrouter = orEl ? orEl.value : '';
    const provider = document.getElementById('ai-provider').value;
    const model    = document.getElementById('ai-model').value;

    const body = { provider, model };
    if (openai     && !openai.startsWith('•'))     body.openai = openai;
    if (groq       && !groq.startsWith('•'))       body.groq   = groq;
    if (openrouter && !openrouter.startsWith('•')) body.openrouter = openrouter;

    await fetch('/api/assistant/keys', {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify(body),
    });

    window.toast && window.toast('Сохранено', 'success');
    closeAiSettings();
    updateProviderHint();
  }
  window.saveAiSettings = saveAiSettings;

  async function clearAllChats() {
    if (!confirm('Удалить ВСЕ чаты? Это нельзя отменить.')) return;
    await fetch('/api/assistant/history', { method:'DELETE' });
    conversations = [];
    newConversation();
    window.toast && window.toast('Все чаты удалены', 'info');
  }
  window.clearAllChats = clearAllChats;

  // ===== PROVIDER HINT =====
  async function updateProviderHint() {
    const hint = document.getElementById('ai-provider-hint');
    if (!hint) return;
    try {
      const r = await fetch('/api/assistant/keys');
      const j = await r.json();
      const parts = [];
      if (j.openrouter_set) parts.push('🌍 OpenRouter');
      if (j.openai_set)     parts.push('OpenAI');
      if (j.groq_set)       parts.push('Groq');
      if (parts.length) {
        hint.innerHTML = '✅ Подключено: ' + parts.join(' + ');
      } else {
        hint.innerHTML = '⚠️ Нет API ключа — отвечаю из базы знаний. <a href="#" onclick="openAiSettings();return false;">Подключить AI →</a>';
      }
    } catch(e) {}
  }

  // ===== INIT =====
  document.addEventListener('DOMContentLoaded', async () => {
    const input = document.getElementById('ai-input');
    if (input) {
      input.addEventListener('input', () => autoResize(input));
    }
    await loadHistory();
    updateProviderHint();
    bindSuggestions();
  });

})();