# ✅ Checklist Pre-Despliegue a OpenShift

Complete todas las siguientes tareas antes de ejecutar el despliegue.

## 📋 Pre-requisitos

- [ ] Cuenta en OpenShift Online (https://console.redhat.com/openshift)
- [ ] OpenShift CLI instalado (`oc version` funciona)
- [ ] Conectado a OpenShift: `oc whoami` retorna tu usuario
- [ ] Repositorio en GitHub (público o privado)
- [ ] Git instalado y configurado

## 🔐 Configuración de Seguridad

- [ ] Generar nueva `SECRET_KEY` segura para producción
  ```bash
  python manage.py shell
  from django.core.management.utils import get_random_secret_key
  print(get_random_secret_key())  # Copiar este valor
  ```

- [ ] Actualizar `backend/config/settings.py`:
  ```python
  DEBUG = False  # ← IMPORTANTE
  SECRET_KEY = 'tu-valor-generado-aqui'
  ALLOWED_HOSTS = ['*']  # O ['tu-dominio.com', 'backend-route']
  ```

- [ ] Agregar `django-cors-headers` a `requirements.txt`:
  ```
  django-cors-headers>=3.14.0
  gunicorn>=21.2.0
  ```

- [ ] Actualizar `backend/config/settings.py` INSTALLED_APPS:
  ```python
  INSTALLED_APPS = [
      ...
      'corsheaders',
  ]
  ```

- [ ] Agregar CORS_ALLOWED_ORIGINS a `settings.py`:
  ```python
  CORS_ALLOWED_ORIGINS = [
      'http://localhost:3000',
      'http://localhost:8088',
  ]
  # Se actualizará después con URLs de OpenShift
  ```

## 🗄️ Base de Datos

- [ ] Verificar conexión local a SQL Server:
  ```bash
  # Con sqlcmd o similar
  sqlcmd -S YOUR_HOST,1433 -U YOUR_USER -P YOUR_PASS -Q "SELECT @@VERSION"
  ```

- [ ] Credenciales preparadas:
  - [ ] Host: `________________`
  - [ ] Database: `________________`
  - [ ] User: `________________`
  - [ ] Password: `________________`

- [ ] Ensure BD está accesible desde "outside" (firewall abierto si es necesario)

## 🐳 Dockerfiles

- [ ] Backend Dockerfile usa `gunicorn` ✓
- [ ] Frontend Dockerfile usa multi-stage build ✓
- [ ] Frontend Dockerfile incluye `nginx.conf` ✓
- [ ] Verificar que builds funcionan localmente:
  ```bash
  docker-compose build
  docker-compose up
  # Probar http://localhost:8088
  ```

## 📦 Git Repository

- [ ] El código está en una rama `main` o `master`
- [ ] Todos los cambios fueron committed:
  ```bash
  git status  # No debe haber archivos sin commitar
  ```

- [ ] `.gitignore` excluye `.env` (credenciales locales)

- [ ] Hacer push a GitHub:
  ```bash
  git push origin main
  ```

- [ ] URL del repositorio confirmada: 
  ```
  https://github.com/USERNAME/REPO.git
  ```

## 🔑 GitHub Access (Webhook opcional)

- [ ] Si quieres builds automáticos, crear Personal Access Token:
  - Ir a GitHub Settings → Developer settings → Personal access tokens
  - Scope: `repo`, `admin:repo_hook`
  - Guardar el token (lo necesitarás para OpenShift)

## 🌐 OpenShift Configuration

- [ ] Archivo `.openshift/configmap-secrets.yaml` editado con tus credenciales:
  ```yaml
  DB_NAME: TU_DATABASE
  DB_USER: TU_USUARIO
  DB_PASS: TU_CONTRASEÑA
  DB_HOST: TU_HOST:PUERTO
  SECRET_KEY: TU_CLAVE_GENERADA
  ```

- [ ] Archivo `.openshift/buildconfigs.yaml` apunta al repo correcto:
  ```yaml
  uri: https://github.com/TU_USUARIO/TU_REPO.git
  ```

- [ ] Routes configuradas con dominios correctos (o dejar que OpenShift auto-genere):
  ```yaml
  host: frontend-default.apps.sandbox.x8i5.p1.openshiftapps.com
  host: backend-default.apps.sandbox.x8i5.p1.openshiftapps.com
  ```

## 🚀 Despliegue

- [ ] Conectarse a OpenShift:
  ```bash
  oc login --server=https://api.sandbox.x8i5.p1.openshiftapps.com:6443
  ```

- [ ] Ejecutar script de despliegue:
  ```bash
  ./.openshift/deploy-openshift.sh default https://github.com/USERNAME/REPO.git
  ```
  O (PowerShell):
  ```powershell
  .\\.openshift\\deploy-openshift.ps1 -Namespace "default" -GitHubRepo "https://github.com/USERNAME/REPO.git"
  ```

## ✅ Post-Despliegue

- [ ] Verificar que pods están corriendo:
  ```bash
  oc get pods -n default
  # Esperar a que Status sea "Running" para todos
  ```

- [ ] Verificar BuildConfigs completaron correctamente:
  ```bash
  oc get buildconfig
  oc logs -f build/backend-1
  oc logs -f build/frontend-1
  ```

- [ ] Obtener URLs públicas:
  ```bash
  oc get routes -n default
  ```

- [ ] Probar aplicación desde navegador:
  - Frontend: `https://<frontend-route>`
  - Backend API: `https://<backend-route>/api/`

- [ ] Revisar logs de errores:
  ```bash
  oc logs -f dc/backend -n default
  oc logs -f dc/frontend -n default
  ```

- [ ] Actualizar CORS_ALLOWED_ORIGINS si es necesario:
  ```bash
  oc edit secret django-secrets
  # Agregar URLs de OpenShift
  ```

## 📊 Monitoreo Continuo

- [ ] Configurar alertas para pods
- [ ] Revisar métricas regularmente: `oc top pods`
- [ ] Configurar logs centralizados (opcional)
- [ ] Hacer backups de BD regularmente

## 🔄 Actualizaciones Futuras

Para desplegar cambios:

1. Hacer cambios localmente
2. Commit: `git commit -am "cambios"`
3. Push: `git push origin main`
4. En OpenShift, iniciar nuevo build:
   ```bash
   oc start-build backend
   oc start-build frontend
   ```
   (O esperar a que lo haga automáticamente via webhook)

---

## 📝 Notas Personales

```
Fecha de despliegue: ________________
Namespace usado: ________________
URLs generadas:
  Frontend: ________________
  Backend: ________________
Problemas encontrados:
  ________________
  ________________
```

---

**¡Listo para desplegar!** 🎉

Si algo no funciona, revisa:
1. `DEPLOYMENT_GUIDE.md` - Sección Troubleshooting
2. Logs de OpenShift: `oc logs -f <pod> -n <namespace>`
3. Documentación oficial: https://docs.openshift.com/online
