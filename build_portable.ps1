# Build a portable ZIP package for Plex Cataloger.
# Produces a one-file executable and packages it into dist\PlexCatalogerPortable_<timestamp>.zip.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $projectRoot 'dist'
$specFile = Join-Path $projectRoot 'PlexCataloger.spec'
$exeName = 'PlexCataloger.exe'
$portableName = "PlexCatalogerPortable_{0}.zip" -f (Get-Date -Format 'yyyyMMddHHmmss')
$tempDir = Join-Path $distDir 'PlexCatalogerPortable'

if(-not (Test-Path $specFile)){
    Write-Error "Spec file not found: $specFile"
    exit 1
}

$pythonExe = 'python'
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if(Test-Path $venvPython){
    $pythonExe = $venvPython
}

Write-Host "Building one-file executable from $specFile..."
& $pythonExe -m PyInstaller $specFile
if($LASTEXITCODE -ne 0){
    Write-Error 'PyInstaller build failed.'
    exit $LASTEXITCODE
}

$exePath = Join-Path $distDir $exeName
if(-not (Test-Path $exePath)){
    Write-Error "Expected executable not found: $exePath"
    exit 1
}

if(Test-Path $tempDir){
    Remove-Item $tempDir -Recurse -Force
}

New-Item -ItemType Directory -Path $tempDir | Out-Null
Copy-Item $exePath -Destination $tempDir

$zipPath = Join-Path $distDir $portableName
if(Test-Path $zipPath){
    Remove-Item $zipPath -Force
}

Compress-Archive -Path (Join-Path $tempDir '*') -DestinationPath $zipPath -Force
Remove-Item $tempDir -Recurse -Force
Write-Host "Portable ZIP created: $zipPath"

# Create a source ZIP excluding build artifacts and virtual environment
$sourceName = "PlexCatalogerSource_{0}.zip" -f (Get-Date -Format 'yyyyMMddHHmmss')
$sourceTemp = Join-Path $distDir 'PlexCatalogerSource'
$excludeNames = @('dist', 'build', '.venv', '.git', '__pycache__')

if(Test-Path $sourceTemp){
    Remove-Item $sourceTemp -Recurse -Force
}
New-Item -ItemType Directory -Path $sourceTemp | Out-Null

Get-ChildItem -Path $projectRoot -Force | Where-Object {
    $excludeNames -notcontains $_.Name
} | ForEach-Object {
    if($_.PSIsContainer){
        Copy-Item -Path $_.FullName -Destination $sourceTemp -Recurse -Force
    } else {
        Copy-Item -Path $_.FullName -Destination $sourceTemp -Force
    }
}

$sourceZipPath = Join-Path $distDir $sourceName
if(Test-Path $sourceZipPath){
    Remove-Item $sourceZipPath -Force
}
Compress-Archive -Path (Join-Path $sourceTemp '*') -DestinationPath $sourceZipPath -Force
Remove-Item $sourceTemp -Recurse -Force
Write-Host "Source ZIP created: $sourceZipPath"
