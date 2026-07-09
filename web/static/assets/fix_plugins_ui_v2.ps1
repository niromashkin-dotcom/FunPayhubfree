# FunPay Hub – plugins UI restore + AutoSMM extended button v2 – safe installer
# Запуск: powershell -ExecutionPolicy Bypass -File .\install_plugin_ext_btn.ps1
$ErrorActionPreference = "Stop"
$Project = "C:\Projects\FunPayCardinal-main"
$web = Join-Path $Project "web\static"
$plugUi = Join-Path $web "plugins-ui.js"
$plugHtml = Join-Path $web "plugins.html"
$btnSrc = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "plugins_autosmm_btn_fix_v2.js"
if(-not (Test-Path $btnSrc)){
  # try alternate locations (when script is run from project root and file is next to it)
  $alt1 = Join-Path $Project "plugins_autosmm_btn_fix_v2.js"
  $alt2 = Join-Path $web "plugins_autosmm_btn_fix_v2.js"
  if(Test-Path $alt1){ $btnSrc=$alt1 } elseif(Test-Path $alt2){ $btnSrc=$alt2 }
}
Write-Host "== FunPay Hub – plugin UI restore =="

# 1. restore plugins-ui.js from known good backups
$backups = @(
  "$plugUi.20260629_pre_niches_btn",
  "$plugUi.backup",
  "$plugUi.bak",
  "$Project\web\static\plugins-ui.clean.js"
)
$restored=$false
foreach($b in $backups){ if(Test-Path $b){ Copy-Item $b $plugUi -Force; Write-Host "[restore] $b -> plugins-ui.js OK"; $restored=$true; break } }
if(-not $restored){ Write-Warning "clean backup not found – continuing with current file, will only clean injected garbage" }

# 2. clean any broken inline autosmm injects from plugins-ui.js
$txt = Get-Content $plugUi -Raw -Encoding UTF8
$origLen = $txt.Length
# remove our old broken footer inject attempts
$txt = $txt -replace '(?s)<a href="/static/autosmm\.html".*?Расширенные настройки.*?</a>', ''
$txt = $txt -replace '(?s)//\s*AutoSMM.*?extended.*?\n\}', ''
# remove accidental markdown that leaked in previous runs: lines containing http://ext.style or "Что на скрине" or "gnsf.cm"
$txt = ($txt -split "`r?`n") | Where-Object { $_ -notmatch 'http://ext\.style|https://ext\.style|Что на скрине|Auto SMM — модалка|gnsf\.cm|becomes|showToast`' | Out-String
# fix common break: if file ends abruptly inside openPluginSettings, restore from backup again
if($txt -notmatch 'function savePluginConfig' -or $txt -notmatch 'openPluginSettings'){
  throw "plugins-ui.js looks corrupted after cleaning – restore manually from plugins-ui.js.20260629_pre_niches_btn"
}
[System.IO.File]::WriteAllText($plugUi, $txt, [System.Text.Encoding]::UTF8)
Write-Host "[clean] plugins-ui.js cleaned, $($origLen) -> $($txt.Length) bytes"

# 3. ensure external btn_fix v2 is in web/static
$dstBtn = Join-Path $web "plugins_autosmm_btn_fix_v2.js"
if(Test-Path $btnSrc){
  Copy-Item $btnSrc $dstBtn -Force
  Write-Host "[copy] plugins_autosmm_btn_fix_v2.js -> $dstBtn OK $((Get-Item $dstBtn).Length) bytes"
} else {
  Write-Warning "btn source not found at $btnSrc – please place plugins_autosmm_btn_fix_v2.js next to this .ps1 or in web/static manually"
}

# 4. wire plugins.html to load v2, remove old v1
$ph = Get-Content $plugHtml -Raw -Encoding UTF8
$ph = $ph -replace '\s*<script src="/static/plugins_autosmm_btn_fix[^"]*\.js"></script>', ''
if($ph -notmatch 'plugins_autosmm_btn_fix_v2\.js'){
  $ph = $ph -replace '</body>', '  <script src="/static/plugins_autosmm_btn_fix_v2.js"></script>`n</body>'
  Write-Host "[wire] plugins.html -> plugins_autosmm_btn_fix_v2.js added"
} else { Write-Host "[wire] already wired" }
[System.IO.File]::WriteAllText($plugHtml, $ph, [System.Text.Encoding]::UTF8)

# 5. cleanup old broken autosmm niche injects
$as = Join-Path $web "autosmm.html"
if(Test-Path $as){
  $ac = Get-Content $as -Raw -Encoding UTF8
  $ac0 = $ac.Length
  # remove any inline niches v3 override blocks
  $ac = $ac -replace '(?s)<!-- AutoSMM niches.*?-->.*?</script>', ''
  # ensure only ONE autosmm_niches_v32.js include
  $ac = $ac -replace '(\s*<script src="/static/autosmm_niches[^"]+\.js"></script>)+', ''
  if($ac -notmatch 'autosmm_niches_v32\.js'){
    $ac = $ac -replace '</body>', '  <script src="/static/autosmm_niches_v32.js"></script>`n</body>'
  }
  [System.IO.File]::WriteAllText($as, $ac, [System.Text.Encoding]::UTF8)
  Write-Host "[clean] autosmm.html cleaned $($ac0) -> $($ac.Length)"
}

Write-Host ""
Write-Host "=== DONE ==="
Write-Host "Next:"
Write-Host " 1) Ensure these 2 files exist in web/static/:"
Write-Host "     - autosmm_niches_v32.js  (~5900 bytes)"
Write-Host "     - plugins_autosmm_btn_fix_v2.js  (~2300 bytes)"
Write-Host " 2) python funpayhub_main.py"
Write-Host " 3) Open: http://127.0.0.1:5000/static/plugins.html"
Write-Host "    → should see: AutoBump / Auto SMM / Logger Plugin / Test Plugin — running — buttons: Настроить / Off / Restart"
Write-Host " 4) Click Auto SMM → Настроить → modal footer left should show: 📊 Расширенные настройки  (NO underline) — click → navigates IN-APP to /static/autosmm.html#tab-niches"
Write-Host " 5) In AutoSMM → Анализ ниш → Найти ниши → should get 4 niches, then Apply"
Write-Host ""
Write-Host "If plugins table still shows 'autobump_plugin' lower-case / stopped / On button — run: "
Write-Host "  Copy-Item 'C:\Projects\FunPayCardinal-main\web\static\plugins-ui.js.20260629_pre_niches_btn' 'C:\Projects\FunPayCardinal-main\web\static\plugins-ui.js' -Force"
