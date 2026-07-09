// FunPay Hub - Chart helpers
(function() {
  'use strict';

  // Wait until Chart loaded
  function whenChartReady(cb) {
    if (window.Chart) { cb(); return; }
    let tries = 0;
    const iv = setInterval(() => {
      tries++;
      if (window.Chart) { clearInterval(iv); cb(); }
      else if (tries > 30) { clearInterval(iv); console.error('Chart.js not loaded'); }
    }, 100);
  }

  // Common dark theme defaults
  function applyTheme() {
    if (!window.Chart) return;
    Chart.defaults.color = '#8BA3C7';
    Chart.defaults.borderColor = 'rgba(100,180,255,0.06)';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.legend.labels.color = '#E8F0FF';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(8, 17, 32, 0.95)';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(100,180,255,0.15)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleColor = '#E8F0FF';
    Chart.defaults.plugins.tooltip.bodyColor = '#8BA3C7';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = false;
  }

  // ============= LINE CHART =============
  window.makeLineChart = function(canvasId, labels, data, options) {
    whenChartReady(() => {
      applyTheme();
      const ctx = document.getElementById(canvasId);
      if (!ctx) return;
      // destroy previous if exists
      if (ctx._chart) ctx._chart.destroy();

      const opts = options || {};
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim() || '#00D4FF';
      const accentRgb = getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb').trim() || '0,212,255';

      // gradient
      const c = ctx.getContext('2d');
      const grad = c.createLinearGradient(0, 0, 0, 300);
      grad.addColorStop(0, `rgba(${accentRgb}, 0.4)`);
      grad.addColorStop(1, `rgba(${accentRgb}, 0)`);

      ctx._chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: opts.label || 'Значение',
            data: data,
            borderColor: accent,
            backgroundColor: grad,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: accent,
            pointBorderColor: 'transparent',
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: '#fff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: '#506882', maxRotation: 0 }
            },
            y: {
              grid: { color: 'rgba(100,180,255,0.04)' },
              ticks: { color: '#506882' },
              beginAtZero: opts.beginAtZero !== false
            }
          }
        }
      });
    });
  };

  // ============= BAR CHART =============
  window.makeBarChart = function(canvasId, labels, data, options) {
    whenChartReady(() => {
      applyTheme();
      const ctx = document.getElementById(canvasId);
      if (!ctx) return;
      if (ctx._chart) ctx._chart.destroy();

      const opts = options || {};
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim() || '#00D4FF';
      const accentRgb = getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb').trim() || '0,212,255';

      ctx._chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: opts.label || 'Значение',
            data: data,
            backgroundColor: `rgba(${accentRgb}, 0.6)`,
            borderColor: accent,
            borderWidth: 1,
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#506882', maxRotation: 0 } },
            y: {
              grid: { color: 'rgba(100,180,255,0.04)' },
              ticks: { color: '#506882' },
              beginAtZero: true
            }
          }
        }
      });
    });
  };

  // ============= HEATMAP (custom - Chart.js has no native heatmap) =============
  window.makeHeatmap = function(containerId, matrix) {
    const c = document.getElementById(containerId);
    if (!c) return;
    if (!matrix || !matrix.length) {
      c.innerHTML = '<div class="empty-state">Нет данных</div>';
      return;
    }

    let max = 0;
    matrix.forEach(row => row.forEach(v => { if (v > max) max = v; }));

    const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb').trim() || '0,212,255';

    let html = '<div class="heatmap-wrap">';
    html += '<div class="heatmap-hours"><span></span>';
    for (let h = 0; h < 24; h++) {
      html += `<span>${h % 3 === 0 ? h : ''}</span>`;
    }
    html += '</div>';

    matrix.forEach((row, i) => {
      html += `<div class="heatmap-row"><span class="heatmap-day">${days[i] || ('D'+i)}</span>`;
      row.forEach((v, h) => {
        const op = max > 0 ? (v / max) : 0;
        html += `<div class="heatmap-cell" style="background:rgba(${accent},${op*0.85});" title="${days[i]} ${h}:00 — ${v}"></div>`;
      });
      html += '</div>';
    });
    html += '</div>';
    c.innerHTML = html;
  };

  // expose
  window.applyChartTheme = applyTheme;
})();