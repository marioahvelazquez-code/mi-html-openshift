# Generador de Fichas Hospitalarias

Sistema de generación automatizada de fichas técnicas (PowerPoint) para unidades médicas hospitalarias del IMSS. A partir de una clave presupuestal, consulta SQL Server, procesa indicadores de productividad y genera un PPTX listo para distribución.

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Flujo de ejecución](#flujo-de-ejecución)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Componentes](#componentes)
- [Stack tecnológico](#stack-tecnológico)
- [Instalación](#instalación)
- [Uso](#uso)
- [Configuración de plantillas PPTX](#configuración-de-plantillas-pptx)

---

## Arquitectura

El sistema sigue una arquitectura en capas con separación estricta de responsabilidades. Cada capa solo conoce a la siguiente y no se acopla a detalles de implementación de las demás.

```
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE ORQUESTACIÓN                    │
│                          engine.py                           │
│  Coordina el flujo end-to-end: SQL → KPIs → Fotos → PPTX     │
└───────┬─────────────────┬──────────────────┬────────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│   ACCESO A   │  │   LÓGICA DE  │  │  RENDERIZADO     │
│    DATOS     │  │   NEGOCIO    │  │     VISUAL       │
│              │  │              │  │                  │
│ repository   │  │  processor   │  │  renderer +      │
│              │  │              │  │  assets          │
│ SP + Excel   │  │  KPIs +      │  │  PPTX +          │
│              │  │  formateo    │  │  fotos           │
└──────┬───────┘  └──────────────┘  └──────────────────┘
       │
       ▼
┌──────────────────┐
│  CONFIGURACIÓN   │
│   config.py      │
│  YAML + secrets  │
└──────────────────┘
```

**Flujo de datos**: cada capa transforma sin tocar las anteriores. SQL devuelve DataFrames crudos → el processor los convierte en KPIs y listas → el renderer los inyecta en la plantilla PowerPoint.

**Contrato central**: el dataclass `FichaData` es el "contrato de datos" que viaja entre capas. Todo lo que sabe el renderer del SQL es a través de este objeto.

---

## Flujo de ejecución

Cuando se ejecuta `engine.generar_ficha(clave)`, ocurren cinco etapas:

**1. Extracción SQL** — `repository.py` ejecuta el stored procedure `sp_GenerarDataFichaHospitalaria_V2` que devuelve 12 result sets (datos generales, productividad semanal, indicadores DG, personal, comparativos, capacidad instalada, día típico, metas, acumulados, top especialidades, comparativo interanual). Cada result set se convierte en un DataFrame de pandas.

**2. Datos auxiliares** — `repository.py` lee el archivo Excel `_BD_Regionalizacion.xlsx` y extrae la población asignada a la unidad (`pda_consultorio`).

**3. Procesamiento (KPIs)** — `processor.py` toma los DataFrames crudos y calcula totales, sumas, listas formateadas, porcentajes de avance, etc. Toda la lógica de negocio vive aquí: si los criterios cambian (qué cuenta como "personal médico", cómo se formatea una lista de cartera de servicios), solo se modifica este archivo.

**4. Búsqueda de fotos** — `assets.py` localiza las fotos de la unidad en OneDrive (estructura de subcarpetas), las convierte a JPG estandarizado y las cachea localmente. Maneja formatos heterogéneos (HEIC del iPhone, PNG, etc.).

**5. Renderizado PPTX** — `renderer.py` abre la plantilla, recorre los shapes y reemplaza por nombre (`TXT_NOMBRE_UNIDAD`, `TABLA_DIA_TIPICO`, `FOTO_FACHADA`, etc.). Preserva el formato original de la plantilla a nivel XML para no romper diseños.

---

## Estructura del proyecto

```
proyecto_fichas/
├── assets/                          # Plantillas PPTX, Excel, caché de imágenes
│   ├── _BD_Regionalizacion.xlsx
│   ├── plantillas/
│   │   ├── Plantilla.pptx
│   │   └── Plantilla_HR.pptx
│   └── cache_fotos/                 # Generado en runtime
├── config/
│   ├── config.yaml                  # Rutas dinámicas (Mac/Windows)
│   └── secrets.json                 # Credenciales SQL (fuera de git)
├── src/
│   ├── core/
│   │   ├── config.py                # Carga YAML + secrets, detecta SO
│   │   ├── data_models.py           # Dataclass FichaData (contrato de datos)
│   │   ├── engine.py                # Orquestador del flujo
│   │   └── processor.py             # Cálculos de negocio (KPIs)
│   ├── data/
│   │   └── repository.py            # Acceso a SQL Server + Excel
│   └── utils/
│       ├── assets.py                # Gestión de fotos (búsqueda y conversión)
│       └── renderer.py              # Renderizado PPTX por nombre de shape
├── output_fichas/                   # Salida (generada en runtime)
├── Ejecucion.ipynb                  # Notebook de ejecución
├── SP_FICHA_HOSPITALES_V3.sql       # Stored procedure
└── requirements.txt
```

---

## Componentes

### `config.py` — Configuración

Lee `config.yaml` y `secrets.json`, detecta automáticamente si está corriendo en macOS o Windows y arma las rutas absolutas de OneDrive en función del sistema. Las credenciales SQL nunca tocan el código.

### `data_models.py` — Contrato de datos

Define `FichaData` (dataclass), la estructura central. Contiene:

- Campos identitarios: clave, nombre, estado, antigüedad, flags `es_hr` / `tiene_mf`.
- Los 11 DataFrames crudos del SP (uno por result set).
- KPIs calculados (totales de personal, productividad, día típico, metas, etc.).
- Listas formateadas (cartera de servicios, equipo, top 10 especialidades).
- Factory method `desde_sql(clave, sets)` que construye el objeto desde los result sets crudos.

### `repository.py` — Acceso a datos

Abre conexiones a SQL Server vía pyodbc (driver detectado automáticamente en Mac/Windows). Ejecuta el SP, recorre los 12 result sets con `cursor.nextset()` y devuelve un `FichaData` parcialmente poblado. También lee el Excel de regionalización y expone helpers para listar claves por estado o todas las claves activas.

### `processor.py` — Lógica de negocio

Toma un `FichaData` con DataFrames crudos y lo enriquece con métricas calculadas. Es la única capa que sabe qué significan las columnas del SP. Defensivo por diseño: si un DataFrame viene vacío o le faltan columnas, la métrica queda en cero / lista vacía sin tronar.

Reglas que viven aquí:

- Suma de personal por categoría (Médicos, Enfermeras, Otros).
- Cálculo de productividad semanal y acumulada por indicador.
- Día típico (consultas, cirugías, urgencias, partos, egresos).
- Avance vs metas anuales.
- Comparativo interanual (`+103.4%`, etc.).
- Construcción de listas legibles para PPT.
- Formateo de fecha de corte (`semana 14, 06 de Abril 2026`).

### `assets.py` — Gestión de fotos

Busca fotos en OneDrive con una estructura de subcarpetas (`fotos_fachada/_<clave>_<nombre>/`, `fotos_origen/_<clave>_<nombre>/`). Para cada unidad localiza:

- **Fachada**: primera imagen de la subcarpeta.
- **Interiores**: archivos cuyo nombre contiene `foto_1`, `foto_2`, `foto_3`, `foto_4`.

Convierte cualquier formato (incluido HEIC del iPhone) a JPG estandarizado y cachea el resultado en disco para evitar reprocesar.

### `renderer.py` — Renderizado PPTX

Genera el archivo `.pptx` final. Estrategia clave: **lookup por nombre de shape**, no por contenido de texto.

La plantilla tiene shapes con nombres convencionales:

| Tipo | Patrón | Ejemplos |
|------|--------|----------|
| Texto | `TXT_*` | `TXT_NOMBRE_UNIDAD`, `TXT_ANTIGUEDAD` |
| Listas | `TXT_LISTA_*` | `TXT_LISTA_CAP_INSTALADA` |
| Tablas | `TABLA_*` | `TABLA_DIA_TIPICO`, `TABLA_PROD_HR` |
| Fotos | `FOTO_*` | `FOTO_FACHADA`, `FOTO_1`...`FOTO_4` |

Para cada shape: busca su nombre en un diccionario de datos. Si lo encuentra, sobrescribe el contenido. Si el dato viene vacío, deja el placeholder original intacto (`XXX`, `AA`) para que sea visible que falta.

**Preservación de formato**: opera a nivel XML clonando los nodos `rPr` y `endParaRPr` de la plantilla. Esto asegura que fuente, color, tamaño, bullets y sangría se mantengan exactamente como los configuró la plantilla, incluso en celdas de tabla vacías donde no hay run de texto del cual copiar.

### `engine.py` — Orquestador

Une todo. Expone dos APIs:

- `generar_ficha(clave) → str` para una sola ficha (lanza excepción si algo falla).
- `generar_batch(claves, n_workers=N) → ResumenBatch` para procesamiento masivo. Maneja excepciones por clave y devuelve estadísticas.

Para el modo masivo paralelizado usa `ThreadPoolExecutor`. Cada thread crea su propio `DataRepository` (almacenado en `threading.local`) porque las conexiones pyodbc no son seguras compartidas entre hilos.

---

## Stack tecnológico

| Componente | Librería | Para qué |
|------------|----------|----------|
| Acceso SQL | `pyodbc` | Conexión a SQL Server vía ODBC Driver 17 |
| Manipulación de datos | `pandas` | DataFrames de result sets, formateo, agregaciones |
| Lectura Excel | `openpyxl` (vía pandas) | Excel de regionalización |
| Generación PPTX | `python-pptx` | API de alto nivel para PowerPoint |
| Edición XML directa | `lxml` | Clonado de nodos `rPr` / `endParaRPr` para preservar formato |
| Procesamiento de imágenes | `Pillow` | Conversión de formatos, redimensionado |
| Soporte HEIC | `pillow-heif` | Lectura de fotos del iPhone |
| Configuración | `PyYAML` | Lectura de `config.yaml` |
| Concurrencia | `concurrent.futures` (stdlib) | `ThreadPoolExecutor` para modo masivo |

---

## Instalación

**Requisitos previos:**

- Python 3.11 o superior
- ODBC Driver 17 for SQL Server
  - macOS: `brew install msodbcsql17`
  - Windows: instalador desde el sitio de Microsoft

**Pasos:**

```bash
# 1. Clonar el repo
git clone <url> proyecto_fichas
cd proyecto_fichas

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar credenciales
cp config/secrets.example.json config/secrets.json
# editar config/secrets.json con server, port, user, password

# 5. Verificar config.yaml
# revisar que las rutas de OneDrive coincidan con tu sistema
```

---

## Uso

### Una sola ficha (notebook)

```python
from src.core.engine import FichaEngine

engine = FichaEngine()
ruta = engine.generar_ficha('010101012151')
print(f'Generado: {ruta}')
```

### Todas las fichas de un estado

```python
claves = engine.repo.obtener_unidades_batch(id_estado='09')
resumen = engine.generar_batch(claves, n_workers=1)
resumen.imprimir()
```

### Todas las fichas a nivel nacional (paralelo)

```python
claves = engine.repo.obtener_todas_las_claves()
resumen = engine.generar_batch(claves, n_workers=4, verbose_cada=10)
resumen.imprimir()

# Acceso a resultados:
# resumen.ok       → [(clave, ruta), ...]
# resumen.errores  → [(clave, mensaje_error), ...]
# resumen.tiempo_total
# resumen.tasa_exito
```

El número de `n_workers` controla las conexiones SQL simultáneas. Empezar en 4 y subir según aguante el servidor.

---

## Configuración de plantillas PPTX

Para que un dato aparezca en el PPT, debe existir un shape en la plantilla con el nombre exacto que el renderer espera.

**Cómo nombrar un shape en PowerPoint:**

1. Seleccionar el shape (cuadro de texto, tabla, imagen, etc.).
2. Panel de selección (Inicio → Organizar → Panel de selección, o `Alt+F10` en Windows).
3. Doble clic sobre el nombre del shape y reescribir.

**Nombres esperados por el renderer:**

| Shape | Datos |
|-------|-------|
| `TXT_NOMBRE_UNIDAD` | Nombre del hospital |
| `TXT_ESTADO` | Entidad federativa |
| `TXT_ANTIGUEDAD` | Años de antigüedad |
| `TXT_ANIO_INICIO` | Año de inicio de operación |
| `TXT_POBLACION` | Población asignada |
| `TXT_CAMAS` | Total de camas |
| `TXT_ESPECIALIDADES` | Total de especialidades (texto: "N especialidades") |
| `TXT_PERSONAL_TOTAL` | Total de personal |
| `TXT_TOTAL_MED` | Total de médicos |
| `TXT_TOTAL_ENF` | Total de enfermeras |
| `TXT_TOTAL_OTROS` | Total de otras categorías |
| `TXT_DIA_TIPICO_TOTAL` | Total atenciones día típico |
| `TXT_PROD_TOTAL` | Total productividad semanal |
| `TXT_DATE_PROD` | Fecha de la semana de corte |
| `TXT_LISTA_CAP_INSTALADA` | Lista de cartera de servicios |
| `TXT_LISTA_EQUIPO` | Lista de equipo relevante |
| `TXT_LISTA_PERSONAL` | Top 10 especialidades |
| `TABLA_DIA_TIPICO` | Tabla 3×4 de día típico |
| `TABLA_PRODUCTIVIDAD` | Tabla 3×4 de productividad acumulada |
| `TABLA_PRODUCTIVIDAD_AÑOS` | Tabla 3×6 de comparativo con metas |
| `TABLA_PROD_HR` | Tabla 3×4 de comparativo HR (solo plantilla HR) |
| `FOTO_FACHADA` | Foto de fachada |
| `FOTO_1` ... `FOTO_4` | Fotos interiores |

Las plantillas pueden tener cualquier diseño visual: el renderer no asume posiciones, solo nombres. Cambiar el color, fuente, tamaño o ubicación de un shape no rompe nada mientras se mantenga el nombre.

---

## Notas técnicas

- **El SP es la fuente de verdad para los datos.** Cualquier cambio en cómo se calculan productividad, comparativos o acumulados se hace en `SP_FICHA_HOSPITALES_V3.sql`, no en Python.
- **El processor es la fuente de verdad para el formato.** Cómo se ve un porcentaje, cómo se construye la lista de cartera de servicios, qué se considera "Personal Otros" — todo vive en `processor.py`.
- **El renderer no tiene reglas de negocio.** Solo sabe "este dato va en este shape". Si TXT_PERSONAL_TOTAL aparece en N diapositivas, se llena en todas con el mismo valor sin lógica adicional.
- **El cache de fotos es persistente entre corridas.** Si una foto cambia en OneDrive, hay que borrar `assets/cache_fotos/` para forzar reproceso.