# Ambiente Local vs OpenShift - Cambios Necesarios

## Cambios Principales Realizados

### 1. Backend Dockerfile
**Antes (Desarrollo):**
```dockerfile
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Ahora (Producción):**
```dockerfile
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

- `runserver` → `gunicorn` (WSGI server adecuado para producción)
- Agregadas 4 workers para manejar concurrencia

### 2. Frontend Dockerfile
**Antes (Desarrollo):**
```dockerfile
CMD ["npm", "run", "dev", "--", "--host"]
```

**Ahora (Producción - Multi-stage):**
- Stage 1: Build de SPA con Node
- Stage 2: Servir con nginx distro slim
- Archivos estáticos con cache headers

### 3. Django Settings
**Cambios necesarios en `backend/config/settings.py`:**

```python
# PRODUCCIÓN
DEBUG = False  # Era True
ALLOWED_HOSTS = ["*"]  # O específico: ["tu-dominio.com"]

# Se mantienen las variables de BD desde env vars
# Importante: cambiar SECRET_KEY en prod
```

### 4. CORS y Seguridad
**Agregar a requirements.txt:**
```
django-cors-headers>=3.14.0
```

**Actualizar settings.py:**
```python
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "https://frontend-route.apps.sandbox.com",
    "https://backend-route.apps.sandbox.com",
]
```

### 5. Static Files
**Para Django** (agregado a Dockerfile backend):
```dockerfile
RUN python manage.py collectstatic --noinput
```

Agregar a `settings.py`:
```python
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

## Configuración de Entorno

### Variables de Entorno Requeridas

**En OpenShift (Secret):**
```yaml
DB_NAME: tu_base_datos
DB_USER: usuario_sql
DB_PASS: contraseña_sql  
DB_HOST: servidor_sql.com
SECRET_KEY: clave-secreta-segura-muy-larga
```

**En ConfigMap:**
```yaml
DEBUG: "False"
ALLOWED_HOSTS: "*"
```

## Testing Localmente Antes de Desplegar

```bash
# 1. Construir imágenes localmente
docker build -t backend:latest ./backend
docker build -t frontend:latest ./frontend

# 2. Ejecutar con docker-compose
docker-compose up

# 3. Probar:
# - Frontend: http://localhost:8088
# - Backend: http://localhost:8000/admin/

# 4. Revisar logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Port Mappings

| Servicio | Local Dev | Container | OpenShift Route |
|----------|-----------|-----------|-----------------|
| Frontend | 8088:80   | :80       | https://route   |
| Backend  | 8000:8000 | :8000     | https://route/api|
| Nginx    | Internal  | Internal  | Internal        |

## Health Checks

El frontend ahora expone un health check:
```
GET /health → 200 "healthy\n"
```

Backend usa `/admin/` como health check (cualquier endpoint que retorna 200).

## Próximos Pasos Recomendados

1. [ ] Actualizar requirements.txt con `django-cors-headers` y `gunicorn`
2. [ ] Actualizar settings.py con CORS_ALLOWED_ORIGINS
3. [ ] Cambiar SECRET_KEY a valor seguro
4. [ ] Agregar `.openshift/` a .gitignore si aún no está
5. [ ] Probar localmente con `docker-compose`
6. [ ] Crear Personal Access Token en GitHub para webhooks
7. [ ] Ejecutar script de despliegue

## Consideraciones de Seguridad

- [ ] DEBUG DEBE ser False en producción
- [ ] SECRET_KEY DEBE ser único y seguro (no en código)
- [ ] ALLOWED_HOSTS debe ser específico (no "*")
- [ ] Usar HTTPS (OpenShift lo termina automáticamente)
- [ ] Limitar CORS_ALLOWED_ORIGINS
- [ ] Auditar dependencias con `pip audit` y `npm audit`
