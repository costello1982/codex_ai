#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

param(
    [string]$ImageName,
    [string]$ContainerName,
    [int]$HostPort,
    [string]$DbVolume
)

if (-not $ImageName) { $ImageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { 'ipam-app' } }
if (-not $ContainerName) { $ContainerName = if ($env:CONTAINER_NAME) { $env:CONTAINER_NAME } else { 'ipam-app' } }
if (-not $HostPort) { $HostPort = if ($env:HOST_PORT) { [int]$env:HOST_PORT } else { 8000 } }
if (-not $DbVolume) { $DbVolume = if ($env:DB_VOLUME) { $env:DB_VOLUME } else { 'ipam-db' } }

$projectRoot = (Resolve-Path "$PSScriptRoot/..")

podman build -t $ImageName -f (Join-Path $projectRoot 'Containerfile') $projectRoot

podman volume exists $DbVolume *> $null
if (-not $?) {
    podman volume create $DbVolume | Out-Null
}

podman container exists $ContainerName *> $null
if ($?) {
    podman rm -f $ContainerName | Out-Null
}

$runArgs = @(
    '--rm'
    '--name'
    $ContainerName
    '-p'
    "$HostPort:8000"
    '-v'
    "$DbVolume:/app/ipam-data"
    '-e'
    'IPAM_DB_PATH=/app/ipam-data/ipam.db'
    $ImageName
)

podman run @runArgs
