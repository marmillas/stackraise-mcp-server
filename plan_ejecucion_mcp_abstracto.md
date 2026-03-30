# Plan de ejecución: MCP abstracto reusable para backend Python

## 1. Objetivo

Implementar un paquete Python reusable llamado provisionalmente `abstract-backend-mcp` que permita:

- servir como **MCP local**
- exponer tools reutilizables para backend Python
- soportar integración con:
  - FastAPI
  - MongoDB
  - Stackraise
  - Poetry
  - Pydantic
- incluir una arquitectura preparada para fases/agentes:
  - `Plan`
  - `Build`
  - `Audit`
- permitir **configuración sencilla por proyecto**
- soportar **operaciones readonly y escrituras controladas**
- ser fácil de instalar y poner en marcha en un repo nuevo

---

## 2. Resultado esperado

Al finalizar, debe existir un repositorio/paquete funcional con:

1. **paquete Python instalable por Poetry**
2. **servidor MCP arrancable localmente**
3. **tools base operativas**
4. **adapters para FastAPI, MongoDB y Stackraise**
5. **configuración por `.env` y YAML**
6. **comando CLI de bootstrap**
7. **plantillas para integración con OpenCode**
8. **documentación mínima de instalación y uso**
9. **tests básicos**
10. **mecanismo de seguridad para escrituras controladas**

---

## 3. Restricciones y decisiones de arquitectura

### 3.1 Restricciones
- Python `>=3.12`
- gestor de dependencias: `Poetry`
- integración primaria con `Stackraise`
- si Stackraise no cubre una necesidad concreta, Mongo puede usar fallback a `pymongo`
- el MCP será **local**, no remoto
- el MCP debe poder usarse desde:
  - OpenCode
  - agente de terminal tipo Codex/OpenCode CLI
- no debe depender de un proyecto concreto

### 3.2 Decisiones de arquitectura
- separar en:
  - `core`
  - `adapters`
  - `tools`
  - `bootstrap`
  - `templates`
- usar **Pydantic Settings** para configuración
- usar **adapters** para desacoplar tools de implementaciones concretas
- usar **registro dinámico de tools**
- usar **Stackraise como integración preferente**
- usar **escritura controlada** con validaciones explícitas
- dejar desde el inicio preparada la semántica para `Plan`, `Build`, `Audit`, aunque el “agente” en sí lo consumirá OpenCode

---

## 4. Alcance funcional de la v1

### Incluido en v1
- servidor MCP operativo
- configuración base
- tools de salud/configuración
- tools de tests/calidad
- tools FastAPI básicas
- tools MongoDB básicas
- tools Stackraise básicas
- operaciones Mongo readonly
- operaciones Mongo write controladas
- CLI `init` y `serve`
- plantillas `AGENTS.md` y `opencode.jsonc`

### No incluido en v1
- servidor HTTP compartido
- operaciones masivas destructivas
- autocorrección automática de código
- trazado avanzado de dependencias entre módulos
- análisis de cobertura de tests por endpoint
- auditoría de seguridad profunda
- introspección avanzada de RPA salvo detección y listados simples

---

## 5. Estructura objetivo del repositorio

```text
abstract-backend-mcp/
├─ pyproject.toml
├─ README.md
├─ .env.example
├─ mcp.project.example.yaml
├─ AGENTS.md
├─ src/
│  └─ abstract_backend_mcp/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ server.py
│     │  ├─ settings.py
│     │  ├─ registry.py
│     │  ├─ errors.py
│     │  ├─ permissions.py
│     │  └─ logging.py
│     ├─ adapters/
│     │  ├─ __init__.py
│     │  ├─ fastapi_adapter.py
│     │  ├─ mongodb_adapter.py
│     │  └─ stackraise_adapter.py
│     ├─ tools/
│     │  ├─ __init__.py
│     │  ├─ health.py
│     │  ├─ poetry_tools.py
│     │  ├─ test_tools.py
│     │  ├─ quality_tools.py
│     │  ├─ fastapi_tools.py
│     │  ├─ mongodb_tools.py
│     │  └─ stackraise_tools.py
│     ├─ bootstrap/
│     │  ├─ __init__.py
│     │  ├─ init_project.py
│     │  └─ detect_project.py
│     └─ templates/
│        ├─ AGENTS.md.j2
│        ├─ opencode.jsonc.j2
│        ├─ mcp.project.yaml.j2
│        └─ env.j2
└─ tests/
   ├─ test_settings.py
   ├─ test_permissions.py
   ├─ test_registry.py
   ├─ test_health_tools.py
   ├─ test_fastapi_adapter.py
   └─ test_mongodb_adapter.py
```

---

## 6. Fases de ejecución

## Fase 0. Preparación

### Objetivo
Dejar listo el esqueleto del proyecto y las decisiones base.

### Tareas
1. Crear repositorio del paquete.
2. Inicializar Poetry.
3. Configurar estructura `src/`.
4. Añadir dependencias iniciales.
5. Añadir linters y tooling mínimo.
6. Crear README inicial.
7. Crear `.gitignore`.
8. Crear carpeta `tests/`.

### Dependencias mínimas
- `pydantic`
- `pydantic-settings`
- `mcp`
- `pymongo`
- `pyyaml`
- `jinja2`
- `fastapi` como opcional o de desarrollo para tests
- `pytest`
- `ruff`
- `pyright`

### Entregables
- repo inicial
- `pyproject.toml`
- estructura de carpetas
- tooling mínimo funcionando

### Criterio de aceptación
- `poetry install` funciona
- `poetry run pytest` ejecuta aunque aún haya pocos tests
- `poetry run ruff check .` pasa o falla solo por código aún no implementado

---

## Fase 1. Núcleo de configuración y errores

### Objetivo
Tener una base sólida para configuración, permisos y errores comunes.

### Archivos a implementar
- `core/settings.py`
- `core/errors.py`
- `core/permissions.py`
- `core/logging.py`

### Tareas detalladas

#### 1. `core/errors.py`
Crear excepciones específicas:
- `MCPConfigurationError`
- `ToolExecutionError`
- `UnsafeOperationError`
- `DependencyNotAvailableError`
- `ProjectDetectionError`

#### 2. `core/settings.py`
Implementar `MCPSettings` con:
- lectura desde `.env`
- posibilidad de sobreescribir con YAML
- valores por defecto razonables
- flags de habilitación de tools/plugins
- configuración de write controls

Campos recomendados:
- `project_name`
- `environment`
- `fastapi_app_path`
- `mongodb_uri`
- `mongodb_db_name`
- `stackraise_enabled`
- `stackraise_package_name`
- `enable_fastapi_tools`
- `enable_mongodb_tools`
- `enable_stackraise_tools`
- `enable_test_tools`
- `enable_quality_tools`
- `allow_write_operations`
- `require_write_confirmation`
- `allowed_write_collections`

#### 3. `core/permissions.py`
Implementar helpers:
- `assert_write_allowed`
- `assert_collection_allowed`
- `assert_environment_safe`
- `normalize_write_request`

Definir reglas:
- si `allow_write_operations=False`, bloquear
- si colección no permitida, bloquear
- si requiere confirmación y no se pasó `confirmed=True`, bloquear

#### 4. `core/logging.py`
Crear logger del MCP.
Regla:
- usar logger estándar por defecto
- si Stackraise logging está disponible, permitir integrarlo
- nunca emitir logs del protocolo MCP por stdout arbitrario

### Entregables
- módulo de settings usable
- sistema de permisos reusable
- errores consistentes
- logger base

### Criterios de aceptación
- tests unitarios de settings y permissions
- configuración carga desde `.env`
- permisos bloquean escrituras no autorizadas

---

## Fase 2. Registry y arranque del servidor

### Objetivo
Poder arrancar un servidor MCP mínimo y registrar tools dinámicamente.

### Archivos
- `core/registry.py`
- `core/server.py`
- `main.py`

### Tareas detalladas

#### 1. `core/registry.py`
Implementar un `ToolRegistry` o función de registro que:
- reciba settings
- reciba instancia del servidor MCP
- cargue tools por grupos según flags
- pueda registrar:
  - health
  - quality
  - tests
  - fastapi
  - mongodb
  - stackraise

#### 2. `core/server.py`
Implementar:
- factory del servidor MCP
- carga de settings
- inicialización de adapters
- registro de tools
- función `create_server()`

#### 3. `main.py`
Implementar CLI mínima con subcomandos:
- `serve`
- `init`
- `doctor` opcional

### Entregables
- servidor arrancable
- registro dinámico funcionando
- CLI mínima usable

### Criterios de aceptación
- `poetry run abstract-mcp serve` arranca sin error
- `ping` o tool equivalente responde
- el servidor registra tools habilitadas

---

## Fase 3. Bootstrap y detección de proyecto

### Objetivo
Hacer que el MCP sea fácil de configurar en nuevos proyectos.

### Archivos
- `bootstrap/init_project.py`
- `bootstrap/detect_project.py`
- `templates/*`

### Tareas detalladas

#### 1. `detect_project.py`
Implementar detección heurística de:
- proyecto Poetry
- presencia de FastAPI
- path probable de app (`app.main:app`, `main:app`, etc.)
- uso de Stackraise
- uso de MongoDB

#### 2. `init_project.py`
Implementar comando `init` que:
- cree `.env.example`
- cree `mcp.project.yaml`
- cree `AGENTS.md`
- cree `opencode.jsonc`
- no sobrescriba sin confirmación
- permita modo dry-run

#### 3. Plantillas Jinja
Crear:
- `AGENTS.md.j2`
- `opencode.jsonc.j2`
- `mcp.project.yaml.j2`
- `env.j2`

### Entregables
- bootstrap automático
- plantillas de integración
- detección básica del proyecto

### Criterios de aceptación
- `poetry run abstract-mcp init` genera ficheros
- las plantillas se rellenan con valores válidos
- funciona en un repo FastAPI/Poetry típico

---

## Fase 4. Adapters base

### Objetivo
Aislar la lógica de acceso a FastAPI, Mongo y Stackraise.

### Archivos
- `adapters/fastapi_adapter.py`
- `adapters/mongodb_adapter.py`
- `adapters/stackraise_adapter.py`

### 4.1 `FastAPIAdapter`

#### Responsabilidades
- importar app FastAPI desde `fastapi_app_path`
- listar rutas
- exponer resumen OpenAPI
- buscar rutas por patrón
- devolver tags y métodos

#### Métodos recomendados
- `load_app()`
- `list_routes()`
- `find_routes(path_fragment)`
- `get_openapi_summary()`

#### Criterio de aceptación
- funciona con una app FastAPI de ejemplo
- no rompe si el import path es inválido: devuelve error controlado

### 4.2 `MongoDBAdapter`

#### Responsabilidades
- intentar resolver cliente Mongo vía Stackraise si aplica
- fallback a `pymongo`
- exponer operaciones:
  - `list_collections`
  - `sample_documents`
  - `count_documents`
  - `show_indexes`
  - `insert_one`
  - `update_one`
  - `delete_one`

#### Reglas
- lecturas permitidas según configuración general
- escrituras delegan en `core.permissions`

#### Criterio de aceptación
- puede listar colecciones y muestrear documentos
- bloquea escritura si no está permitida

### 4.3 `StackraiseAdapter`

#### Responsabilidades
- detectar módulos disponibles:
  - `stackraise.model`
  - `stackraise.db`
  - `stackraise.logging`
  - `stackraise.di`
- exponer metadatos útiles del framework
- si es posible, resolver:
  - cliente DB
  - logger
  - bindings DI
  - recursos CRUD

#### Métodos recomendados
- `detect_modules()`
- `is_available()`
- `get_db_metadata()`
- `get_logging_metadata()`
- `get_di_metadata()`
- `list_crud_resources()` si se puede inferir

#### Nota importante
No asumir APIs internas no confirmadas. Diseñar el adapter para:
- detectar de forma segura
- degradar con elegancia si algo no existe
- devolver “no soportado” en vez de romper

### Criterio de aceptación
- detecta presencia de Stackraise
- no rompe cuando Stackraise no está instalado
- puede integrarse opcionalmente con DB/logging

---

## Fase 5. Tools de salud y sistema

### Objetivo
Tener tools básicas para diagnosticar el MCP y el entorno.

### Archivo
- `tools/health.py`

### Tools a implementar
- `ping()`
- `show_runtime_config()`
- `list_enabled_tools()`
- `check_project_health()`

### Comportamiento esperado
- `ping`: devuelve estado simple
- `show_runtime_config`: devuelve configuración efectiva sanitizada
- `list_enabled_tools`: enumera grupos activos
- `check_project_health`: valida presencia de FastAPI, Stackraise, Poetry, etc.

### Criterio de aceptación
- usable desde servidor MCP
- salida consistente y serializable

---

## Fase 6. Tools de calidad y tests

### Objetivo
Exponer capacidades estándar de validación del proyecto.

### Archivos
- `tools/poetry_tools.py`
- `tools/test_tools.py`
- `tools/quality_tools.py`

### Tareas detalladas

#### 1. Helpers de ejecución de comandos
Crear helper interno seguro para ejecutar comandos.
Requisitos:
- timeout configurable
- captura de stdout/stderr
- salida serializable
- códigos de retorno claros

#### 2. `test_tools.py`
Tools:
- `run_tests_all()`
- `run_tests_file(path)`
- `run_tests_keyword(keyword)`
- `run_tests_nodeid(nodeid)`

Todas deben usar Poetry:
- `poetry run pytest ...`

#### 3. `quality_tools.py`
Tools:
- `run_ruff_check()`
- `run_ruff_format_check()`
- `run_pyright()`
- `run_quality_suite()`

#### 4. `poetry_tools.py`
Tools mínimas:
- `poetry_install()`
- `poetry_show()`

Evitar en v1 una tool abierta tipo “ejecuta cualquier comando”.

### Criterio de aceptación
- desde MCP se pueden lanzar tests
- desde MCP se puede correr ruff/pyright
- las salidas son legibles por otro agente

---

## Fase 7. Tools de FastAPI

### Objetivo
Dar capacidades de introspección útiles para análisis, build y auditoría.

### Archivo
- `tools/fastapi_tools.py`

### Tools a implementar
- `list_routes()`
- `find_route(path_fragment)`
- `show_openapi_summary()`
- `list_routes_by_tag(tag)` opcional si es simple

### Formato de salida recomendado
Cada ruta debería incluir:
- path
- methods
- name
- tags si existen

### Criterio de aceptación
- con una app de ejemplo, lista rutas correctamente
- puede filtrar por fragmento de path
- no falla de forma abrupta si OpenAPI no está disponible

---

## Fase 8. Tools de MongoDB

### Objetivo
Dar herramientas de inspección y escritura controlada.

### Archivo
- `tools/mongodb_tools.py`

### Tools readonly
- `list_collections()`
- `sample_documents(collection, limit=5)`
- `count_documents(collection, filter={})`
- `show_indexes(collection)`

### Tools de escritura controlada
- `insert_one_controlled(collection, document, confirmed=False)`
- `update_one_controlled(collection, filter, update, confirmed=False)`
- `delete_one_controlled(collection, filter, confirmed=False)`

### Reglas
- todas las tools de escritura deben:
  - validar permisos
  - validar colección permitida
  - soportar `confirmed`
  - registrar intención/resultado

### Criterio de aceptación
- en entorno de prueba, operaciones readonly funcionan
- operaciones write fallan si no hay permiso
- operaciones write pasan si:
  - entorno permitido
  - colección permitida
  - confirmación explícita
  - settings lo permiten

---

## Fase 9. Tools de Stackraise

### Objetivo
Exponer el valor añadido del framework interno.

### Archivo
- `tools/stackraise_tools.py`

### Tools v1
- `detect_stackraise()`
- `show_stackraise_modules()`
- `show_stackraise_db_metadata()`
- `show_stackraise_logging_metadata()`
- `show_stackraise_di_metadata()`
- `list_stackraise_resources()` solo si se puede obtener de forma fiable

### Regla
No inventar introspección que no esté soportada. Implementar detección progresiva:
- primero módulos
- luego metadatos accesibles
- luego recursos avanzados si el framework los expone claramente

### Criterio de aceptación
- funciona sin Stackraise instalado devolviendo estado controlado
- con Stackraise disponible, devuelve información útil

---

## Fase 10. Integración con OpenCode

### Objetivo
Dejar el paquete listo para ser consumido como MCP local.

### Archivos generados por bootstrap
- `AGENTS.md`
- `opencode.jsonc`

### Requisitos del `opencode.jsonc`
- agente `plan`
- agente `build`
- agente `audit`
- conexión al MCP local usando:
  - `poetry run abstract-mcp serve`

### Comportamiento esperado de agentes

#### Plan
- sin edición
- sin escrituras Mongo
- lectura, inspección y tests permitidos

#### Build
- edición permitida bajo confirmación
- tools de calidad y tests
- escrituras controladas posibles si settings lo permiten

#### Audit
- sin edición
- foco en revisión, calidad, configuración, riesgos

### Criterio de aceptación
- bootstrap genera un `opencode.jsonc` válido
- el proyecto puede arrancar OpenCode con el MCP local

---

## Fase 11. Tests

### Objetivo
Validar componentes críticos.

### Cobertura mínima recomendada

#### Unit tests
- settings
- permissions
- registry
- helpers de ejecución de comandos
- adapters en condiciones normales y de error

#### Integration-like tests
- FastAPI adapter con app demo
- Mongo adapter con mock o entorno de prueba
- tools health
- tools readonly

### Importante
Para MongoDB:
- preferible usar mock o contenedor local en tests de integración
- no depender de una base real no controlada

### Criterio de aceptación
- tests de settings y permissions obligatorios
- al menos un test por grupo de tools
- `poetry run pytest` pasa

---

## Fase 12. Documentación

### Objetivo
Permitir a otro desarrollador instalarlo y usarlo.

### Archivos
- `README.md`
- ejemplos de configuración
- sección de seguridad

### Contenido mínimo del README
1. qué es el paquete
2. instalación
3. cómo arrancar
4. cómo hacer bootstrap en un proyecto
5. configuración `.env`
6. configuración YAML
7. lista de tools
8. política de write operations
9. ejemplo de `opencode.jsonc`
10. troubleshooting

### Criterio de aceptación
- alguien ajeno puede instalarlo siguiendo el README
- el README explica claramente los límites de la v1

---

## 7. Orden de implementación recomendado

Este es el orden que debe seguir el otro agente:

1. inicializar repo y Poetry
2. crear `pyproject.toml`
3. crear estructura `src/`
4. implementar `errors.py`
5. implementar `settings.py`
6. implementar `permissions.py`
7. implementar `logging.py`
8. implementar `registry.py`
9. implementar `server.py`
10. implementar `main.py`
11. implementar `health.py`
12. implementar helpers de subprocess
13. implementar `test_tools.py`
14. implementar `quality_tools.py`
15. implementar `fastapi_adapter.py`
16. implementar `fastapi_tools.py`
17. implementar `stackraise_adapter.py`
18. implementar `mongodb_adapter.py`
19. implementar `mongodb_tools.py`
20. implementar `stackraise_tools.py`
21. implementar `detect_project.py`
22. implementar `init_project.py`
23. crear templates
24. añadir tests
25. documentar
26. probar integración local completa

---

## 8. Dependencias técnicas concretas

### Requeridas
- `python >= 3.12`
- `poetry`
- `mcp`
- `pydantic`
- `pydantic-settings`
- `pyyaml`
- `pymongo`
- `jinja2`

### Desarrollo
- `pytest`
- `ruff`
- `pyright`
- `fastapi`
- `httpx` si hace falta en tests

### Opcionales
- `stackraise`
- `motor` no necesario si ya vais con Stackraise + pymongo

---

## 9. Reglas de implementación para el otro agente

Estas reglas son importantes.

### Regla 1
No acoplar tools directamente a imports del proyecto final.  
Usar adapters.

### Regla 2
No asumir detalles internos de Stackraise no confirmados.  
Implementar detección defensiva.

### Regla 3
Toda operación de escritura debe pasar por `core.permissions`.

### Regla 4
No exponer en v1 una tool abierta para ejecutar shell arbitrario.

### Regla 5
Toda salida de tool debe ser:
- serializable
- consistente
- razonablemente breve
- apta para ser leída por otro agente

### Regla 6
Los errores deben ser controlados y comprensibles.

### Regla 7
La configuración debe poder venir de:
- `.env`
- YAML
- defaults internos

### Regla 8
Si Stackraise está disponible, usarlo prioritariamente frente a `pymongo`.

---

## 10. Definición de done

El proyecto se considera terminado cuando:

1. `poetry install` funciona
2. `poetry run abstract-mcp serve` arranca
3. el MCP expone tools básicas
4. `poetry run abstract-mcp init` genera configuración
5. FastAPI adapter funciona con app demo
6. Mongo adapter funciona en readonly
7. write controls están implementados
8. Stackraise detection funciona
9. existe `opencode.jsonc` de ejemplo
10. existe `AGENTS.md` de ejemplo
11. `poetry run pytest` pasa
12. `poetry run ruff check .` pasa
13. el README explica instalación y uso

---

## 11. Riesgos y mitigaciones

### Riesgo 1: Stackraise no expone APIs introspectables claras
**Mitigación**  
Diseñar `stackraise_adapter` como detección progresiva y fallback elegante.

### Riesgo 2: demasiada ambición en v1
**Mitigación**  
Limitar v1 a tools de alto valor y dejar introspección avanzada para v2.

### Riesgo 3: escrituras peligrosas en Mongo
**Mitigación**  
Implementar validación estricta:
- entornos permitidos
- colecciones permitidas
- confirmación obligatoria
- logging de operación

### Riesgo 4: bootstrap demasiado acoplado a una estructura concreta
**Mitigación**  
Hacer detección heurística con defaults editables, no hardcodeados.

### Riesgo 5: salidas de tools demasiado verbosas
**Mitigación**  
Normalizar respuestas y truncar stdout/stderr si hace falta.

---

## 12. Backlog posterior a la v1

Dejar anotado, pero no implementar en esta fase:

- soporte HTTP/streamable transport
- auditoría por endpoint sin tests
- diff de OpenAPI entre versiones
- introspección avanzada de CRUD autogenerados por Stackraise
- herramientas de RPA
- soporte multi-entorno
- integración con logs estructurados de Stackraise
- comparación de configuración efectiva entre proyectos

---

## 13. Prompt operativo para otro agente

Puedes pasarle esto tal cual:

> Implementa un paquete Python llamado `abstract-backend-mcp` con soporte para Python 3.12+, Poetry, FastAPI, MongoDB y Stackraise.  
> La arquitectura debe separarse en `core`, `adapters`, `tools`, `bootstrap` y `templates`.  
> Debe haber configuración con Pydantic Settings, registro dinámico de tools, adapters para FastAPI/MongoDB/Stackraise, tools de health, tests, quality, FastAPI, MongoDB y Stackraise.  
> Las escrituras Mongo deben ser controladas mediante una capa de permisos central.  
> Debe existir un CLI con `serve` e `init`.  
> Debe generarse integración base con OpenCode usando agentes `plan`, `build` y `audit`.  
> Prioriza una v1 pequeña pero sólida.  
> No asumas APIs internas de Stackraise que no puedas detectar de forma segura.  
> Toda salida debe ser serializable y usable por otro agente.  
> Añade tests mínimos y documentación suficiente para instalarlo y usarlo.

---

## 14. Mi recomendación final de ejecución

Si lo va a implementar otro agente, yo dividiría su trabajo en 3 bloques:

### Bloque A
Core + server + CLI + bootstrap

### Bloque B
Adapters + tools

### Bloque C
Tests + documentación + integración OpenCode

Ese reparto suele evitar que mezcle infraestructura con lógica de dominio demasiado pronto.
