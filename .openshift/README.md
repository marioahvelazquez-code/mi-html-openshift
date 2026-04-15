# Archivos de Despliegue a OpenShift

## 📋 Descripción de Archivos

### Manifiestos de Kubernetes/OpenShift

- **`imagestreams.yaml`** - Define los ImageStreams para backend y frontend
- **`buildconfigs.yaml`** - Configuración de builds automáticos desde GitHub
- **`configmap-secrets.yaml`** - Variables de entorno y credenciales
- **`backend-dc.yaml`** - DeploymentConfig + Service para backend
- **`frontend-dc.yaml`** - DeploymentConfig + Service para frontend  
- **`routes.yaml`** - Routes para exponer aplicaciones al exterior

### Scripts de Despliegue

- **`deploy-openshift.sh`** - Script bash para Linux/macOS
- **`deploy-openshift.ps1`** - Script PowerShell para Windows

### Documentación

- **`DEPLOYMENT_GUIDE.md`** - Guía completa de despliegue paso a paso
- **`CHANGES.md`** - Cambios realizados en la configuración
- **`README.md`** - Este archivo

### Archivos de Referencia

- **`django-settings-prod.py`** - Configuración recomendada para settings.py
- **`../requirements.txt.prod`** - Dependencies para producción
- **`../.env.prod.example`** - Template de variables de entorno

---

## 🚀 Quick Start

### 1. Preparación (5 minutos)

```bash
# Instalar OpenShift CLI
# Windows: choco install openshift-cli
# macOS: brew install openshift-cli

# Conectarse a OpenShift Online
oc login --server=https://api.sandbox.x8i5.p1.openshiftapps.com:6443
# Pegar token cuando se pida
```

### 2. Configurar Secretos (2 minutos)

```bash
# Editar credenciales de BD
nano configmap-secrets.yaml
# Cambiar DB_HOST, DB_USER, DB_PASS, DB_NAME
# Generar SECRET_KEY nuevo
```

### 3. Desplegar (10-15 minutos)

**Opción Bash:**
```bash
chmod +x deploy-openshift.sh
./deploy-openshift.sh default https://github.com/tuusuario/microservicios.git
```

**Opción PowerShell:**
```powershell
.\deploy-openshift.ps1 -Namespace "default" `
  -GitHubRepo "https://github.com/tuusuario/microservicios.git"
```

### 4. Verificar (3 minutos)

```bash
# Ver pods corriendo
oc get pods -n default

# Ver URLs generadas
oc get routes -n default

# Monitorear logs
oc logs -f dc/backend -n default
```

---

## 📝 Pasos Antes de Desplegar

- [ ] Actualizar `backend/requirements.txt` con versiones de `requirements.txt.prod`
- [ ] Actualizar `backend/config/settings.py` con configuración de `django-settings-prod.py`
- [ ] Agregar `django-cors-headers` a INSTALLED_APPS
- [ ] Cambiar `DEBUG = False` en settings.py
- [ ] Generar `SECRET_KEY` nuevo con: `python manage.py shell` → `from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`
- [ ] Crear Personal Access Token en GitHub (para webhooks)
- [ ] Probar localmente: `docker-compose up`
- [ ] Push a GitHub: `git push origin main`

---

## 🔧 Recursos

| Tarea | Comando |
|-------|---------|
| Ver estado general | `oc status` |
| Listar todos los pods | `oc get pods -n default` |
| Ver logs de backend | `oc logs -f dc/backend` |
| Ver logs de frontend | `oc logs -f dc/frontend` |
| Editar secret | `oc edit secret django-secrets -n default` |
| Reiniciar despliegue | `oc rollout latest dc/backend` |
| Ver eventos | `oc get events -n default` |
| Eliminar todo | `oc delete all --all` |

---

## 🐛 Troubleshooting

### "Build fails - Dockerfile not found"
- Verificar que `contextDir` en buildconfigs.yaml apunta a la carpeta correcta
- Verificar que el Dockerfile está presente en la rama main

### "ImagePullBackOff"
- El build no se completó
- Ejecutar: `oc logs -f build/backend-1`

### "CrashLoopBackOff"  
- La aplicación se crasha al iniciar
- Revisar logs: `oc logs -f pod/<pod-name>`
- Verificar credenciales de BD

### "Frontend no conecta a Backend"
- Verificar que `frontend/nginx.conf` proxy_pass es correcto: `http://backend-service:8000`
- Verificar CORS_ALLOWED_ORIGINS en Django settings

---

## 📚 Documentación Completa

Ver **DEPLOYMENT_GUIDE.md** para instrucciones detalladas.

---

## ⚠️ Notas Importantes

1. **Secret Key**: DEBE ser cambiad en producción. Generar con `get_random_secret_key()`
2. **Debug Mode**: DEBE ser False en producción
3. **Base de Datos**: Debe ser accesible desde OpenShift (firewall/red)
4. **Replica Count**: Por defecto backend=1, frontend=2. Ajustar según necesidad
5. **Recursos**: Configurados con 500m CPU y 512Mi RAM. Monitorear y ajustar

---

## 📞 Soporte

Para dudas específicas de OpenShift:
- Documentación oficial: https://docs.openshift.com/online
- CLI Help: `oc --help` o `oc <command> --help`

Fecha: 2026-03-25
