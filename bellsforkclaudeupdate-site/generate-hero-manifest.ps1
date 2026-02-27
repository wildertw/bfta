# Generates assets/hero/manifest.json containing every image found in assets/hero/
# Run from your site root folder (the folder that contains index.html and assets/)

$ErrorActionPreference = 'Stop'

$root = Get-Location
$heroDir = Join-Path $root 'assets\hero'
if (-not (Test-Path $heroDir)) {
  throw "Could not find folder: $heroDir (make sure you're running this from your site root)"
}

$exts = @('.jpg','.jpeg','.png','.webp','.gif')
$images = Get-ChildItem $heroDir -File | Where-Object { $exts -contains $_.Extension.ToLower() } | Sort-Object Name | ForEach-Object { $_.Name }

$manifestPath = Join-Path $heroDir 'manifest.json'
@{ images = $images } | ConvertTo-Json -Depth 3 | Set-Content -Path $manifestPath -Encoding utf8

Write-Host "Wrote $manifestPath with $($images.Count) images."
