# Windows development PC only; never run on factory controller.
param([string]$Python = "python", [string]$Evidence = "", [string]$Blender = "auto")
$ErrorActionPreference = "Stop"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)
function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Exe $Arguments" }
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Checked $Python @("-m","venv",".venv")
}
$py = (Resolve-Path ".venv\Scripts\python.exe").Path
Invoke-Checked $py @("-m","pip","install","-r","requirements.txt")
Invoke-Checked $py @("-m","pip","check")
Invoke-Checked $py @("-m","unittest","discover","-s","tests","-p","test_*.py")
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "outputs/development_$stamp"
Invoke-Checked $py @("scripts/first_test.py","--output","$out/calibration")
$argsReview = @("scripts/prepare_tp40.py","--output","$out/tp40_review","--blender",$Blender)
if ($Evidence) { $argsReview += @("--evidence",$Evidence) }
Invoke-Checked $py $argsReview
& $py -m pip freeze | Out-File "$out/dependencies.txt" -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw "pip freeze failed" }
Write-Host ("Review: " + (Resolve-Path "$out/tp40_review").Path)
Write-Host "Inspect PNGs/GLBs; calibration is test only. Do not copy development tools to factory PC."
