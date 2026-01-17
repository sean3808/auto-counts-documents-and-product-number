<#
.SYNOPSIS
    採購單關聯單據重組與單據明細產生器 - PowerShell 入口腳本

.DESCRIPTION
    此腳本為 Python 核心的包裝器，負責：
    1. 檢查資料夾存在
    2. 檢查 uv 可用
    3. 呼叫 Python CLI
    4. 傳遞退出碼
    5. 執行結束後開啟 log 檔案

.PARAMETER Command
    執行的階段：phase0, phase1, phase2, all

.EXAMPLE
    .\run.ps1 phase0
    執行 Phase 0：PDF 蓋章

.EXAMPLE
    .\run.ps1 phase1
    執行 Phase 1：合併 PDF

.EXAMPLE
    .\run.ps1 phase2
    執行 Phase 2：產生 Excel 明細

.EXAMPLE
    .\run.ps1 all
    依序執行 Phase 0 + Phase 1 + Phase 2
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("phase0", "phase1", "phase2", "all")]
    [string]$Command = "all"
)

$ErrorActionPreference = "Stop"

# 取得腳本所在目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 定義路徑
$InputDir = Join-Path $ScriptDir "input"
$OutputDir = Join-Path $ScriptDir "output"
$TemplateFile = Join-Path $ScriptDir "template.xlsx"
$StampsDir = Join-Path $ScriptDir "印章\removebg"
$TempDir = Join-Path $ScriptDir "temp\stamped"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "採購單關聯單據重組與單據明細產生器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 檢查 uv 是否可用
Write-Host "[檢查] uv 套件管理器..." -ForegroundColor Yellow
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "[錯誤] 找不到 uv。請先安裝 uv：" -ForegroundColor Red
    Write-Host "  irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Gray
    exit 2
}
Write-Host "[OK] uv 已安裝: $($uvPath.Source)" -ForegroundColor Green

# 2. 檢查資料夾
Write-Host "[檢查] 資料夾結構..." -ForegroundColor Yellow

# input 資料夾
if (-not (Test-Path $InputDir)) {
    Write-Host "[建立] input/ 資料夾" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $InputDir -Force | Out-Null
    Write-Host "[提示] 請將 PDF 檔案放入 input/ 資料夾後再執行" -ForegroundColor Yellow
    if ($Command -eq "phase0" -or $Command -eq "phase1" -or $Command -eq "all") {
        exit 1
    }
}

# output 資料夾
if (-not (Test-Path $OutputDir)) {
    Write-Host "[建立] output/ 資料夾" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# temp/stamped 資料夾（Phase 0 需要）
if ($Command -eq "phase0" -or $Command -eq "all") {
    if (-not (Test-Path $TempDir)) {
        Write-Host "[建立] temp/stamped/ 資料夾" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    }
}

# template.xlsx（Phase 2 需要）
if ($Command -eq "phase2" -or $Command -eq "all") {
    if (-not (Test-Path $TemplateFile)) {
        Write-Host "[錯誤] 找不到 template.xlsx" -ForegroundColor Red
        exit 2
    }
}

# 印章資料夾（Phase 0 需要）
if ($Command -eq "phase0" -or $Command -eq "all") {
    if (-not (Test-Path $StampsDir)) {
        Write-Host "[警告] 找不到印章資料夾: $StampsDir" -ForegroundColor Yellow
        Write-Host "[提示] Phase 0 可能無法正常蓋章" -ForegroundColor Yellow
    }
}

Write-Host "[OK] 資料夾檢查完成" -ForegroundColor Green
Write-Host ""

# 3. 執行 Python CLI
Write-Host "[執行] $Command" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray

$exitCode = 0
$logFilePath = $null

try {
    # 執行 Python 並捕獲輸出
    $output = & uv run python -m doc_processor $Command --input $InputDir --output $OutputDir --template $TemplateFile --stamps $StampsDir 2>&1
    $exitCode = $LASTEXITCODE

    # 顯示輸出並尋找 log 檔案路徑
    foreach ($line in $output) {
        $lineStr = $line.ToString()
        if ($lineStr -match "^LOG_FILE_PATH:(.+)$") {
            $logFilePath = $Matches[1]
        } else {
            Write-Host $lineStr
        }
    }
}
catch {
    Write-Host "[錯誤] 執行失敗: $_" -ForegroundColor Red
    $exitCode = 2
}

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray

# 4. 顯示結果
switch ($exitCode) {
    0 {
        Write-Host "[完成] 執行成功" -ForegroundColor Green
    }
    1 {
        Write-Host "[完成] 部分項目跳過，請查看 log 檔案" -ForegroundColor Yellow
    }
    2 {
        Write-Host "[失敗] 執行失敗，請查看 log 檔案" -ForegroundColor Red
    }
    default {
        Write-Host "[未知] 退出碼: $exitCode" -ForegroundColor Red
    }
}

# 5. 開啟 log 檔案
if ($logFilePath -and (Test-Path $logFilePath)) {
    Write-Host ""
    Write-Host "[開啟] Log 檔案: $logFilePath" -ForegroundColor Cyan
    Start-Process $logFilePath
} elseif ($logFilePath) {
    Write-Host "[警告] Log 檔案不存在: $logFilePath" -ForegroundColor Yellow
}

exit $exitCode
