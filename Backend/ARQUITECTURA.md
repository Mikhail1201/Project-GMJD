# Arquitectura del Backend — Project GMJD

Diagrama de la arquitectura en capas del backend. Está escrito en
[Mermaid](https://mermaid.js.org/), que **GitHub renderiza automáticamente** en
cualquier archivo `.md` — no necesitas exportar una imagen ni instalar nada
para verlo en el repositorio.

## Flujo general de una petición

```mermaid
flowchart LR
    U["👤 Cliente<br/>Formulario / Frontend"]

    subgraph APP["BACKEND — Flask"]
        direction TB

        API["🌐 API / Blueprints<br/><small>Validación · HTTP · JSON</small>"]

        subgraph LOGIC["Lógica de aplicación"]
            direction LR
            REPO["🗄️ Repositories<br/><small>SQL + reglas de negocio</small>"]
            CAT["📚 Catálogos<br/><small>IDs de rol / estado<br/>+ caché</small>"]
            MODEL["📦 Models<br/><small>Dataclasses<br/>Fila ↔ objeto</small>"]
        end

        subgraph CORE["Infraestructura"]
            direction LR
            DB["⚙️ database.py<br/><small>SQLAlchemy Engine<br/>Pool de conexiones</small>"]
            AUTH["🔐 auth.py<br/><small>NeonAuthClient</small>"]
        end
    end

    PG[("🐘 PostgreSQL<br/>Neon")]
    NA["🔑 Neon Auth<br/><small>Better Auth managed</small>"]

    U -->|"HTTP + JSON"| API
    API -->|"llama"| REPO
    API -->|"usa"| MODEL

    REPO -->|"resuelve IDs"| CAT
    REPO -->|"SQL"| DB
    CAT -->|"SQL"| DB
    DB -->|"conexión pooled"| PG

    API -.->|"solo al crear usuarios"| AUTH
    AUTH -->|"REST API"| NA
    NA -.->|"auth_user_id · UUID"| AUTH

    API -->|"HTTP + JSON"| U

    classDef client fill:#e8f0fe,stroke:#4285f4,stroke-width:2px,color:#1a1a1a
    classDef api fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef logic fill:#f3e8ff,stroke:#8e44ad,stroke-width:1.5px,color:#4a235a
    classDef core fill:#fff3e0,stroke:#ef6c00,stroke-width:1.5px,color:#5d4037
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    classDef auth fill:#fff8e1,stroke:#f9a825,stroke-width:2px,color:#6d4c00

    class U client
    class API api
    class REPO,CAT,MODEL logic
    class DB,AUTH core
    class PG db
    class NA auth

    style APP fill:#fafafa,stroke:#616161,stroke-width:2px
    style LOGIC fill:#ffffff,stroke:#b39ddb,stroke-dasharray:5 5
    style CORE fill:#ffffff,stroke:#ffb74d,stroke-dasharray:5 5
```
mermaid
flowchart TD
    Cliente["Cliente<br/>(formulario HTML / futuro frontend)"]

    subgraph Flask["Flask app (app/)"]
        Rutas["api/rutas_&lt;tabla&gt;.py<br/>Blueprints — validan input,<br/>arman respuestas JSON"]
        Repo["repositories/&lt;tabla&gt;_repo.py<br/>Toda la lógica SQL vive aquí"]
        Modelo["models/&lt;tabla&gt;.py<br/>@dataclass — solo contenedor de datos"]
        Catalogos["repositories/catalogos.py<br/>obtener_id_estado() / obtener_id_rol()<br/>(cacheado con lru_cache)"]
        DB["core/database.py<br/>engine de SQLAlchemy"]
        Auth["core/auth.py<br/>NeonAuthClient"]
    end

    Postgres[("PostgreSQL<br/>(Neon)")]
    NeonAuth["Neon Auth<br/>(Better Auth managed)"]

    Cliente -- "HTTP request<br/>(JSON)" --> Rutas
    Rutas -- "usa" --> Modelo
    Rutas -- "llama a" --> Repo
    Repo -- "consulta ids de<br/>estado/rol" --> Catalogos
    Repo -- "SQL vía text()" --> DB
    Catalogos -- "SQL vía text()" --> DB
    DB -- "conexión pooled" --> Postgres
    Rutas -. "solo en creación<br/>de usuarios" .-> Auth
    Auth -- "REST API<br/>+ header Origin" --> NeonAuth
    NeonAuth -. "auth_user_id (UUID)" .-> Auth
    Rutas -- "HTTP response<br/>(JSON)" --> Cliente

    style Cliente fill:#e8f0fe,stroke:#4285f4
    style Postgres fill:#e6f4ea,stroke:#34a853
    style NeonAuth fill:#fef7e0,stroke:#fbbc04
    style Flask fill:#fafafa,stroke:#999
```

## Qué hace cada capa

| Capa | Responsabilidad | Lo que **no** hace |
|---|---|---|
| `api/rutas_*.py` (Blueprints) | Recibe el request, valida campos requeridos, llama al repositorio correspondiente, traduce errores (`ValueError`/`IntegrityError`) a códigos HTTP | No contiene SQL |
| `models/*.py` (dataclasses) | Define la forma tipada de cada fila (`Usuario`, `Alerta`, ...) y la conversión `fila de BD → objeto` / `objeto → dict` | No tiene lógica de negocio ni SQL |
| `repositories/*_repo.py` | Todo el SQL: `listar`, `obtener`, `crear`, `actualizar`, `eliminar`, y las reglas de negocio (soft delete, paginación, validación de enums, atomicidad de operaciones como "cerrar límite anterior + crear nuevo") | No conoce Flask ni HTTP |
| `repositories/catalogos.py` | Resuelve nombres de estado/rol a sus IDs reales en cada ambiente, con caché en memoria | No expone endpoints propios |
| `core/database.py` | Engine único de SQLAlchemy compartido por todos los repos (`pool_pre_ping` para las conexiones serverless de Neon) | No ejecuta queries directamente |
| `core/auth.py` (`NeonAuthClient`) | Login de la cuenta admin técnica contra Neon Auth, creación de usuarios vía `/admin/create-user`, reintento en `401` | No toca la tabla `usuarios` de negocio (esa la maneja `usuario_repo.py`) |

## Por qué esta separación

- **Testeable por capas**: se puede probar un repositorio con una base de datos
  de prueba sin levantar Flask, o mockear el repositorio para probar una ruta
  sin tocar la base de datos real.
- **El SQL no se repite mezclado con lógica de HTTP**: cada tabla tiene un único
  lugar donde vive su SQL.
- **El contrato HTTP es estable aunque cambie la implementación interna**: la
  refactorización de `api/<tabla>/routes.py` (SQL directo) a
  `repositories/<tabla>_repo.py` (capas) no cambió ninguna URL, método ni forma
  de los JSON — el frontend/formulario no necesitó ningún cambio.

## Referencia si prefieres rehacerlo tú mismo

Si quieres editarlo o rehacerlo con otra herramienta:

- **Mermaid Live Editor**: https://mermaid.live — pega el bloque de código de
  arriba y lo puedes exportar como PNG/SVG.
- **draw.io / diagrams.net** (https://app.diagrams.net): si prefieres un
  diagrama de cajas más visual/manual en vez de código, es la alternativa más
  usada; exporta a PNG/SVG y lo puedes insertar como imagen en el README.
- **C4 Model** (https://c4model.com): si el proyecto crece y quieres un
  estándar más formal de diagramas de arquitectura (Contexto → Contenedores →
  Componentes), este es el framework de referencia — probablemente
  sobre-dimensionado para el tamaño actual del backend, pero útil si en el
  futuro se suma un frontend propio, más servicios, etc.
