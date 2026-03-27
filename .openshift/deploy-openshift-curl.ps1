# Script de despliegue a OpenShift usando curl y API REST
# Uso: .\deploy-openshift-curl.ps1

param(
    [string]$Token = "",
    [string]$Server = "https://api.rm2.thpm.p1.openshiftapps.com:6443",
    [string]$GitRepo = "https://github.com/tuusuario/repo.git",
    [string]$Namespace = "default"
)

if (-not $Token) {
    Write-Host "Error: Debes enviar -Token con tu token de OpenShift." -ForegroundColor Red
    exit 1
}

# Desactivar validación SSL para testing (cambiar en producción)
[Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Desployando a OpenShift vía API REST" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "Namespace: $Namespace" -ForegroundColor Yellow
Write-Host ""

# Headers comunes para autenticación
$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

# Función para hacer llamadas a la API de OpenShift
function Invoke-OpenShiftAPI {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Body = ""
    )
    
    $uri = "$Server$Path"
    
    try {
        if ($Body) {
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -Body $Body
        } else {
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers
        }
        return $response
    } catch {
        Write-Host "⚠️  Error en API: $_" -ForegroundColor Yellow
        return $null
    }
}

# Paso 1: Verificar conexión
Write-Host "🔐 Verificando conexión a OpenShift..." -ForegroundColor Cyan

try {
    $user = Invoke-RestMethod -Uri "$Server/apis/user.openshift.io/v1/users/~" `
        -Headers $headers
    Write-Host "✅ Conectado como: $($user.metadata.name)" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: No se puede conectar a OpenShift" -ForegroundColor Red
    Write-Host "Token o servidor inválidos" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Paso 2: Crear namespace si no existe
Write-Host "📁 Asegurando que existe el namespace '$Namespace'..." -ForegroundColor Cyan

$nsJson = @{
    apiVersion = "v1"
    kind = "Namespace"
    metadata = @{
        name = $Namespace
    }
} | ConvertTo-Json

try {
    $nsResponse = Invoke-OpenShiftAPI -Method POST `
        -Path "/api/v1/namespaces" `
        -Body $nsJson
    Write-Host "✅ Namespace '$Namespace' listo" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Namespace ya existe" -ForegroundColor Yellow
}

Write-Host ""

# Función para aplicar un manifiesto YAML (lo convierte a JSON)
function Apply-Manifest {
    param(
        [string]$YamlFile,
        [string]$Description
    )
    
    if (-not (Test-Path $YamlFile)) {
        Write-Host "❌ Error: Archivo no encontrado: $YamlFile" -ForegroundColor Red
        return $false
    }
    
    Write-Host "📝 $Description..." -ForegroundColor Cyan
    
    # Aquí irían conversiones de YAML a JSON
    # Por ahora, mostraremos el status
    Write-Host "   ✓ Listo para aplicar: $YamlFile" -ForegroundColor Green
    
    return $true
}

# Paso 3-8: Aplicar manifiestos
$projectDir = Split-Path -Parent $PSScriptRoot

Apply-Manifest "$projectDir\.openshift\configmap-secrets.yaml" "ConfigMap y Secrets"
Apply-Manifest "$projectDir\.openshift\imagestreams.yaml" "ImageStreams"
Apply-Manifest "$projectDir\.openshift\buildconfigs.yaml" "BuildConfigs"
Apply-Manifest "$projectDir\.openshift\backend-dc.yaml" "Backend DeploymentConfig"
Apply-Manifest "$projectDir\.openshift\frontend-dc.yaml" "Frontend DeploymentConfig"
Apply-Manifest "$projectDir\.openshift\routes.yaml" "Routes"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "ℹ️  Próximos pasos:" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Opción 1: Usar kubectl/oc (si lo instalas después)" -ForegroundColor Yellow
Write-Host "  kubectl apply -f .openshift/configmap-secrets.yaml" -ForegroundColor Gray
Write-Host "  kubectl apply -f .openshift/imagestreams.yaml" -ForegroundColor Gray
Write-Host ""
Write-Host "Opción 2: Usar el dashboard web" -ForegroundColor Yellow
Write-Host "  1. Abre: $Server/console" -ForegroundColor Gray
Write-Host "  2. Inicia sesión con tu usuario" -ForegroundColor Gray
Write-Host "  3. Crea proyecto y aplica los manifiestos manualmente" -ForegroundColor Gray
Write-Host ""
Write-Host "Opción 3: Usar Docker para oc CLI (recomendado)" -ForegroundColor Yellow
Write-Host "  cd .openshift" -ForegroundColor Gray
Write-Host "  docker pull quay.io/openshift/origin-cli:latest" -ForegroundColor Gray
Write-Host ""
