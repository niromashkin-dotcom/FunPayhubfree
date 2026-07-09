// autosmm_niches_v3.4 — UI этапа B (Мои / Глобальные + прогресс-бар + Platform)
// Работает как раньше: IIFE, DOMContentLoaded, table with checkboxes.
(function(){
  var $ = function(id){ return document.getElementById(id); };

  function log(msg){
    var el = $('niches-log');
    if(!el) return;
    var t = new Date().toLocaleTimeString('ru-RU', {hour12:false});
    el.textContent = '['+t+'] ' + msg + '\n' + (el.textContent || '');
    if(el.textContent.length > 4000) el.textContent = el.textContent.substring(0, 4000);
  }
  function toast(msg, type){
    if(window.showToast){ window.showToast(msg, type||'info'); return; }
    console.log('['+type+'] '+msg);
  }
  function meta(text){
    var el = $('niches-meta');
    if(el) el.innerHTML = text;
  }

  // ==== Инжект контролов режима + progress bar ====
  function injectControls(){
    var metaEl = $('niches-meta');
    if(!metaEl) return;
    if(document.getElementById('niches-mode-wrap')) return; // уже вставлено

    var wrap = document.createElement('div');
    wrap.id = 'niches-mode-wrap';
    wrap.style.cssText = 'display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px;';
    wrap.innerHTML = ''
      + '<div style="display:flex;gap:6px;background:rgba(90,140,255,.08);padding:4px;border-radius:10px;">'
      +   '<button id="niches-mode-my"     class="btn btn-sm btn-primary"   style="min-width:120px">🏠 Мои ниши</button>'
      +   '<button id="niches-mode-global" class="btn btn-sm btn-secondary" style="min-width:160px">🌐 По всему рынку</button>'
      +   '<button id="niches-mode-deep"   class="btn btn-sm btn-secondary" style="min-width:170px">🔬 Глубокий (все 1751)</button>'
      + '</div>'
      + '<div id="niches-mode-hint" style="opacity:.7;font-size:.9em;">Быстрый поиск по прогретым категориям (heatmap)</div>';
    metaEl.parentNode.insertBefore(wrap, metaEl);

    // Прогресс-бар (скрыт по умолчанию)
    var pb = document.createElement('div');
    pb.id = 'niches-progress-wrap';
    pb.style.cssText = 'display:none;margin:10px 0;padding:10px;background:rgba(90,140,255,.06);border:1px solid rgba(90,140,255,.25);border-radius:10px;';
    pb.innerHTML = ''
      + '<div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:.9em;">'
      +   '<span id="niches-progress-label">Сканирую…</span>'
      +   '<span id="niches-progress-percent">0%</span>'
      + '</div>'
      + '<div style="height:8px;background:rgba(0,0,0,.2);border-radius:4px;overflow:hidden;">'
      +   '<div id="niches-progress-bar" style="height:100%;width:0%;background:linear-gradient(90deg,#5a8cff,#7fb2ff);transition:width .3s ease;"></div>'
      + '</div>'
      + '<div id="niches-progress-detail" style="margin-top:6px;font-size:.8em;opacity:.7;"></div>';
    metaEl.parentNode.insertBefore(pb, metaEl);

    var modeBtns = [myBtn = $('niches-mode-my'), glBtn = $('niches-mode-global'), deepBtn = $('niches-mode-deep')];
    [myBtn, glBtn, deepBtn].forEach(function(b){
      if(!b) return;
      b.addEventListener('click', function(){
        if(b === myBtn) setMode('my');
        else if(b === glBtn) setMode('global');
        else setMode('deep');
      });
    });
  }

  var MODE = 'my'; // 'my' | 'global' | 'deep'

  function setMode(m){
    MODE = m;
    var my = $('niches-mode-my'), gl = $('niches-mode-global'), deep = $('niches-mode-deep'), hint = $('niches-mode-hint');
    if(my && gl && deep){
      if(m === 'my'){
        my.className = 'btn btn-sm btn-primary';
        gl.className = 'btn btn-sm btn-secondary';
        deep.className = 'btn btn-sm btn-secondary';
        if(hint) hint.textContent = 'Быстрый поиск по прогретым категориям (heatmap)';
      } else if(m === 'global'){
        my.className = 'btn btn-sm btn-secondary';
        gl.className = 'btn btn-sm btn-primary';
        deep.className = 'btn btn-sm btn-secondary';
        if(hint) hint.textContent = '🌐 Полный скан всех SMM-площадок FunPay (5-10 минут)';
      } else {
        my.className = 'btn btn-sm btn-secondary';
        gl.className = 'btn btn-sm btn-secondary';
        deep.className = 'btn btn-sm btn-primary';
        if(hint) hint.textContent = '🔬 Длинный скан всех 1751 Twiboost-услуг (20-40 минут). Не закрывай окно.';
      }
    }
    // сбрасываем таблицу
    var res = $('niches-results'); if(res) res.innerHTML = '';
    meta('');
    var apply = $('apply-niches'); if(apply){ apply.disabled = true; apply.textContent = '✅ Применить выбранные'; }
  }

  // ==== Progress bar API ====
  function showProgress(show){
    var el = $('niches-progress-wrap');
    if(el) el.style.display = show ? 'block' : 'none';
  }
  function updateProgress(pct, label, detail){
    var bar = $('niches-progress-bar');
    var pctEl = $('niches-progress-percent');
    var labelEl = $('niches-progress-label');
    var detailEl = $('niches-progress-detail');
    if(bar) bar.style.width = Math.max(0, Math.min(100, pct)) + '%';
    if(pctEl) pctEl.textContent = Math.round(pct) + '%';
    if(labelEl && label) labelEl.textContent = label;
    if(detailEl && detail !== undefined) detailEl.textContent = detail;
  }

  // ==== Renderer таблицы (общий для my/global/deep) ====
  function renderTable(niches, mode){
    var res = $('niches-results');
    if(!res) return;
    if(!niches || !niches.length){
      res.innerHTML = '<div style="padding:20px;opacity:.6;text-align:center;">Ниш не найдено. Попробуй увеличить бюджет.</div>';
      return;
    }
    window._fh_lastNiches = niches;

    var isGlobal = mode === 'global';
    var isDeep = mode === 'deep';
    var html = '<table class="table" style="width:100%;font-size:.9em">';
    html += '<thead><tr>';
    html += '<th style="width:36px;"><input type="checkbox" id="niche-chk-all"></th>';
    if(isGlobal) html += '<th>Платформа</th>';
    if(isDeep) html += '<th>Найдено на FunPay</th><th>Прибыльность</th>';
    html += '<th>Ниша</th><th>Услуга Twiboost</th>';
    html += '<th>Себест.</th><th>Средняя</th><th>Цена</th>';
    html += '<th>Прибыль</th><th>Маржа</th>';
    html += '<th>Продавцов</th><th>Лотов</th>';
    html += '</tr></thead><tbody>';

    niches.forEach(function(n, i){
      var margin = Number(n.margin_pct || 0);
      var mColor = margin >= 100 ? '#4ade80' : (margin >= 30 ? '#fbbf24' : '#f87171');
      html += '<tr>';
      html += '<td><input type="checkbox" class="niche-chk" data-idx="'+i+'"></td>';
      if(isGlobal){
        html += '<td><b>'+ (n.category_name || '—') +'</b></td>';
      }
      if(isDeep){
        html += '<td>'+(n.funpay_found || '—')+'</td>';
        html += '<td style="color:'+(n.is_profitable ? '#4ade80' : '#f87171')+'">'+(n.is_profitable ? 'Да' : 'Нет')+'</td>';
      }
      html += '<td>'+ (n.subcategory_name || n.twiboost_title || '—') +'</td>';
      html += '<td style="font-size:.85em;opacity:.85">' + (n.service_name ? ('AS#'+ n.service_id +' — '+ n.service_name.substring(0,40)) : (n.twiboost_title || '').substring(0,60)) +'</td>';
      html += '<td>' + (n.cost != null ? Number(n.cost).toFixed(2)+' ₽' : '—') + '</td>';
      html += '<td>' + (n.avg_price != null ? Number(n.avg_price).toFixed(0)+' ₽' : '—') + '</td>';
      html += '<td><b>'+ Number(n.price || 0).toFixed(2) +' ₽</b></td>';
      html += '<td style="color:#4ade80">'+ Number(n.profit || 0).toFixed(2) +' ₽</td>';
      html += '<td style="color:'+ mColor +';white-space:nowrap">'+ margin.toFixed(1) +' %</td>';
      html += '<td>' + (n.total_sellers || '?') + '</td>';
      html += '<td>' + (n.total_lots || '?') + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    res.innerHTML = html;

    // чекбоксы — event delegation
    var chkAll = $('niche-chk-all');
    if(chkAll){
      chkAll.checked = false;
      chkAll.addEventListener('change', function(){
        document.querySelectorAll('.niche-chk').forEach(function(c){ c.checked = chkAll.checked; });
        updateApplyBtn();
      });
    }
    var res = $('niches-results');
    if(res && !res._chkBound){
      res._chkBound = true;
      res.addEventListener('change', function(e){
        if(e.target && e.target.classList && e.target.classList.contains('niche-chk')){
          updateApplyBtn();
        }
      });
      res.addEventListener('click', function(e){
        var row = e.target.closest ? e.target.closest('tr') : null;
        if(row && e.target.tagName !== 'INPUT'){
          var chk = row.querySelector('.niche-chk');
          if(chk){
            chk.checked = !chk.checked;
            updateApplyBtn();
          }
        }
      });
    }
    updateApplyBtn();
  }

  function updateApplyBtn(){
    var sel = document.querySelectorAll('.niche-chk:checked').length;
    var btn = $('apply-niches');
    if(!btn) return;
    btn.disabled = sel === 0;
    btn.textContent = sel ? '✅ Применить выбранные ('+sel+')' : '✅ Применить выбранные';
  }

  // ==== Scan: My niches (heatmap-based) ====
  async function scanMy(){
    var budget = parseFloat(($('niches-budget')||{}).value || '500');
    if(!(budget > 0)){ alert('Введи бюджет > 0'); return; }
    log('scan MY budget='+budget);
    meta('<em>Ищу ниши по heatmap…</em>');
    $('scan-niches').disabled = true;
    try{
      var r = await fetch('/api/market/analyze_niches', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({budget: budget})
      });
      var j = await r.json();
      if(!j.available){
        meta('<span style="color:#f87171">'+ (j.error || 'нет данных') +'</span>');
        toast(j.error || 'Ошибка', 'error');
        renderTable([], 'my');
        return;
      }
      meta('Найдено: <b>'+ j.total +'</b> | Бюджет: <b>'+ budget +' ₽</b> | '+ new Date().toLocaleString('ru-RU'));
      renderTable(j.niches || [], 'my');
      log('scan MY done — '+ j.total +' ниш');
      toast('Найдено ниш: '+ j.total, 'success');
    } catch(e){
      log('scan MY err: '+e);
      meta('<span style="color:#f87171">Ошибка: '+e+'</span>');
      toast('Ошибка сканирования', 'error');
    } finally {
      $('scan-niches').disabled = false;
    }
  }

  // ==== Scan: Global (все SMM-платформы, с polling) ====
  var _globalPoller = null;
  var _deepPoller = null;
  async function scanGlobal(){
    var budget = parseFloat(($('niches-budget')||{}).value || '500');
    if(!(budget > 0)){ alert('Введи бюджет > 0'); return; }
    log('scan GLOBAL budget='+budget);
    meta('<em>Запуск глобального скана…</em>');
    $('scan-niches').disabled = true;
    showProgress(true);
    updateProgress(0, 'Инициализация…', '');

    try{
      var startR = await fetch('/api/market/analyze_niches_global', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({budget: budget})
      });
      var startJ = await startR.json();
      if(!startJ.ok || !startJ.task_id){
        toast('Ошибка старта: '+(startJ.error||'unknown'), 'error');
        meta('<span style="color:#f87171">Ошибка старта</span>');
        showProgress(false);
        $('scan-niches').disabled = false;
        return;
      }
      var taskId = startJ.task_id;
      log('global task_id='+taskId);

      // polling
      if(_globalPoller) clearInterval(_globalPoller);
      var elapsed = 0;
      _globalPoller = setInterval(async function(){
        elapsed += 3;
        try {
          var pR = await fetch('/api/market/analyze_niches_global/progress?task_id='+taskId);
          var p = await pR.json();
          if(!p.available){
            log('progress unavailable: '+(p.error||'?'));
            return;
          }
          var pct = p.percent || 0;
          var lastName = (p.last_done && p.last_done.name) ? p.last_done.name : '—';
          updateProgress(pct,
            'Сканирую платформы… ('+ p.current +'/'+ p.total +')',
            'Прошло: '+ Math.round(p.elapsed_sec || elapsed) +'с | Последняя: '+ lastName
          );

          if(p.status === 'done'){
            clearInterval(_globalPoller); _globalPoller = null;
            updateProgress(100, '✅ Готово!', 'Прошло: '+ Math.round(p.elapsed_sec) +'с');
            var res = p.result || {};
            meta('Найдено: <b>'+ (res.total||0) +'</b> | Просканировано: <b>'+ (res.scanned||0) +'</b> | Бюджет: <b>'+ budget +' ₽</b>');
            renderTable(res.niches || [], 'global');
            log('global done — '+ (res.total||0) +' ниш');
            toast('Найдено ниш: '+ (res.total||0), 'success');
            $('scan-niches').disabled = false;
            setTimeout(function(){ showProgress(false); }, 3000);
          }
          else if(p.status === 'error'){
            clearInterval(_globalPoller); _globalPoller = null;
            log('global error: '+p.error);
            meta('<span style="color:#f87171">Ошибка: '+p.error+'</span>');
            toast('Ошибка скана: '+p.error, 'error');
            $('scan-niches').disabled = false;
            showProgress(false);
          }
        } catch(e){
          log('poll err: '+e);
        }
      }, 3000);
    } catch(e){
      log('scan GLOBAL err: '+e);
      meta('<span style="color:#f87171">Ошибка: '+e+'</span>');
      toast('Ошибка запуска', 'error');
      showProgress(false);
      $('scan-niches').disabled = false;
    }
  }

  // ==== Scan: Deep (все Twiboost-услуги, с polling) ====
  async function scanDeep(){
    var budget = parseFloat(($('niches-budget')||{}).value || '500');
    if(!(budget > 0)){ alert('Введи бюджет > 0'); return; }
    if(!confirm('Глубокий анализ может занять 20-40 минут. Вы уверены, что хотите продолжить?')){ return; }
    log('scan DEEP budget='+budget);
    meta('<em>Запуск глубокого анализа…</em>');
    $('scan-niches').disabled = true;
    showProgress(true);
    updateProgress(0, 'Инициализация глубокого скана…', '');

    try{
      var startR = await fetch('/api/market/analyze_niches_deep', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({budget: budget})
      });
      var startJ = await startR.json();
      if(!startJ.ok || !startJ.task_id){
        toast('Ошибка старта: '+(startJ.error||'unknown'), 'error');
        meta('<span style="color:#f87171">Ошибка старта</span>');
        showProgress(false);
        $('scan-niches').disabled = false;
        return;
      }
      var taskId = startJ.task_id;
      log('deep task_id='+taskId);

      if(_deepPoller) clearInterval(_deepPoller);
      var elapsed = 0;
      _deepPoller = setInterval(async function(){
        elapsed += 2;
        try {
          var pR = await fetch('/api/market/analyze_niches_deep/progress?task_id='+taskId);
          var p = await pR.json();
          var total = p.total || 0;
          var current = p.progress || 0;
          var pct = total > 0 ? Math.min(100, Math.round(current * 100 / total)) : 0;
          updateProgress(pct,
            '🔬 Глубокий анализ… ('+ current +'/'+ total +')',
            'Прошло: '+ Math.round(p.elapsed_sec || elapsed) +'с | Статус: '+ (p.status || '—')
          );

          if(p.status === 'completed'){
            clearInterval(_deepPoller); _deepPoller = null;
            updateProgress(100, '✅ Глубокий анализ готов!', 'Прошло: '+ Math.round(p.elapsed_sec || elapsed) +'с');
            var results = p.results || [];
            meta('Найдено: <b>'+ results.length +'</b> | Бюджет: <b>'+ budget +' ₽</b>');
            renderTable(results, 'deep');
            log('deep done — '+ results.length +' ниш');
            toast('Глубокий анализ: '+ results.length +' ниш', 'success');
            $('scan-niches').disabled = false;
            setTimeout(function(){ showProgress(false); }, 3000);
          }
          else if(p.status === 'failed'){
            clearInterval(_deepPoller); _deepPoller = null;
            log('deep error: '+(p.error||'?'));
            meta('<span style="color:#f87171">Ошибка: '+(p.error||='неизвестная')+'</span>');
            toast('Ошибка глубокого анализа', 'error');
            $('scan-niches').disabled = false;
            showProgress(false);
          }
        } catch(e){
          log('deep poll err: '+e);
        }
      }, 2000);
    } catch(e){
      log('scan DEEP err: '+e);
      meta('<span style="color:#f87171">Ошибка: '+e+'</span>');
      toast('Ошибка запуска', 'error');
      showProgress(false);
      $('scan-niches').disabled = false;
    }
  }

  function scanNiches(){
    if(MODE === 'global') scanGlobal();
    else if(MODE === 'deep') scanDeep();
    else scanMy();
  }

  // ==== Apply (генерация лотов из выбранных ниш) ====
  async function applyNiches(){
    var lastNiches = window._fh_lastNiches || [];
    var idxs = Array.from(document.querySelectorAll('.niche-chk:checked')).map(function(ch){ return parseInt(ch.getAttribute('data-idx'),10); });
    var chosen = idxs.map(function(i){ return lastNiches[i]; }).filter(Boolean);
    if(!chosen.length){ alert('Выбери ниши'); return; }
    var btn = $('apply-niches');
    log('apply '+chosen.length+' ниш…');
    if(btn){ btn.disabled=true; btn.textContent='⏳ Генерация…'; }
    try{
      var payload = { niches: chosen.map(function(n){
        return {
          service_id: n.service_id,
          quantity: n.quantity || 1000,
          price: n.price,
          variations: n.variations || n.recommended_lots || 15
        };
      })};
      var r = await fetch('/api/autosmm/generate_from_niches', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      var j = await r.json();
      log('generate: '+ JSON.stringify(j).substring(0,300));
      if(j.ok){
        toast('Сгенерировано лотов: '+(j.total_generated||0), 'success');
        alert('Готово!\nСгенерировано: '+(j.total_generated||0)+' лотов\nНиш: '+chosen.length);
      } else {
        alert('Ошибка генерации: '+(j.error||'unknown'));
        toast('Ошибка генерации', 'error');
      }
    }catch(e){
      alert('JS: '+e); log('apply err '+e);
    } finally {
      updateApplyBtn();
    }
  }

  function bindNiches(){
    if(!$('niches-budget')){
      // страница не готова, попробуем позже
      setTimeout(bindNiches, 400);
      return;
    }
    injectControls();
    setMode('my');

    var my = $('niches-mode-my');    if(my) my.onclick = function(){ setMode('my'); };
    var gl = $('niches-mode-global'); if(gl) gl.onclick = function(){ setMode('global'); };
    var s = $('scan-niches');  if(s) s.onclick = scanNiches;
    var a = $('apply-niches'); if(a) a.onclick = applyNiches;

    log('niches v3.4 ready (my/global toggle, progress)');
  }

  function boot(){ bindNiches(); }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
