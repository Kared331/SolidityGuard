<#
.SYNOPSIS
    SolidGuard 管理门户 — 一键启动 + 交互式配置管理
.DESCRIPTION
    无参数运行进入交互菜单；带参数直接执行对应操作。
.EXAMPLE
    .\manage.ps1              # 交互菜单
    .\manage.ps1 -Up          # 启动
    .\manage.ps1 -Config      # 直接进配置菜单
    .\manage.ps1 -Health      # 健康检查
#>

[CmdletBinding()]
param(
    [switch]$Up,
    [switch]$Down,
    [switch]$Restart,
    [switch]$Logs,
    [switch]$Status,
    [switch]$Health,
    [switch]$Config
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
$JsonFile = Join-Path $ProjectRoot "solidguard.json"
$JsonExample = Join-Path $ProjectRoot "solidguard.json.example"

# ── 颜色输出辅助 ─────────────────────────────────────────────────
function Write-Info([string]$msg)    { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)      { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn([string]$msg)    { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)     { Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Title([string]$msg)   { Write-Host "`n═══ $msg ═══" -ForegroundColor Magenta }

# ── 前置检查 ─────────────────────────────────────────────────────
function Test-Docker {
    try {
        $null = docker info 2>&1
        if ($LASTEXITCODE -ne 0) { throw "docker info failed" }
        return $true
    } catch {
        Write-Err "Docker 未运行，请先启动 Docker Desktop"
        return $false
    }
}

function Ensure-Config {
    if (-not (Test-Path $EnvFile)) {
        if (Test-Path $EnvExample) {
            Copy-Item $EnvExample $EnvFile
            Write-Warn "已从 .env.example 创建 .env，请修改其中的 changeme 密码"
        } else {
            Write-Err ".env.example 不存在，无法创建 .env"
            exit 1
        }
    }
    if (-not (Test-Path $JsonFile)) {
        if (Test-Path $JsonExample) {
            Copy-Item $JsonExample $JsonFile
            Write-Ok "已从 solidguard.json.example 创建 solidguard.json"
        }
    }
}

# ── 读取/写入 .env ──────────────────────────────────────────────
function Get-EnvValue([string]$key) {
    if (-not (Test-Path $EnvFile)) { return $null }
    $lines = Get-Content $EnvFile
    foreach ($line in $lines) {
        if ($line -match "^\s*$key\s*=\s*(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Set-EnvValue([string]$key, [string]$value) {
    $lines = Get-Content $EnvFile
    $found = $false
    $newLines = @()
    foreach ($line in $lines) {
        if ($line -match "^\s*$key\s*=") {
            $newLines += "$key=$value"
            $found = $true
        } else {
            $newLines += $line
        }
    }
    if (-not $found) {
        $newLines += "$key=$value"
    }
    Set-Content -Path $EnvFile -Value $newLines -Encoding UTF8
}

# ── 读取/写入 solidguard.json ───────────────────────────────────
function Get-JsonConfig {
    if (-not (Test-Path $JsonFile)) {
        Write-Err "solidguard.json 不存在"
        return $null
    }
    return Get-Content $JsonFile -Raw | ConvertFrom-Json
}

function Save-JsonConfig($config) {
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $JsonFile -Encoding UTF8
}

function Set-JsonValue([string]$path, $value) {
    $config = Get-JsonConfig
    $parts = $path -split "\."
    $obj = $config
    for ($i = 0; $i -lt $parts.Length - 1; $i++) {
        $obj = $obj.($parts[$i])
    }
    $obj.($parts[$parts.Length - 1]) = $value
    Save-JsonConfig $config
}

# ── 服务管理 ────────────────────────────────────────────────────
function Invoke-Up {
    Write-Title "启动 SolidGuard"
    if (-not (Test-Docker)) { return }
    Ensure-Config
    Write-Info "构建并启动容器..."
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Err "启动失败"
        return
    }
    Write-Info "等待 postgres 就绪..."
    for ($i = 0; $i -lt 30; $i++) {
        $health = docker inspect --format='{{.State.Health.Status}}' solidguard-postgres-1 2>$null
        if ($health -eq "healthy") { break }
        Start-Sleep -Seconds 2
    }
    Write-Ok "服务已启动"
    Show-AccessInfo
}

function Invoke-Down {
    Write-Title "停止 SolidGuard"
    docker compose down
    Write-Ok "服务已停止"
}

function Invoke-Restart {
    Write-Title "重启 SolidGuard"
    docker compose restart
    Write-Ok "服务已重启"
}

function Invoke-Logs {
    Write-Title "日志（Ctrl+C 退出）"
    docker compose logs -f
}

function Invoke-Status {
    Write-Title "服务状态"
    docker compose ps
}

function Invoke-Health {
    Write-Title "健康检查"
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5
        Write-Ok "API 健康: $($resp.status)"
    } catch {
        Write-Err "API 不可达: $_"
    }
    $pgHealth = docker inspect --format='{{.State.Health.Status}}' solidguard-postgres-1 2>$null
    if ($pgHealth) { Write-Info "PostgreSQL: $pgHealth" }
    $redisPing = docker exec solidguard-redis-1 redis-cli ping 2>$null
    if ($redisPing) { Write-Info "Redis: $redisPing" }
}

function Show-AccessInfo {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  SolidGuard 已启动" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  前端:  http://localhost:3000" -ForegroundColor White
    Write-Host "  API:   http://localhost:8000" -ForegroundColor White
    Write-Host "  文档:  http://localhost:8000/docs" -ForegroundColor White
    $apiKey = Get-EnvValue "API_KEY"
    Write-Host "  API Key: $apiKey" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
}

# ── 配置管理 ────────────────────────────────────────────────────
function Show-ConfigMenu {
    :configLoop while ($true) {
        Write-Title "配置管理"
        Write-Host "  1. 修改数据库密码"
        Write-Host "  2. 修改 Redis 密码"
        Write-Host "  3. 修改 API Key"
        Write-Host "  4. 修改 LLM API Key"
        Write-Host "  5. 切换 LLM Provider/Model"
        Write-Host "  6. 修改 Token Budget"
        Write-Host "  7. 查看完整配置"
        Write-Host "  0. 返回主菜单"
        $choice = Read-Host "`n选择"

        switch ($choice) {
            "1" { Edit-DbPassword }
            "2" { Edit-RedisPassword }
            "3" { Edit-ApiKey }
            "4" { Edit-LlmApiKey }
            "5" { Edit-LlmProvider }
            "6" { Edit-TokenBudget }
            "7" { Show-FullConfig }
            "0" { break configLoop }
        }
    }
}

function Edit-DbPassword {
    Write-Title "修改数据库密码"
    $current = Get-EnvValue "POSTGRES_PASSWORD"
    Write-Info "当前密码: $current"
    $new = Read-Host "新密码（直接回车取消）"
    if (-not $new) { return }

    # 同步修改 DATABASE_URL（如果存在）
    Set-EnvValue "POSTGRES_PASSWORD" $new

    Write-Warn "数据库密码已修改，需重建 postgres 卷才能生效"
    $confirm = Read-Host "是否立即重建？（会丢失数据，输入 yes 确认）"
    if ($confirm -eq "yes") {
        docker compose down -v
        docker compose up -d --build
        Write-Ok "已重建，新密码生效"
    } else {
        Write-Warn "稍后执行: docker compose down -v && docker compose up -d --build"
    }
}

function Edit-RedisPassword {
    Write-Title "修改 Redis 密码"
    $current = Get-EnvValue "REDIS_PASSWORD"
    Write-Info "当前密码: $current"
    $new = Read-Host "新密码（直接回车取消）"
    if (-not $new) { return }

    Set-EnvValue "REDIS_PASSWORD" $new
    Write-Warn "需重启服务生效"
    $confirm = Read-Host "是否立即重启？（输入 yes 确认）"
    if ($confirm -eq "yes") {
        docker compose restart redis api worker
        Write-Ok "已重启"
    } else {
        Write-Warn "稍后执行: docker compose restart redis api worker"
    }
}

function Edit-ApiKey {
    Write-Title "修改 API Key"
    $current = Get-EnvValue "API_KEY"
    Write-Info "当前 API Key: $current"
    $new = Read-Host "新 API Key（直接回车取消）"
    if (-not $new) { return }

    Set-EnvValue "API_KEY" $new
    Write-Warn "需重启 frontend 和 api 生效"
    $confirm = Read-Host "是否立即重启？（输入 yes 确认）"
    if ($confirm -eq "yes") {
        docker compose restart frontend api
        Write-Ok "已重启"
    } else {
        Write-Warn "稍后执行: docker compose restart frontend api"
    }
}

function Edit-LlmApiKey {
    Write-Title "修改 LLM API Key"
    $current = Get-EnvValue "LLM_API_KEY"
    Write-Info "当前 LLM API Key: $($current.Substring(0, [Math]::Min(8, $current.Length)))..."
    $new = Read-Host "新 LLM API Key（直接回车取消）"
    if (-not $new) { return }

    Set-EnvValue "LLM_API_KEY" $new
    Write-Ok "已修改。下次 LLM 任务自动生效（热加载），无需重启"
}

function Edit-LlmProvider {
    Write-Title "切换 LLM Provider/Model"
    $config = Get-JsonConfig
    if (-not $config) { return }

    $providers = $config.providers.PSObject.Properties.Name | Where-Object { $_ -ne "embedding" }
    Write-Info "可用 Provider: $($providers -join ', ')"
    $current = $config.providers.default.defaultModel
    Write-Info "当前默认 Model: $current"

    $providerChoice = Read-Host "选择 Provider（default/xiaomi，直接回车保持 default）"
    if (-not $providerChoice) { $providerChoice = "default" }
    if ($providerChoice -notin $providers) {
        Write-Err "Provider 不存在: $providerChoice"
        return
    }

    $models = $config.providers.$providerChoice.models
    Write-Info "可用 Model:"
    for ($i = 0; $i -lt $models.Count; $i++) {
        Write-Host "  $($i+1). $($models[$i].id) ($($models[$i].name))"
    }

    $modelChoice = Read-Host "选择 Model 编号（直接回车取消）"
    if (-not $modelChoice) { return }
    $idx = [int]$modelChoice - 1
    if ($idx -lt 0 -or $idx -ge $models.Count) {
        Write-Err "编号无效"
        return
    }

    $selectedModel = $models[$idx].id
    Set-JsonValue "providers.$providerChoice.defaultModel" $selectedModel
    Write-Ok "已切换到 $providerChoice / $selectedModel"
    Write-Info "热加载生效，下一个 LLM 任务使用新配置"
}

function Edit-TokenBudget {
    Write-Title "修改 Token Budget"
    $config = Get-JsonConfig
    $current = $config.app.tokenBudget
    Write-Info "当前 Token Budget: $current"

    $new = Read-Host "新值（直接回车取消）"
    if (-not $new) { return }
    if ($new -notmatch "^\d+$") {
        Write-Err "必须是数字"
        return
    }

    Set-JsonValue "app.tokenBudget" [int]$new
    Write-Ok "已修改为 $new，热加载生效"
}

function Show-FullConfig {
    Write-Title "当前配置"
    Write-Host "`n--- .env ---" -ForegroundColor Cyan
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | Where-Object { $_ -match "^\s*#|^\s*$" -eq $false } | ForEach-Object {
            # 敏感值脱敏显示
            if ($_ -match "(PASSWORD|API_KEY|TOKEN)=") {
                $key = ($_ -split "=")[0]
                Write-Host "  $key=********"
            } else {
                Write-Host "  $_"
            }
        }
    }
    Write-Host "`n--- solidguard.json ---" -ForegroundColor Cyan
    if (Test-Path $JsonFile) {
        $config = Get-JsonConfig
        Write-Host "  App:" -ForegroundColor Gray
        Write-Host "    port: $($config.app.port)"
        Write-Host "    logLevel: $($config.app.logLevel)"
        Write-Host "    tokenBudget: $($config.app.tokenBudget)"
        Write-Host "    maxLLMCallsPerProject: $($config.app.maxLLMCallsPerProject)"
        Write-Host "  Database:" -ForegroundColor Gray
        Write-Host "    poolSize: $($config.database.poolSize)"
        Write-Host "  RAG:" -ForegroundColor Gray
        Write-Host "    topK: $($config.rag.topK)"
        Write-Host "  Providers:" -ForegroundColor Gray
        $config.providers.PSObject.Properties | ForEach-Object {
            $name = $_.Name
            $p = $_.Value
            if ($name -eq "embedding") {
                Write-Host "    ${name}: api=$($p.api)"
            } else {
                Write-Host "    ${name}: api=$($p.api) model=$($p.defaultModel) baseUrl=$($p.baseUrl)"
            }
        }
    }
    Write-Host ""
}

# ── 主菜单 ──────────────────────────────────────────────────────
function Show-MainMenu {
    :mainLoop while ($true) {
        Write-Host ""
        Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Magenta
        Write-Host "║        SolidGuard 管理门户          ║" -ForegroundColor Magenta
        Write-Host "╠══════════════════════════════════════╣" -ForegroundColor Magenta
        Write-Host "║  1. 启动服务                        ║" -ForegroundColor White
        Write-Host "║  2. 停止服务                        ║" -ForegroundColor White
        Write-Host "║  3. 重启服务                        ║" -ForegroundColor White
        Write-Host "║  4. 查看日志                        ║" -ForegroundColor White
        Write-Host "║  5. 服务状态                        ║" -ForegroundColor White
        Write-Host "║  ───────────────────────────────    ║" -ForegroundColor Gray
        Write-Host "║  6. 配置管理                        ║" -ForegroundColor White
        Write-Host "║  7. 健康检查                        ║" -ForegroundColor White
        Write-Host "║  0. 退出                            ║" -ForegroundColor White
        Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Magenta

        $choice = Read-Host "选择"

        switch ($choice) {
            "1" { Invoke-Up }
            "2" { Invoke-Down }
            "3" { Invoke-Restart }
            "4" { Invoke-Logs }
            "5" { Invoke-Status }
            "6" { Show-ConfigMenu }
            "7" { Invoke-Health }
            "0" { break mainLoop }
            default { Write-Warn "无效选择" }
        }
    }
}

# ── 入口：参数模式 vs 交互模式 ──────────────────────────────────
if ($Up)      { Invoke-Up; exit }
if ($Down)    { Invoke-Down; exit }
if ($Restart) { Invoke-Restart; exit }
if ($Logs)    { Invoke-Logs; exit }
if ($Status)  { Invoke-Status; exit }
if ($Health)  { Invoke-Health; exit }
if ($Config)  { Show-ConfigMenu; exit }

# 无参数 → 交互菜单
Show-MainMenu
