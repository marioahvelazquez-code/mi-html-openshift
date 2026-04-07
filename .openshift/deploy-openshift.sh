#!/bin/bash

# Script de despliegue a OpenShift
# Uso: ./deploy-openshift.sh <namespace> <github-repo-url>

set -e

NAMESPACE=${1:-default}
GITHUB_REPO=${2:-.}

echo "=========================================="
echo "Desployando a OpenShift"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo ""

# Verify oc is installed and user is logged in
if ! command -v oc &> /dev/null; then
    echo "❌ 'oc' CLI no está instalado. Por favor instala OpenShift CLI."
    exit 1
fi

# Check if logged in
if ! oc auth can-i create deploymentconfigs --namespace=$NAMESPACE &> /dev/null; then
    echo "❌ No estás conectado a OpenShift, o no tienes permisos en el namespace $NAMESPACE"
    echo "Por favor ejecuta: oc login"
    exit 1
fi

# Create namespace if it doesn't exist
echo "📁 Creando namespace si no existe..."
oc create namespace $NAMESPACE 2>/dev/null || true

# Switch to namespace
oc project $NAMESPACE

# Create ConfigMap and Secrets
echo "⚙️  Creando ConfigMap..."
oc apply -f .openshift/configmap-secrets.yaml

# Update BuildConfigs with GitHub repo URL
echo "🔨 Actualizando BuildConfigs..."
if [ "$GITHUB_REPO" != "." ]; then
    sed -i "s|https://github.com/YOUR_GITHUB_REPO.git|$GITHUB_REPO|g" .openshift/buildconfigs.yaml
fi

# Create ImageStreams
echo "🖼️  Creando ImageStreams..."
oc apply -f .openshift/imagestreams.yaml

# Create BuildConfigs
echo "🔨 Creando BuildConfigs..."
oc apply -f .openshift/buildconfigs.yaml

# Start builds
echo "🚀 Iniciando builds..."
echo "  - Backend build..."
oc start-build backend --follow || true

echo "  - Frontend build..."
oc start-build frontend --follow || true

# Create DeploymentConfigs and Services
echo "📦 Creando DeploymentConfigs y Services..."
oc apply -f .openshift/backend-dc.yaml
oc apply -f .openshift/frontend-dc.yaml

# Create Routes
echo "🌐 Creando Routes..."
oc apply -f .openshift/routes.yaml

# Wait for deployments to complete
echo "⏳ Esperando a que se completen los desployos..."
oc rollout status dc/backend -n $NAMESPACE --timeout=5m
oc rollout status dc/frontend -n $NAMESPACE --timeout=5m

# Get route information
echo ""
echo "=========================================="
echo "✅ Despliegue completado!"
echo "=========================================="
echo ""
echo "URLs de acceso:"
echo "  Frontend: $(oc get route frontend -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo 'Esperando...')"
echo "  Backend:  $(oc get route backend -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo 'Esperando...')"
echo ""
echo "Monitorear despliegues:"
echo "  oc logs -f dc/backend -n $NAMESPACE"
echo "  oc logs -f dc/frontend -n $NAMESPACE"
