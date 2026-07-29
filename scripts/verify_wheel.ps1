param(
    [string]$ConfigPath = $env:BIA_BRIEF_CONFIG,
    [string]$EnvironmentName = "BIA-Brief-wheel-test",
    [switch]$KeepEnvironment
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dist = Join-Path $repo "dist"

if (-not (Test-Path $ConfigPath)) {
    throw "A model config is required. Pass -ConfigPath or set BIA_BRIEF_CONFIG."
}

python -m build --wheel --outdir $dist
$wheel = Get-ChildItem $dist -Filter "bia_brief-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $wheel) { throw "Wheel was not created in $dist" }

conda env remove -n $EnvironmentName -y 2>$null
conda create -n $EnvironmentName python=3.11 pip -y
conda run -n $EnvironmentName python -m pip install $wheel.FullName

conda run -n $EnvironmentName bia-brief-doctor --project (Join-Path $repo "projects\fudan_mouse_25")
$common = @("--config", $ConfigPath, "--no-delivery-copy")
conda run -n $EnvironmentName bia-brief-project fudan_mouse_25 @common
conda run -n $EnvironmentName bia-brief-project imu_sheep_21_2 @common

if (-not $KeepEnvironment) {
    conda env remove -n $EnvironmentName -y
}
