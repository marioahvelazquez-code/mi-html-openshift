# 🎯 Referencia Rápida - Comandos OpenShift

## 🔐 Autenticación

```bash
# Login a OpenShift Online
oc login --server=https://api.sandbox.x8i5.p1.openshiftapps.com:6443

# Logout
oc logout

# Ver usuario actual
oc whoami

# Ver servidor actual
oc cluster-info
```

## 📦 Gestionar el Proyecto

```bash
# Crear namespace
oc create namespace myproject

# Listar namespaces
oc get namespace

# Cambiar a namespace
oc project myproject

# Ver proyecto actual
oc project -q
```

## 🖼️ ImageStreams

```bash
# Listar ImageStreams
oc get imagestream

# Ver detalles de ImageStream
oc describe imagestream backend

# Listar tags disponibles
oc get imagestream backend -o json | jq '.status.tags'
```

## 🔨 Builds

```bash
# Listar BuildConfigs
oc get buildconfig

# Ver detalles
oc describe buildconfig backend

# Listar builds
oc get builds

# Ver logs de un build
oc logs -f build/backend-1

# Iniciar build manualmente
oc start-build backend

# Iniciar build y seguir logs
oc start-build backend --follow

# Cancelar build en progreso
oc cancel-build backend-1

# Reconstruir última compilación
oc start-build --from-build=backend-1
```

## 📦 Pods & Containers

```bash
# Listar todos los pods
oc get pods

# Listar pods con detalles
oc get pods -o wide

# Ver logs de pod
oc logs pod/backend-1-abc123

# Seguir logs en tiempo real
oc logs -f pod/backend-1-abc123

# Seguir logs de DeploymentConfig
oc logs -f dc/backend

# Ejecutar comando en pod
oc exec pod/backend-1-abc123 -- ls -la

# Shell interactivo en pod
oc exec -it pod/backend-1-abc123 -- /bin/bash

# Copiar archivos desde pod
oc cp backend-1-abc123:/app/file.txt ./file.txt

# Copiar archivos a pod
oc cp ./file.txt backend-1-abc123:/app/
```

## 🚀 DeploymentConfigs

```bash
# Listar DeploymentConfigs
oc get dc

# Ver detalles
oc describe dc backend

# Ver estado de rollout
oc rollout status dc/backend

# Revert a despliegue anterior
oc rollout undo dc/backend

# Escalar replicas
oc scale --replicas=3 dc/backend

# Forzar redeploy sin cambios de imagen
oc rollout latest dc/backend

# Ver historial de deployments
oc rollout history dc/backend
```

## 🔌 Services

```bash
# Listar services
oc get svc

# Ver detalles
oc describe svc backend-service

# Exponer un service (crear route)
oc expose svc backend-service
```

## 🌐 Routes

```bash
# Listar routes
oc get routes

# Ver detalles de route
oc describe route frontend

# Editar route
oc edit route frontend

# Crear route manualmente
oc create route edge frontend \
  --service=frontend-service \
  --hostname=frontend.example.com

# Eliminar route
oc delete route frontend
```

## 🔐 Secrets & ConfigMaps

```bash
# Listar secrets
oc get secrets

# Ver secret (decodificado)
oc get secret django-secrets -o jsonpath='{.data.DB_PASS}' | base64 -d

# Editar secret
oc edit secret django-secrets

# Crear secret desde .env
oc create secret generic app-secrets --from-file=.env

# Listar ConfigMaps
oc get configmap

# Editar ConfigMap
oc edit configmap django-config

# Crear ConfigMap desde archivo
oc create configmap app-config --from-file=config.properties
```

## 📊 Monitoreo

```bash
# Ver recursos utilizados por pods
oc top pods

# Ver recursos utilizados por nodes
oc top nodes

# Ver eventos del namespace
oc get events

# Ver eventos ordenados por tiempo
oc get events --sort-by='.lastTimestamp'

# Monitorear cambios en pods
watch oc get pods

# Ver status general del namespace
oc status
```

## 🔍 Debugging

```bash
# Ver todos los recursos
oc get all

# Ver descripción detallada
oc describe pod pod-name

# Ver YAML de recurso
oc get pod pod-name -o yaml

# Ver JSON formatteado
oc get pod pod-name -o json | python -m json.tool

# Listar eventos ordenados
oc get events -n default --sort-by='.lastTimestamp'

# Test conectividad entre pods
oc exec -it frontend-1-xyz -- \
  curl http://backend-service:8000/admin/

# Revisar variables de entorno en pod
oc exec pod-name -- env | sort

# Test DNS
oc exec -it pod-name -- nslookup backend-service
```

## 📝 Editar Recursos

```bash
# Editar recurso con editor predeterminado
oc edit dc backend

# Editar y aplicar cambios desde YAML
oc apply -f backend-dc.yaml

# Reemplazar recurso completo
oc replace -f backend-dc.yaml

# Patch un recurso
oc patch dc backend \
  -p '{"spec":{"replicas":3}}'

# Actualizar imagen
oc set image dc/backend \
  backend=myregistry/myapp:v1
```

## 🗑️ Limpiar Recursos

```bash
# Eliminar pod
oc delete pod pod-name

# Eliminar DeploymentConfig
oc delete dc backend

# Eliminar todos los pods en namespace
oc delete pods --all

# Eliminar todo en namespace
oc delete all --all

# Eliminar namespace (elimina todo adentro)
oc delete namespace myproject

# Eliminar recurso específico
oc delete route backend
oc delete service backend-service
oc delete configmap django-config
```

## 📂 Contextos y Proyectos

```bash
# Ver contextos guardados
oc config get-contexts

# Cambiar contexto
oc config use-context mycontext

# Ver configuración actual
oc config view

# Establecer namespace por defecto
oc config set-context --current --namespace=default
```

## 🔗 Webhooks (Builds automáticos)

```bash
# Ver webhook URL
oc describe bc backend | grep "webhook.*github"

# El formato es:
# https://api.sandbox.x8i5.p1.openshiftapps.com:6443/apis/build.openshift.io/v1/namespaces/default/buildconfigs/backend/webhooks/github/secret-token/trigger
```

En GitHub Settings → Webhooks → Add webhook:
- Payload URL: (arriba)
- Content type: application/json
- Events: Push events

---

## 💡 Tips Útiles

```bash
# Alias útil en bash
alias oc-logs='oc logs -f'
alias oc-status='oc status'
alias oc-pods='oc get pods -o wide'

# Ver multiple pods en tiempo real
watch 'oc get pods -o wide'

# Ver últimas líneas de logs
oc logs --tail=50 dc/backend

# Buscar pod por nombre
oc get pods | grep backend

# Ver CPU/Memory en tiempo real
oc top pods --containers

# Dump completo de recurso
oc get all -o yaml > backup.yaml
```

---

## 📚 Variables de Entorno Útiles

```bash
# En ~/.bashrc o ~/.zshrc
export OPENSHIFT_SERVER=https://api.sandbox.x8i5.p1.openshiftapps.com:6443
export OPENSHIFT_NAMESPACE=default

# Luego:
oc login --server=$OPENSHIFT_SERVER
oc project $OPENSHIFT_NAMESPACE
```

---

## 🆘 Comandos de Emergencia

```bash
# Forzar eliminación de pod (si está stuck)
oc delete pod pod-name --grace-period=0 --force

# Reiniciar deployment
oc rollout restart dc/backend

# Recuperarse de error de imagen
oc set env dc/backend \
  IMAGE_PULL_POLICY=Always

# Reset permisos de service account
oc policy add-role-to-user \
  system:deployer \
  -z default
```

---

Última actualización: 2026-03-25
