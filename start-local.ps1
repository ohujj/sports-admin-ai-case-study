param(
    [ValidateRange(1024,65535)][int]$Port = 8766,
    [string]$OllamaPath,
    [string]$ModelDirectory,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Python environment missing. Run: py -3.14 -m venv .venv, then .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt (see README.md).'
}
& $python -B -c 'import fastapi, uvicorn, pydantic'
if ($LASTEXITCODE -ne 0) { throw 'Dependencies missing. Install requirements-lock.txt in .venv.' }
$models = $null
try { $models = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 } catch { }
if ($null -eq $models) {
    if ($CheckOnly) { throw 'Ollama is not running on 127.0.0.1:11434. Start local Ollama first; CheckOnly does not launch it.' }
    $exe = $null
    $legacyRuntime = Join-Path $env:LOCALAPPDATA 'SportsAdminAiPoc\Ollama'
    if ($OllamaPath) {
        if (-not (Test-Path -LiteralPath $OllamaPath -PathType Leaf)) { throw 'Specified OllamaPath does not exist.' }
        $exe = (Resolve-Path -LiteralPath $OllamaPath).ProviderPath
    } else {
        $command = Get-Command ollama.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $exe = $command.Source }
        if (-not $exe) {
            $standard = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
            if (Test-Path -LiteralPath $standard -PathType Leaf) { $exe = $standard }
        }
        if (-not $exe) {
            $legacy = Join-Path $legacyRuntime 'bin\ollama.exe'
            if (Test-Path -LiteralPath $legacy -PathType Leaf) {
                $exe = $legacy
                if (-not $ModelDirectory) { $ModelDirectory = Join-Path $legacyRuntime 'models' }
            }
        }
    }
    if (-not $exe) { throw 'Ollama not found. Install official Ollama, reopen PowerShell, or pass -OllamaPath. No software was downloaded.' }
    if ($ModelDirectory -and -not (Test-Path -LiteralPath $ModelDirectory -PathType Container)) {
        throw 'Specified ModelDirectory does not exist. Download the model first as documented in README.md.'
    }
    $names = @('OLLAMA_HOST','OLLAMA_MODELS','OLLAMA_NO_CLOUD','OLLAMA_CONTEXT_LENGTH','OLLAMA_NUM_PARALLEL','OLLAMA_MAX_LOADED_MODELS')
    $previous = @{}
    foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    try {
        $env:OLLAMA_HOST = '127.0.0.1:11434'
        if ($ModelDirectory) { $env:OLLAMA_MODELS = (Resolve-Path -LiteralPath $ModelDirectory).ProviderPath }
        $env:OLLAMA_NO_CLOUD = '1'
        $env:OLLAMA_CONTEXT_LENGTH = '4096'
        $env:OLLAMA_NUM_PARALLEL = '1'
        $env:OLLAMA_MAX_LOADED_MODELS = '1'
        $logs = Join-Path $PSScriptRoot '.local-runtime'
        New-Item -ItemType Directory -Path $logs -Force | Out-Null
        $process = Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'ollama.stdout.log') -RedirectStandardError (Join-Path $logs 'ollama.stderr.log') -PassThru
    } finally {
        foreach ($name in $names) {
            if ($null -eq $previous[$name]) {
                Remove-Item -LiteralPath ('Env:\' + $name) -ErrorAction SilentlyContinue
            } else {
                [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
            }
        }
    }
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try { $models = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 1; break } catch {
            if ($process.HasExited) { break }
            Start-Sleep -Milliseconds 250
        }
    }
    if ($null -eq $models) { throw 'Local Ollama did not become ready. Check the ignored .local-runtime logs; do not publish them.' }
}
if (-not ($models.models | Where-Object { $_.name -eq 'qwen3:4b-instruct' })) {
    throw 'Local model missing. Run: ollama pull qwen3:4b-instruct against this local server. The script will not download or switch models automatically.'
}
if ($CheckOnly) {
    Write-Host 'Ready: Python dependencies and local qwen3:4b-instruct. No app server was launched.'
    return
}
Push-Location $PSScriptRoot
try {
    Write-Host "Synthetic-only app: http://127.0.0.1:$Port/ (no business backend or external LLM)"
    & $python -B -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'Application exited with an error. Check whether the selected port is already in use.' }
} finally { Pop-Location }
