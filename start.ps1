param(
    [ValidateRange(1024,65535)][int]$Port = 8766,
    [string]$OllamaPath,
    [string]$ModelDirectory,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'start-local.ps1') @PSBoundParameters
