# Plan operativo ampliado: MCP abstracto reusable para backend Python + contexto Stackraise

Este documento conserva el plan original y lo amplia con una capa especifica para dar a MCP contexto completo del stack tecnologico de Stackraise.

---

## 1. Objetivo

Implementar un paquete Python reusable llamado provisionalmente `abstract-backend-mcp` que permita:

- servir como MCP local
- exponer tools reutilizables para backend Python
- soportar integracion con:
  - FastAPI
  - MongoDB
  - Stackraise
  - Poetry
  - Pydantic
- incluir una arquitectura preparada para fases/agentes:
  - Plan
  - Build
  - Audit
- permitir configuracion sencilla por proyecto
- soportar operaciones readonly y escrituras controladas
- ser facil de instalar y poner en marcha en un repo nuevo

Adicionalmente (ampliacion):

- construir una capa de contexto estructurado para Stackraise con salida serializable y estable
- capturar contexto de dominio, API, auth, workflows y contratos frontend-backend
- operar en modo defensivo (degradacion elegante) cuando no sea posible introspeccion runtime

---

## 2. Resultado esperado

Al finalizar, debe existir un repositorio/paquete funcional con:

1. paquete Python instalable por Poetry
2. servidor MCP arrancable localmente
3. tools base operativas
4. adapters para FastAPI, MongoDB y Stackraise
5. configuracion por `.env` y YAML
6. comando CLI de bootstrap
7. plantillas para integracion con OpenCode
8. documentacion minima de instalacion y uso
9. tests basicos
10. mecanismo de seguridad para escrituras controladas

Ampliacion de resultado esperado:

11. contrato de contexto Stackraise (`stackraise_context_snapshot`) estable
12. extraccion hibrida (`static`, `runtime`, `hybrid`) con fallback seguro
13. sanitizacion/redaccion de secretos en toda salida de tools
14. warnings explicitos de contexto incompleto (sin romper ejecucion)

---

## 3. Restricciones y decisiones de arquitectura

### 3.1 Restricciones

- Python `>=3.12`
- gestor de dependencias: `Poetry`
- integracion primaria con `Stackraise`
- si Stackraise no cubre una necesidad concreta, Mongo puede usar fallback a `pymongo`
- el MCP sera local, no remoto
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
- usar Pydantic Settings para configuracion
- usar adapters para desacoplar tools de implementaciones concretas
- usar registro dinamico de tools
- usar Stackraise como integracion preferente
- usar escritura controlada con validaciones explicitas
- dejar desde el inicio preparada la semantica para `Plan`, `Build`, `Audit`, aunque el agente lo consumira OpenCode

Ampliacion de decisiones:

- agregar modulo `context/` para extraccion y normalizacion de contexto
- definir un schema de salida unico para contexto (`project`, `stackraise`, `security`, `extraction`)
- extraer contexto con estrategia hibrida:
  - `static`: analisis de codigo sin importar app
  - `runtime`: introspeccion real de app/modulos
  - `hybrid`: runtime + fallback static

---

## 4. Alcance funcional de la v1

### Incluido en v1

- servidor MCP operativo
- configuracion base
- tools de salud/configuracion
- tools de tests/calidad
- tools FastAPI basicas
- tools MongoDB basicas
- tools Stackraise basicas
- operaciones Mongo readonly
- operaciones Mongo write controladas
- CLI `init` y `serve`
- plantillas `AGENTS.md` y `opencode.jsonc`

Ampliacion incluida en v1:

- contexto Stackraise:
  - deteccion de modulos del framework (`model`, `db`, `ctrl`, `auth`, `di`, `logging`, `ai`, `templating`, `io`)
  - inventario de documentos `db.Document`, referencias y colecciones
  - mapeo de recursos CRUD (incluyendo rutas generadas por `ctrl.Crud`)
  - resumen de rutas FastAPI y tags
  - mapa de scopes/guards de auth
  - deteccion de workflows (RPA, email watcher, generacion documental)
  - deteccion de contratos frontend (`@stackraise/core`, `@stackraise/auth`, modelos demo)

### No incluido en v1

- servidor HTTP compartido
- operaciones masivas destructivas
- autocorreccion automatica de codigo
- trazado avanzado de dependencias entre modulos
- analisis de cobertura de tests por endpoint
- auditoria de seguridad profunda
- introspeccion avanzada de RPA salvo deteccion y listados simples

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
│     ├─ context/
│     │  ├─ __init__.py
│     │  ├─ schemas.py
│     │  ├─ extractors_static.py
│     │  ├─ extractors_runtime.py
│     │  ├─ normalizer.py
│     │  └─ redaction.py
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
   ├─ test_mongodb_adapter.py
   ├─ test_stackraise_context_static.py
   └─ test_stackraise_context_hybrid.py
```

---

## 6. Fases de ejecucion

## Fase 0. Preparacion

### Objetivo

Dejar listo el esqueleto del proyecto y las decisiones base.

### Tareas

1. Crear repositorio del paquete.
2. Inicializar Poetry.
3. Configurar estructura `src/`.
4. Anadir dependencias iniciales.
5. Anadir linters y tooling minimo.
6. Crear README inicial.
7. Crear `.gitignore`.
8. Crear carpeta `tests/`.

### Dependencias minimas

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
- tooling minimo funcionando

### Criterio de aceptacion

- `poetry install` funciona
- `poetry run pytest` ejecuta aunque aun haya pocos tests
- `poetry run ruff check .` pasa o falla solo por codigo aun no implementado

---

## Fase 1. Nucleo de configuracion y errores

### Objetivo

Tener una base solida para configuracion, permisos y errores comunes.

### Archivos a implementar

- `core/settings.py`
- `core/errors.py`
- `core/permissions.py`
- `core/logging.py`

### Tareas detalladas

#### 1. `core/errors.py`

Crear excepciones especificas:

- `MCPConfigurationError`
- `ToolExecutionError`
- `UnsafeOperationError`
- `DependencyNotAvailableError`
- `ProjectDetectionError`

Ampliacion:

- `ContextExtractionError`
- `ContextRedactionError`

#### 2. `core/settings.py`

Implementar `MCPSettings` con:

- lectura desde `.env`
- posibilidad de sobreescribir con YAML
- valores por defecto razonables
- flags de habilitacion de tools/plugins
- configuracion de write controls

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

Campos ampliados para contexto:

- `stackraise_context_mode` (`static|runtime|hybrid`)
- `include_frontend_context`
- `redact_sensitive_fields`
- `stackraise_domain_globs`
- `stackraise_api_globs`
- `max_output_items`

#### 3. `core/permissions.py`

Implementar helpers:

- `assert_write_allowed`
- `assert_collection_allowed`
- `assert_environment_safe`
- `normalize_write_request`

Definir reglas:

- si `allow_write_operations=False`, bloquear
- si coleccion no permitida, bloquear
- si requiere confirmacion y no se paso `confirmed=True`, bloquear

#### 4. `core/logging.py`

Crear logger del MCP.

Regla:

- usar logger estandar por defecto
- si Stackraise logging esta disponible, permitir integrarlo
- nunca emitir logs del protocolo MCP por stdout arbitrario

### Entregables

- modulo de settings usable
- sistema de permisos reusable
- errores consistentes
- logger base

### Criterios de aceptacion

- tests unitarios de settings y permissions
- configuracion carga desde `.env`
- permisos bloquean escrituras no autorizadas

---

## Fase 2. Registry y arranque del servidor

### Objetivo

Poder arrancar un servidor MCP minimo y registrar tools dinamicamente.

### Archivos

- `core/registry.py`
- `core/server.py`
- `main.py`

### Tareas detalladas

#### 1. `core/registry.py`

Implementar un `ToolRegistry` o funcion de registro que:

- reciba settings
- reciba instancia del servidor MCP
- cargue tools por grupos segun flags
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
- inicializacion de adapters
- registro de tools
- funcion `create_server()`

#### 3. `main.py`

Implementar CLI minima con subcomandos:

- `serve`
- `init`
- `doctor` opcional

Ampliacion CLI:

- `context snapshot`
- `context doctor`

### Entregables

- servidor arrancable
- registro dinamico funcionando
- CLI minima usable

### Criterios de aceptacion

- `poetry run abstract-mcp serve` arranca sin error
- `ping` o tool equivalente responde
- el servidor registra tools habilitadas

---

## Fase 3. Bootstrap y deteccion de proyecto

### Objetivo

Hacer que el MCP sea facil de configurar en nuevos proyectos.

### Archivos

- `bootstrap/init_project.py`
- `bootstrap/detect_project.py`
- `templates/*`

### Tareas detalladas

#### 1. `detect_project.py`

Implementar deteccion heuristica de:

- proyecto Poetry
- presencia de FastAPI
- path probable de app (`app.main:app`, `main:app`, `demo:app`, etc.)
- uso de Stackraise
- uso de MongoDB

Ampliacion deteccion Stackraise real:

- detectar `backend/src/stackraise`
- detectar `backend/src/demo`
- detectar `frontend/libs/@stackraise/core`
- detectar `frontend/libs/@stackraise/auth`

#### 2. `init_project.py`

Implementar comando `init` que:

- cree `.env.example`
- cree `mcp.project.yaml`
- cree `AGENTS.md`
- cree `opencode.jsonc`
- no sobrescriba sin confirmacion
- permita modo dry-run

#### 3. Plantillas Jinja

Crear:

- `AGENTS.md.j2`
- `opencode.jsonc.j2`
- `mcp.project.yaml.j2`
- `env.j2`

### Entregables

- bootstrap automatico
- plantillas de integracion
- deteccion basica del proyecto

### Criterios de aceptacion

- `poetry run abstract-mcp init` genera ficheros
- las plantillas se rellenan con valores validos
- funciona en un repo FastAPI/Poetry tipico

---

## Fase 4. Adapters base

### Objetivo

Aislar la logica de acceso a FastAPI, Mongo y Stackraise.

### Archivos

- `adapters/fastapi_adapter.py`
- `adapters/mongodb_adapter.py`
- `adapters/stackraise_adapter.py`

### 4.1 `FastAPIAdapter`

#### Responsabilidades

- importar app FastAPI desde `fastapi_app_path`
- listar rutas
- exponer resumen OpenAPI
- buscar rutas por patron
- devolver tags y metodos

#### Metodos recomendados

- `load_app()`
- `list_routes()`
- `find_routes(path_fragment)`
- `get_openapi_summary()`

#### Criterio de aceptacion

- funciona con una app FastAPI de ejemplo
- no rompe si el import path es invalido: devuelve error controlado

### 4.2 `MongoDBAdapter`

#### Responsabilidades

- intentar resolver cliente Mongo via Stackraise si aplica
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

- lecturas permitidas segun configuracion general
- escrituras delegan en `core.permissions`

#### Criterio de aceptacion

- puede listar colecciones y muestrear documentos
- bloquea escritura si no esta permitida

### 4.3 `StackraiseAdapter`

#### Responsabilidades

- detectar modulos disponibles:
  - `stackraise.model`
  - `stackraise.db`
  - `stackraise.logging`
  - `stackraise.di`
  - `stackraise.ctrl`
  - `stackraise.auth`
  - `stackraise.ai`
  - `stackraise.templating`
  - `stackraise.io`
- exponer metadatos utiles del framework
- si es posible, resolver:
  - cliente DB
  - logger
  - bindings DI
  - recursos CRUD

#### Metodos recomendados

- `detect_modules()`
- `is_available()`
- `get_db_metadata()`
- `get_logging_metadata()`
- `get_di_metadata()`
- `list_crud_resources()` si se puede inferir

Metodos ampliados (contexto):

- `get_domain_model_graph()`
- `get_auth_scope_map()`
- `get_workflow_map()`
- `get_frontend_contracts()`

#### Nota importante

No asumir APIs internas no confirmadas. Disenar el adapter para:

- detectar de forma segura
- degradar con elegancia si algo no existe
- devolver `no soportado` en vez de romper

#### Criterio de aceptacion

- detecta presencia de Stackraise
- no rompe cuando Stackraise no esta instalado
- puede integrarse opcionalmente con DB/logging

---

## Fase 5. Tools de salud y sistema

### Objetivo

Tener tools basicas para diagnosticar el MCP y el entorno.

### Archivo

- `tools/health.py`

### Tools a implementar

- `ping()`
- `show_runtime_config()`
- `list_enabled_tools()`
- `check_project_health()`

### Comportamiento esperado

- `ping`: devuelve estado simple
- `show_runtime_config`: devuelve configuracion efectiva sanitizada
- `list_enabled_tools`: enumera grupos activos
- `check_project_health`: valida presencia de FastAPI, Stackraise, Poetry, etc.

### Criterio de aceptacion

- usable desde servidor MCP
- salida consistente y serializable

---

## Fase 6. Tools de calidad y tests

### Objetivo

Exponer capacidades estandar de validacion del proyecto.

### Archivos

- `tools/poetry_tools.py`
- `tools/test_tools.py`
- `tools/quality_tools.py`

### Tareas detalladas

#### 1. Helpers de ejecucion de comandos

Crear helper interno seguro para ejecutar comandos.

Requisitos:

- timeout configurable
- captura de stdout/stderr
- salida serializable
- codigos de retorno claros

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

Tools minimas:

- `poetry_install()`
- `poetry_show()`

Evitar en v1 una tool abierta tipo "ejecuta cualquier comando".

### Criterio de aceptacion

- desde MCP se pueden lanzar tests
- desde MCP se puede correr ruff/pyright
- las salidas son legibles por otro agente

---

## Fase 7. Tools de FastAPI

### Objetivo

Dar capacidades de introspeccion utiles para analisis, build y auditoria.

### Archivo

- `tools/fastapi_tools.py`

### Tools a implementar

- `list_routes()`
- `find_route(path_fragment)`
- `show_openapi_summary()`
- `list_routes_by_tag(tag)` opcional si es simple

### Formato de salida recomendado

Cada ruta deberia incluir:

- path
- methods
- name
- tags si existen

### Criterio de aceptacion

- con una app de ejemplo, lista rutas correctamente
- puede filtrar por fragmento de path
- no falla de forma abrupta si OpenAPI no esta disponible

---

## Fase 8. Tools de MongoDB

### Objetivo

Dar herramientas de inspeccion y escritura controlada.

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
  - validar coleccion permitida
  - soportar `confirmed`
  - registrar intencion/resultado

### Criterio de aceptacion

- en entorno de prueba, operaciones readonly funcionan
- operaciones write fallan si no hay permiso
- operaciones write pasan si:
  - entorno permitido
  - coleccion permitida
  - confirmacion explicita
  - settings lo permiten

---

## Fase 9. Tools de Stackraise

### Objetivo

Exponer el valor anadido del framework interno.

### Archivo

- `tools/stackraise_tools.py`

### Tools v1

- `detect_stackraise()`
- `show_stackraise_modules()`
- `show_stackraise_db_metadata()`
- `show_stackraise_logging_metadata()`
- `show_stackraise_di_metadata()`
- `list_stackraise_resources()` solo si se puede obtener de forma fiable

### Tools ampliadas de contexto

- `build_stackraise_context_snapshot(mode='hybrid')`
- `list_stackraise_documents()`
- `list_stackraise_crud_resources()`
- `show_stackraise_auth_scopes()`
- `list_stackraise_workflows()`
- `show_stackraise_frontend_contracts()`
- `show_stackraise_context_warnings()`

### Regla

No inventar introspeccion que no este soportada. Implementar deteccion progresiva:

- primero modulos
- luego metadatos accesibles
- luego recursos avanzados si el framework los expone claramente

### Criterio de aceptacion

- funciona sin Stackraise instalado devolviendo estado controlado
- con Stackraise disponible, devuelve informacion util

---

## Fase 10. Integracion con OpenCode

### Objetivo

Dejar el paquete listo para ser consumido como MCP local.

### Archivos generados por bootstrap

- `AGENTS.md`
- `opencode.jsonc`

### Requisitos del `opencode.jsonc`

- agente `plan`
- agente `build`
- agente `audit`
- conexion al MCP local usando:
  - `poetry run abstract-mcp serve`

### Comportamiento esperado de agentes

#### Plan

- sin edicion
- sin escrituras Mongo
- lectura, inspeccion y tests permitidos
- debe arrancar con `build_stackraise_context_snapshot`

#### Build

- edicion permitida bajo confirmacion
- tools de calidad y tests
- escrituras controladas posibles si settings lo permiten
- debe usar snapshot de contexto antes de modificar codigo

#### Audit

- sin edicion
- foco en revision, calidad, configuracion, riesgos
- debe reportar huecos de contexto y riesgos de secretos

### Criterio de aceptacion

- bootstrap genera un `opencode.jsonc` valido
- el proyecto puede arrancar OpenCode con el MCP local

---

## Fase 11. Tests

### Objetivo

Validar componentes criticos.

### Cobertura minima recomendada

#### Unit tests

- settings
- permissions
- registry
- helpers de ejecucion de comandos
- adapters en condiciones normales y de error

#### Integration-like tests

- FastAPI adapter con app demo
- Mongo adapter con mock o entorno de prueba
- tools health
- tools readonly

#### Tests ampliados de contexto

- extraccion static en repo con estructura Stackraise
- extraccion runtime (si entorno disponible)
- modo hybrid con fallback
- redaccion de secretos
- estabilidad del schema de salida

### Importante

Para MongoDB:

- preferible usar mock o contenedor local en tests de integracion
- no depender de una base real no controlada

### Criterio de aceptacion

- tests de settings y permissions obligatorios
- al menos un test por grupo de tools
- `poetry run pytest` pasa

---

## Fase 12. Documentacion

### Objetivo

Permitir a otro desarrollador instalarlo y usarlo.

### Archivos

- `README.md`
- ejemplos de configuracion
- seccion de seguridad

### Contenido minimo del README

1. que es el paquete
2. instalacion
3. como arrancar
4. como hacer bootstrap en un proyecto
5. configuracion `.env`
6. configuracion YAML
7. lista de tools
8. politica de write operations
9. ejemplo de `opencode.jsonc`
10. troubleshooting

Contenido ampliado obligatorio:

11. contrato del contexto Stackraise
12. modos de extraccion (`static/runtime/hybrid`)
13. politica de redaccion de secretos
14. limitaciones conocidas en introspeccion runtime

### Criterio de aceptacion

- alguien ajeno puede instalarlo siguiendo el README
- el README explica claramente los limites de la v1

---

## 7. Orden de implementacion recomendado

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
24. anadir tests
25. documentar
26. probar integracion local completa

Orden ampliado de contexto:

27. implementar `context/schemas.py`
28. implementar `context/extractors_static.py`
29. implementar `context/extractors_runtime.py`
30. implementar `context/normalizer.py` y `context/redaction.py`
31. conectar `stackraise_tools.py` con `context/*`
32. anadir tests de contexto y redaccion

---

## 8. Dependencias tecnicas concretas

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

## 9. Reglas de implementacion para el otro agente

### Regla 1

No acoplar tools directamente a imports del proyecto final.
Usar adapters.

### Regla 2

No asumir detalles internos de Stackraise no confirmados.
Implementar deteccion defensiva.

### Regla 3

Toda operacion de escritura debe pasar por `core.permissions`.

### Regla 4

No exponer en v1 una tool abierta para ejecutar shell arbitrario.

### Regla 5

Toda salida de tool debe ser:

- serializable
- consistente
- razonablemente breve
- apta para ser leida por otro agente

### Regla 6

Los errores deben ser controlados y comprensibles.

### Regla 7

La configuracion debe poder venir de:

- `.env`
- YAML
- defaults internos

### Regla 8

Si Stackraise esta disponible, usarlo prioritariamente frente a `pymongo`.

### Regla 9 (ampliada)

Toda salida de contexto debe pasar por redaccion de secretos.

### Regla 10 (ampliada)

Si falla runtime introspection, hacer fallback a static y anotar warnings.

---

## 10. Definicion de done

El proyecto se considera terminado cuando:

1. `poetry install` funciona
2. `poetry run abstract-mcp serve` arranca
3. el MCP expone tools basicas
4. `poetry run abstract-mcp init` genera configuracion
5. FastAPI adapter funciona con app demo
6. Mongo adapter funciona en readonly
7. write controls estan implementados
8. Stackraise detection funciona
9. existe `opencode.jsonc` de ejemplo
10. existe `AGENTS.md` de ejemplo
11. `poetry run pytest` pasa
12. `poetry run ruff check .` pasa
13. el README explica instalacion y uso

Done ampliado:

14. `build_stackraise_context_snapshot` devuelve schema valido
15. contexto funciona en modo `hybrid` con fallback
16. secretos redaccionados por defecto
17. warnings de contexto incompleto cuando aplique

---

## 11. Riesgos y mitigaciones

### Riesgo 1: Stackraise no expone APIs introspectables claras

Mitigacion:
Disenar `stackraise_adapter` como deteccion progresiva y fallback elegante.

### Riesgo 2: demasiada ambicion en v1

Mitigacion:
Limitar v1 a tools de alto valor y dejar introspeccion avanzada para v2.

### Riesgo 3: escrituras peligrosas en Mongo

Mitigacion:
Implementar validacion estricta:

- entornos permitidos
- colecciones permitidas
- confirmacion obligatoria
- logging de operacion

### Riesgo 4: bootstrap demasiado acoplado a una estructura concreta

Mitigacion:
Hacer deteccion heuristica con defaults editables, no hardcodeados.

### Riesgo 5: salidas de tools demasiado verbosas

Mitigacion:
Normalizar respuestas y truncar stdout/stderr si hace falta.

### Riesgo 6 (ampliado): fuga de secretos en snapshot/contexto

Mitigacion:
- redaccion centralizada
- denylist de claves sensibles (`password`, `secret`, `token`, `api_key`, etc.)
- excluir contenido de `.env` y settings no sanitizados

---

## 12. Backlog posterior a la v1

Dejar anotado, pero no implementar en esta fase:

- soporte HTTP/streamable transport
- auditoria por endpoint sin tests
- diff de OpenAPI entre versiones
- introspeccion avanzada de CRUD autogenerados por Stackraise
- herramientas de RPA
- soporte multi-entorno
- integracion con logs estructurados de Stackraise
- comparacion de configuracion efectiva entre proyectos

Backlog ampliado:

- graph de dependencias dominio->servicios->API
- matriz endpoint->scopes->modelo
- diff de snapshot de contexto entre ramas/versiones

---

## 13. Contexto observado de Stackraise en este repo (para guiar al otro agente)

### Layout principal

- backend: `backend/`
- frontend: `frontend/`
- framework Python: `backend/src/stackraise/`
- app demo FastAPI: `backend/src/demo/`

### Modulos backend Stackraise relevantes

- modelado: `backend/src/stackraise/model/`
- persistencia Mongo: `backend/src/stackraise/db/`
- controladores CRUD/change-stream/file-storage: `backend/src/stackraise/ctrl/`
- auth y scopes: `backend/src/stackraise/auth/`
- DI: `backend/src/stackraise/di.py`
- logging: `backend/src/stackraise/logging.py`
- AI/RPA: `backend/src/stackraise/ai/`
- templating: `backend/src/stackraise/templating/`
- IO mail: `backend/src/stackraise/io/`

### App demo (dominio y APIs)

- app principal: `backend/src/demo/app.py`
- settings: `backend/src/demo/settings.py`
- dominio: `backend/src/demo/domain/`
- APIs: `backend/src/demo/api/`
- servicios/workflows: `backend/src/demo/service/`

### Frontend reutilizable

- `@stackraise/core`: `frontend/libs/@stackraise/core/`
- `@stackraise/auth`: `frontend/libs/@stackraise/auth/`
- demo app: `frontend/apps/demo/`

### Seguridad (dato importante para el agente)

Existen ficheros de configuracion en backend con credenciales en claro en este repo. El MCP debe:

- no exponer estos valores en salida
- redaccionar por defecto
- reportar warning de riesgo

---

## 14. Prompt operativo final para otro agente

Usa este prompt tal cual:

> Implementa un paquete Python llamado `abstract-backend-mcp` con soporte para Python 3.12+, Poetry, FastAPI, MongoDB y Stackraise.
> La arquitectura debe separarse en `core`, `adapters`, `tools`, `bootstrap`, `context` y `templates`.
> Debe haber configuracion con Pydantic Settings, registro dinamico de tools, adapters para FastAPI/MongoDB/Stackraise, tools de health, tests, quality, FastAPI, MongoDB y Stackraise.
> Las escrituras Mongo deben ser controladas mediante una capa de permisos central.
> Debe existir un CLI con `serve`, `init` y un comando de contexto.
> Debe generarse integracion base con OpenCode usando agentes `plan`, `build` y `audit`.
> Prioriza una v1 pequena pero solida.
> No asumas APIs internas de Stackraise que no puedas detectar de forma segura.
> Toda salida debe ser serializable y usable por otro agente.
> Anade tests minimos y documentacion suficiente para instalarlo y usarlo.
>
> Adicional obligatorio para Stackraise:
> 1) Implementa `build_stackraise_context_snapshot(mode='hybrid')` con schema estable que incluya:
>    - `project`
>    - `stackraise.modules`
>    - `stackraise.domain` (documents, refs, collections, indexes)
>    - `stackraise.api` (routes, crud resources, openapi summary)
>    - `stackraise.auth` (scopes, guards)
>    - `stackraise.workflows` (rpa, email watcher, doc generation)
>    - `stackraise.frontend_contracts`
>    - `security` (redacted, warnings)
>    - `extraction` (mode, fallback warnings)
> 2) Implementa extraccion hibrida (`static/runtime`) con fallback seguro.
> 3) Redacciona secretos por defecto en todas las tools de contexto.
> 4) Si falla runtime, no romper: devolver snapshot parcial + warnings claros.
>
> Entrega esperada:
> - paquete instalable
> - servidor MCP funcional
> - bootstrap usable
> - tools de contexto Stackraise funcionando
> - tests minimos de settings/permissions/registry/context
> - README con instalacion, uso, limites y politica de seguridad.

---

## 15. Recomendacion final de ejecucion

Para implementacion por otro agente, dividir en 4 bloques:

### Bloque A

Core + server + CLI + bootstrap

### Bloque B

Adapters + tools base

### Bloque C

Contexto Stackraise (`context/*` + tools de snapshot)

### Bloque D

Tests + documentacion + integracion OpenCode

Este reparto evita mezclar infraestructura con logica de contexto demasiado pronto y permite validar base tecnica antes de la introspeccion avanzada.
