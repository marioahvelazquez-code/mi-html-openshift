# Guía de Despliegue a OpenShift Online

## Requisitos Previos

1. **Cuenta en OpenShift Online**
   - Crear cuenta en https://www.redhat.com/es/technologies/cloud-platforms/openshift/online
   - Obtener un cluster sandbox (gratuito por 30 días)

2. **Instalar OpenShift CLI (oc)**
   ```bash
   # Windows (PowerShell)
   choco install openshift-cli
   
   # macOS
   brew install openshift-cli
   
   # Linux
   wget https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz
   tar xzf openshift-client-linux.tar.gz -C /usr/local/bin
   ```

3. **GitHub Repository**
   - Tu código debe estar en GitHub (público o privado)
   - Copiar la URL del repositorio (ejemplo: https://github.com/tuusuario/repo.git)

4. **Base de Datos SQL Server accesible**
   - Debe estar disponible desde OpenShift (red, firewall, etc.)
   - Prepared: host, usuario, contraseña

## Paso 1: Preparar el Repositorio

### 1.1 Actualizar settings.py de Django

Ensure que `DEBUG=False` y `ALLOWED_HOSTS` están correctamente configurados:

```python
# backend/config/settings.py
DEBUG = False
ALLOWED_HOSTS = ["*"]  # O ser más específico con tu dominio
```

### 1.2 Commit de cambios

```bash
git add .
git commit -m "Preparar para OpenShift"
git push origin main
```

## Paso 2: Conectarse a OpenShift

```bash
# Acceder a OpenShift Online
oc login --server=https://api.sandbox.x8i5.p1.openshiftapps.com:6443

# Te pedirá token - cópialo desde https://console.redhat.com/openshift
# Y pégalo en la terminal
```

**En PowerShell (Windows):**
```powershell
oc login --server=https://api.sandbox.x8i5.p1.openshiftapps.com:6443
```

## Paso 3: Configurar Secretos

Antes de desplegar, actualiza los secretos con tus credenciales:

```bash
# Editar archivo de secretos
nano .openshift/configmap-secrets.yaml

# O directamente en OpenShift después del despliegue
oc edit secret django-secrets -n default
```

**Variables necesarias:**
```yaml
DB_NAME: tu_base_datos
DB_USER: tu_usuario_db
DB_PASS: tu_contraseña_db
DB_HOST: tu_servidor_sql_server.com
SECRET_KEY: genera-una-clave-secreta-segura
```

Generar SECRET_KEY segura:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## Paso 4: Ejecutar Despliegue

### Opción A: Script Bash (Linux/macOS)

```bash
cd .openshift
chmod +x deploy-openshift.sh
./deploy-openshift.sh default https://github.com/tuusuario/repo.git
```

### Opción B: Script PowerShell (Windows)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

.\\.openshift\\deploy-openshift.ps1 -Namespace "default" -GitHubRepo "https://github.com/tuusuario/repo.git"
```

### Opción C: Manual (paso a paso)

```bash
# 1. Crear namespace
oc create namespace default

# 2. Switch al namespace
oc project default

# 3. Crear ConfigMap y Secrets
oc apply -f .openshift/configmap-secrets.yaml

# 4. Crear ImageStreams
oc apply -f .openshift/imagestreams.yaml

# 5. Crear BuildConfigs
oc apply -f .openshift/buildconfigs.yaml

# 6. Iniciar builds
oc start-build backend --follow
oc start-build frontend --follow

# 7. Crear DeploymentConfigs y Services
oc apply -f .openshift/backend-dc.yaml
oc apply -f .openshift/frontend-dc.yaml

# 8. Crear Routes
oc apply -f .openshift/routes.yaml

# 9. Esperar a que se completen
oc rollout status dc/backend -n default --timeout=5m
oc rollout status dc/frontend -n default --timeout=5m
```

## Paso 5: Verificar Despliegue

```bash
# Ver estado de pods
oc get pods -n default

# Ver logs del backend
oc logs -f dc/backend -n default

# Ver logs del frontend
oc logs -f dc/frontend -n default

# Ver routes creadas
oc get routes -n default

# Ver URLs de acceso
echo "Frontend: $(oc get route frontend -n default -o jsonpath='{.spec.host}')"
echo "Backend: $(oc get route backend -n default -o jsonpath='{.spec.host}')"
```

## Troubleshooting

### Build falló

```bash
# Ver detalles del build
oc logs -f build/backend-1
oc logs -f build/frontend-1

# Problemas comunes:
# - Dockerfile no encontrado
# - Dependencias no instaladas (requirements.txt, package.json)
# - Puertos incorrectos
```

### Pod no inicia

```bash
# Ver descripción del pod
oc describe pod <pod-name> -n default

# Ver eventos
oc get events -n default --sort-by='.lastTimestamp'

# Problemas comunes:
# - imagePullBackOff: Imagen no construida o no disponible
# - CrashLoopBackOff: Aplicación se crasha, revisar logs
# - Pending: Falta recursos o el nodo está lleno
```

### Conectividad a Base de Datos

```bash
# Verificar si la BD es accesible desde el contenedor
oc exec -it <backend-pod> -- bash

# Dentro del pod, probar conexión
# (si está instalada la herramienta)
```

Si no conecta:
- Verificar firewall del servidor SQL Server
- Verificar que la BD está en una red accesible desde OpenShift
- Verificar credenciales en el Secret

### Frontend no carga cuando acceso a Backend

Asegúrate que en `frontend/nginx.conf`:
```nginx
location /api/ {
    proxy_pass http://backend-service:8000;
    # ... resto de headers
}
```

Y que la URL en el frontend es relativa:
```typescript
// Correcto
const response = await fetch('/api/endpoint');

// Incorrecto
const response = await fetch('http://localhost:8000/api/endpoint');
```

## Acceso a la Aplicación

Una vez completado el despliegue:

1. **Frontend**: `https://<frontend-route>`
2. **Backend API**: `https://<backend-route>/api/`

Las URLs estarán disponibles en la salida del script o con:
```bash
oc get routes -n default
```

## Scale Up/Down

Para escalar el número de replicas:

```bash
# Frontend (por defecto 2)
oc scale dc frontend --replicas=3

# Backend (por defecto 1)
oc scale dc backend --replicas=2
```

## Actualizaciones Futuras

Para desplegar cambios nuevos:

```bash
# Hacer push a GitHub
git push origin main

# Iniciar nuevo build
oc start-build backend --follow
oc start-build frontend --follow

# OpenShift redesplegará automáticamente con la nueva imagen
```

## Monitoreo

```bash
# Pod metrics
oc top pods -n default

# Node metrics
oc top nodes

# Ver Rolling Updates en tiempo real
watch oc get pods -n default
```

## Limpiar Recursos

```bash
# Eliminar todo del namespace
oc delete all --all -n default

# Eliminar namespace completo
oc delete namespace default
```

## Recursos Útiles

- [OpenShift CLI Documentation](https://docs.openshift.com/online/cli_reference/index.html)
- [OpenShift Building Images](https://docs.openshift.com/online/builds/creating-build-inputs.html)
- [DeploymentConfig Reference](https://docs.openshift.com/online/rest_api/apps_apis/deploymentconfig-apps-openshift-io-v1.html)

---

**¿Necesitas ayuda?** Contacta al equipo de DevOps o ejecuta:
```bash
oc version
oc status
oc get all
```
