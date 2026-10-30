# Copies the ReSeason files into FM24 and checks the whole setup. Safe to run again.
param([string]$UserData, [string]$Game)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$italy = 'sortitoutsi.net FM24 Data Update - Italy (2026 Start).fmf'

function Ask-Folder($question) {
    $answer = (Read-Host $question).Trim().Trim('"')
    if ($answer -and (Test-Path -LiteralPath $answer)) { return $answer }
    return $null
}

if (-not $UserData) {
    $UserData = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Sports Interactive\Football Manager 2024'
}
if (-not (Test-Path -LiteralPath $UserData)) {
    Write-Host "Can't find $UserData"
    $UserData = Ask-Folder "Start FM24 once so it creates that folder, or paste its path here"
    if (-not $UserData) { exit 1 }
}

if (-not $Game) {
    $steam = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if ($steam) {
        # Every Steam library is listed in libraryfolders.vdf as: "path"  "<folder>"
        $libraries = @($steam)
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            $libraries += Select-String -LiteralPath $vdf -Pattern '"path"\s+"(.+)"' |
                ForEach-Object { $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }
        }
        $Game = $libraries |
            ForEach-Object { Join-Path $_ 'steamapps\common\Football Manager 2024' } |
            Where-Object { Test-Path -LiteralPath (Join-Path $_ 'data') } |
            Select-Object -First 1
    }
    if (-not $Game) {
        $Game = Ask-Folder "Can't find FM24 in Steam. Paste the path of your 'Football Manager 2024' game folder (or press Enter to skip)"
    }
}

$modules = @(Get-ChildItem -LiteralPath (Join-Path $root 'data') -Filter '*.fmf')
if ($modules.Count -eq 0) {
    Write-Host 'The ReSeason modules are missing from the data folder.'
    Write-Host 'Download ReSeason from the Releases page, not with the green Code button.'
    exit 1
}

$editor = Join-Path $UserData 'editor data'
New-Item -ItemType Directory -Force -Path $editor | Out-Null
$modules | Copy-Item -Destination $editor -Force
Write-Host "Copied $($modules.Count) ReSeason modules into editor data."

# The ReSeason Italy module replaces this file; loading both breaks the Italian leagues.
$italyPath = Join-Path $editor $italy
if (Test-Path -LiteralPath $italyPath) {
    Move-Item -LiteralPath $italyPath -Destination "$italyPath.disabled" -Force
    Write-Host 'Disabled the sortitoutsi Italy file (ReSeason replaces it).'
}

$helper = if ($Game) { Join-Path $Game 'data\database\db\2430\edt\permanent' }
if ($helper -and (Test-Path -LiteralPath $helper)) {
    Copy-Item -LiteralPath (Join-Path $root 'data\FM24_History_Ahron_Retention.ddt') -Destination $helper -Force
    Write-Host 'Copied the retention helper into the game folder.'
} else {
    Write-Host 'Skipped the retention helper: FM24 game folder not found.'
}

Write-Host "`nChecking editor data against the tested setup..."
$known = @{}
$problems = 0
foreach ($line in Get-Content -LiteralPath (Join-Path $root 'data\checksums.txt') -Encoding UTF8) {
    $sum, $name = $line -split '  ', 2
    $known[$name] = $true
    $path = Join-Path $editor $name
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "  missing:   $name"; $problems++
    } elseif ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $sum) {
        Write-Host "  different: $name"; $problems++
    }
}
$extra = @(Get-ChildItem -LiteralPath $editor -Filter '*.fmf' | Where-Object { -not $known.ContainsKey($_.Name) })

if ($problems) {
    Write-Host "`n$problems of $($known.Count) files are missing or not the tested version."
    Write-Host "Get the sortitoutsi 2026 start update (see README). A newer update should work, but it hasn't been tested."
} else {
    Write-Host "`nAll $($known.Count) files match the tested setup."
}
if ($extra.Count) {
    Write-Host "`nOther editor data files found. Untick them when you create the career:"
    $extra | ForEach-Object { Write-Host "  $($_.Name)" }
}
Write-Host "`nDone. Start FM24 from Steam and create a new career."
