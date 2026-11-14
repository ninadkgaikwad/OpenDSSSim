<#+
.SYNOPSIS
  Windows PowerShell entry point for the self-contained IEEE-123 course.
.DESCRIPTION
  Run from the repository root after activating a Python environment with
  the project's required dependencies. Never installs or patches source.
.EXAMPLE
  & .\examples\ieee123_course\scripts\run_windows.ps1 -Lesson 00 -RunId check_001
.EXAMPLE
  & .\examples\ieee123_course\scripts\run_windows.ps1 -PaperCampaign -Steps 24 -RunId pesgm_001
#>
param(
  [ValidateSet('00','01','02','03','04','05','06','07','08','09','10')][string]$Lesson='00',
  [switch]$All,
  [switch]$PaperCampaign,
  [ValidateRange(1,24)][int]$Steps=3,
  [string]$RunId='',
  [ValidateSet('ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')][string]$Variant='ieee123_p2_mf01_simple',
  [ValidateSet('slack-first','service-first')][string]$Policy='slack-first'
)
$ErrorActionPreference='Stop'
$Repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$Script=Join-Path $Repo 'examples\ieee123_course\run_course.py'
if (-not (Test-Path $Script)) {throw 'Missing course script'}
$Python= if ($env:CONDA_PREFIX) {Join-Path $env:CONDA_PREFIX 'python.exe'} else {(Get-Command python -CommandType Application | Select-Object -First 1).Source}
if (-not (Test-Path $Python)) {throw 'Python executable not found'}
$Args=@('-B',$Script,'--steps',[string]$Steps,'--variant',$Variant,'--policy',$Policy)
if ($PaperCampaign) {$Args+= '--paper-campaign'}
elseif ($All) {$Args+= '--all'}
else {$Args+=@('--lesson',$Lesson)}
if ($RunId) {$Args+=@('--run-id',$RunId)}
Write-Host ('OPEN DSS SIM COURSE: '+$Python) -ForegroundColor Cyan
& $Python @Args
if ($LASTEXITCODE -ne 0) {throw ('Course failed: '+$LASTEXITCODE+' (partial output preserved)')}
Write-Host 'COURSE=PASS' -ForegroundColor Green
