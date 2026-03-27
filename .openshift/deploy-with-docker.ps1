# Script de despliegue a OpenShift usando Docker
# Uso: .\deploy-with-docker.ps1 -Token "..." -Server "..." -GitRepo "..."

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

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Desployando a OpenShift con Docker" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "Namespace: $Namespace" -ForegroundColor Yellow
Write-Host ""

# Verificar que Docker está disponible
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker no está instalado o no está en PATH" -ForegroundColor Red
    exit 1
}

# Obtener directorio del proyecto
$projectDir = Split-Path -Parent $PSScriptRoot
$projectName = Split-Path -Leaf $projectDir

Write-Host "Proyecto: $projectDir" -ForegroundColor Yellow
Write-Host ""

# Función para ejecutar comandos oc dentro de Docker
function Invoke-OC {
    param([string[]]$Arguments)
    
    $cmd = @($Arguments)
    $result = & docker run --rm `
        -v "${projectDir}:/workspace" `
        -e KUBECONFIG=/tmp/kubeconfig `
        quay.io/openshift/origin-cli:latest `
        oc @cmd
    
    return $result
}

# Paso 1: Login
Write-Host "🔐 Conectando a OpenShift..." -ForegroundColor Cyan
docker run --rm `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc login --token=$Token --server=$Server

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: No se pudo conectar a OpenShift" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Conectado a OpenShift" -ForegroundColor Green
Write-Host ""

# Paso 2: Crear namespace
Write-Host "📁 Creando namespace '$Namespace'..." -ForegroundColor Cyan
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc create namespace $Namespace 2>$null

# Switch al namespace
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc project $Namespace

Write-Host ""

# Paso 3: Crear ConfigMap y Secrets
Write-Host "⚙️  Creando ConfigMap y Secrets..." -ForegroundColor Cyan
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /workspace/.openshift/configmap-secrets.yaml

Write-Host ""

# Paso 4: Crear ImageStreams
Write-Host "🖼️  Creando ImageStreams..." -ForegroundColor Cyan
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /workspace/.openshift/imagestreams.yaml

Write-Host ""

# Paso 5: Actualizar y crear BuildConfigs
Write-Host "🔨 Creando BuildConfigs..." -ForegroundColor Cyan

# Leer el archivo y reemplazar URL del repo
$buildConfigContent = Get-Content "$projectDir\.openshift\buildconfigs.yaml" -Raw
$buildConfigContent = $buildConfigContent -replace 'https://github.com/YOUR_GITHUB_REPO.git', $GitRepo

# Crear archivo temporal
$tempBuildConfig = "$env:TEMP\buildconfigs-temp.yaml"
Set-Content $tempBuildConfig $buildConfigContent

# Aplicar BuildConfigs
docker run --rm `
    -v "${projectDir}:/workspace" `
    -v "${tempBuildConfig}:/tmp/buildconfigs.yaml" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /tmp/buildconfigs.yaml

# Limpiar
Remove-Item $tempBuildConfig

Write-Host ""

# Paso 6: Iniciar builds
Write-Host "🚀 Iniciando builds..." -ForegroundColor Cyan

Write-Host "  📦 Backend build..." -ForegroundColor Yellow
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc start-build backend --follow

Write-Host ""
Write-Host "  📦 Frontend build..." -ForegroundColor Yellow
docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc start-build frontend --follow

Write-Host ""

# Paso 7: Crear DeploymentConfigs y Services
Write-Host "📦 Creando DeploymentConfigs y Services..." -ForegroundColor Cyan

docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /workspace/.openshift/backend-dc.yaml

docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /workspace/.openshift/frontend-dc.yaml

Write-Host ""

# Paso 8: Crear Routes
Write-Host "🌐 Creando Routes..." -ForegroundColor Cyan

docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc apply -f /workspace/.openshift/routes.yaml

Write-Host ""

# Paso 9: Esperar a que se completen los desployos
Write-Host "⏳ Esperando a que se completen los desployos..." -ForegroundColor Cyan

docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc rollout status dc/backend -n $Namespace --timeout=10m

docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc rollout status dc/frontend -n $Namespace --timeout=10m

Write-Host ""

# Paso 10: Mostrar información final
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✅ Despliegue completado!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Host "URLs de acceso:" -ForegroundColor Yellow
Write-Host ""

$frontendRoute = docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc get route frontend -n $Namespace -o jsonpath='{.spec.host}' 2>$null

$backendRoute = docker run --rm `
    -v "${projectDir}:/workspace" `
    -e KUBECONFIG=/tmp/kubeconfig `
    quay.io/openshift/origin-cli:latest `
    oc get route backend -n $Namespace -o jsonpath='{.spec.host}' 2>$null

if ($frontendRoute) {
    Write-Host "  🌐 Frontend: https://$frontendRoute" -ForegroundColor Cyan
} else {
    Write-Host "  🌐 Frontend: (esperando...)" -ForegroundColor Gray
}

if ($backendRoute) {
    Write-Host "  🌐 Backend:  https://$backendRoute/api" -ForegroundColor Cyan
} else {
    Write-Host "  🌐 Backend: (esperando...)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Esperar a que los pods estén en running"
Write-Host "  2. Ver logs: docker run --rm quay.io/openshift/origin-cli:latest oc logs -f dc/backend"
Write-Host "  3. Ver pods: docker run --rm quay.io/openshift/origin-cli:latest oc get pods"
Write-Host ""
