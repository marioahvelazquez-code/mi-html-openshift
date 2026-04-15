# Script de despliegue a OpenShift (PowerShell)
# Uso: .\deploy-openshift.ps1 -Namespace "default" -GitHubRepo "https://github.com/..."

param(
    [string]$Namespace = "default",
    [string]$GitHubRepo = ""
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Desployando a OpenShift" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Namespace: $Namespace" -ForegroundColor Yellow
Write-Host ""

# Verify oc is installed
if (-not (Get-Command oc -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'oc' CLI no esta instalado. Por favor instala OpenShift CLI." -ForegroundColor Red
    exit 1
}

# Check if logged in
$testLogin = oc auth can-i create deploymentconfigs --namespace=$Namespace 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: No estas conectado a OpenShift o no tienes permisos en $Namespace" -ForegroundColor Red
    Write-Host "Ejecuta: oc login" -ForegroundColor Yellow
    exit 1
}

# Create namespace
Write-Host "📁 Creando namespace si no existe..." -ForegroundColor Cyan
oc create namespace $Namespace 2>$null

# Switch to namespace
oc project $Namespace

# Create ConfigMap and Secrets
Write-Host "⚙️  Creando ConfigMap..." -ForegroundColor Cyan
oc apply -f .\.openshift\configmap-secrets.yaml

# Update BuildConfigs with GitHub repo if provided
if ($GitHubRepo) {
    Write-Host "🔨 Actualizando BuildConfigs..." -ForegroundColor Cyan
    $buildConfigContent = Get-Content .\.openshift\buildconfigs.yaml -Raw
    $buildConfigContent = $buildConfigContent -replace 'https://github.com/YOUR_GITHUB_REPO.git', $GitHubRepo
    Set-Content .\.openshift\buildconfigs.yaml $buildConfigContent
}

# Create ImageStreams
Write-Host "🖼️  Creando ImageStreams..." -ForegroundColor Cyan
oc apply -f .\.openshift\imagestreams.yaml

# Create BuildConfigs
Write-Host "🔨 Creando BuildConfigs..." -ForegroundColor Cyan
oc apply -f .\.openshift\buildconfigs.yaml

# Start builds
Write-Host "🚀 Iniciando builds..." -ForegroundColor Cyan
Write-Host "  - Backend build..." -ForegroundColor Yellow
oc start-build backend --follow

Write-Host "  - Frontend build..." -ForegroundColor Yellow
oc start-build frontend --follow

# Create DeploymentConfigs and Services
Write-Host "📦 Creando DeploymentConfigs y Services..." -ForegroundColor Cyan
oc apply -f .\.openshift\backend-dc.yaml
oc apply -f .\.openshift\frontend-dc.yaml

# Create Routes
Write-Host "🌐 Creando Routes..." -ForegroundColor Cyan
oc apply -f .\.openshift\routes.yaml

# Wait for deployments
Write-Host "⏳ Esperando a que se completen los desployos..." -ForegroundColor Cyan
oc rollout status dc/backend -n $Namespace --timeout=5m
oc rollout status dc/frontend -n $Namespace --timeout=5m

# Get route information
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✅ Despliegue completado!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

$frontendRoute = oc get route frontend -n $Namespace -o jsonpath='{.spec.host}' 2>$null
$backendRoute = oc get route backend -n $Namespace -o jsonpath='{.spec.host}' 2>$null

Write-Host "URLs de acceso:" -ForegroundColor Yellow
Write-Host "  Frontend: $frontendRoute" -ForegroundColor Cyan
Write-Host "  Backend:  $backendRoute" -ForegroundColor Cyan
Write-Host ""
Write-Host "Monitorear despliegues:" -ForegroundColor Yellow
Write-Host "  oc logs -f dc/backend -n $Namespace" -ForegroundColor Gray
Write-Host "  oc logs -f dc/frontend -n $Namespace" -ForegroundColor Gray
