# Project GMJD — Backend

Backend en **Flask** para el proyecto de monitoreo ambiental de **Monomeros**
(Barranquilla, Colombia): mide temperatura, humedad y gases para determinar si
el ambiente representa un riesgo para las personas o los productos en la zona.

Base de datos: **PostgreSQL en Neon**, con autenticación gestionada vía
**Neon Auth** (Better Auth).

## Stack

- Python 3 + Flask
- SQLAlchemy Core (consultas SQL explícitas con `text()`, sin ORM)
- PostgreSQL (Neon, serverless)
- Neon Auth para gestión de usuarios/sesiones
- `requests` para la integración con la API de administración de Neon Auth

## Estructura del proyecto

```
Backend/
├── main.py                        # entry point: app = create_app()
├── requirements.txt
├── .env.example                    # plantilla de variables de entorno
└── app/
    ├── __init__.py                 # create_app(): registra blueprints y rutas base
    ├── core/
    │   ├── database.py             # engine de SQLAlchemy (pool_pre_ping para Neon)
    │   ├── constants.py            # nombres de estados/roles (NO ids hardcodeados)
    │   └── auth.py                 # NeonAuthClient: login admin + creación de usuarios
    ├── models/                     # una @dataclass simple por tabla (sin lógica)
    │   ├── base.py                 # ModeloBase: desde_fila() / a_dict()
    │   └── <tabla>.py
    ├── repositories/                # toda la lógica SQL, una clase por tabla
    │   ├── catalogos.py             # obtener_id_estado() / obtener_id_rol(), cacheados
    │   └── <tabla>_repo.py
    ├── api/
    │   └── rutas_<tabla>.py         # blueprints Flask: validan input, llaman al repo
    └── templates/
        └── formulario_usuario.html  # formulario de prueba para creación de usuarios
```

**Arquitectura en capas** (ver `ARQUITECTURA.md` para el diagrama):
`ruta Flask → repository → SQLAlchemy (text()) → Postgres`. Los modelos
(`dataclass`) son solo contenedores de datos tipados; toda la lógica de acceso a
datos vive en los repositorios.

## Tablas / recursos cubiertos

`roles`, `estados`, `usuarios`, `areas`, `parametros_ambientales`, `mediciones`,
`limites_ambientales`, `alertas`, `incidentes_ambientales`, `mantenimientos`,
`modelos_ia`, `predicciones_ia` — ver `API.md` para el detalle de cada endpoint.

### Estrategia de borrado por tipo de tabla

| Tipo de tabla | Estrategia | Tablas |
|---|---|---|
| Entidad con ciclo de vida | soft delete vía `id_estado` | usuarios, areas, alertas, incidentes_ambientales, modelos_ia |
| Histórico/versionado temporal | `fecha_fin` (no se borra) | limites_ambientales |
| Log append-only | no se borra | mediciones, predicciones_ia, mantenimientos |
| Catálogo | DELETE real + validación de FK | roles, estados, parametros_ambientales |

## Requisitos previos

- Python 3.11+
- Un proyecto en [Neon](https://neon.tech) con la base de datos ya creada
  (ver esquema SQL del proyecto) y **Neon Auth** habilitado
- Una cuenta admin "técnica" en Neon Auth con rol admin (no una cuenta personal)

## Instalación

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y completa con tus propios valores:

```bash
cp .env.example .env
```

```env
NEON_DATABASE_URL=postgresql://usuario:contraseña@host/basededatos?sslmode=require
NEON_AUTH_URL=https://tu-endpoint.neonauth.<region>.aws.neon.tech/neondb/auth
NEON_AUTH_ADMIN_EMAIL=admin.sistema@tuempresa.com
NEON_AUTH_ADMIN_PASSWORD=contraseña-de-la-cuenta-tecnica
```

> ⚠️ **Nunca subas `.env` a git**, y asegúrate de que `.env.example` solo tenga
> valores de ejemplo — nunca credenciales reales. Si una credencial real llega
> a quedar en el historial de git, rótala de inmediato en el dashboard de Neon,
> sin importar si el repositorio es público o privado.

`NEON_AUTH_ADMIN_EMAIL`/`PASSWORD` corresponden a una cuenta técnica creada
específicamente para que el backend administre usuarios — no es la cuenta
personal de ningún desarrollador. Debe tener rol admin asignado desde el
Console de Neon (Auth → Users → **Make admin**), y el origen desde el que corre
el backend (ej. `http://localhost:8000`) debe estar en la lista de **Trusted
origins** del proyecto en Neon Auth (Console → Auth → Configuration).

## Ejecutar el servidor

```bash
python main.py
```

También es válido usar:

```bash
flask --app app run --host=0.0.0.0 --port=8000
```

Por defecto corre en `http://localhost:8000` con `debug=True`.

- `GET /health` — verifica la conexión a la base de datos
- `GET /formulario-usuario` — formulario de prueba para crear un usuario
- Endpoints de la API bajo `/api/...` — ver `API.md`

## Notas de diseño

- **Los IDs de `estados`/`roles` no son estables entre ambientes.** Se resuelven
  en tiempo de ejecución vía `obtener_id_estado("Activo")` /
  `obtener_id_rol("empleado")` (en `app/repositories/catalogos.py`), cacheados en
  memoria con `lru_cache` porque esas tablas casi no cambian.
- **Creación de usuarios**: no hay auto-registro público. Un admin crea las
  cuentas desde el formulario interno; el backend llama a la API de
  administración de Neon Auth y luego inserta la fila de negocio en `usuarios`
  en la misma petición, de forma síncrona (una sola operación atómica en vez de
  depender de webhooks).
- **Sesión admin cacheada**: `NeonAuthClient` mantiene una sesión de `requests`
  en memoria de proceso, con reintento automático de login si expira (401).
  No está probado su comportamiento bajo múltiples workers de Flask
  concurrentes — pendiente si el proyecto escala a ese punto.

## Pendientes conocidos

- No hay flujo de **login** del lado del empleado (solo creación de cuenta por
  el admin).
- Los enums libres (`calidad_dato`, `tipo` en mantenimientos, `nivel`/`severidad`,
  `tipo_modelo`) se validan como listas fijas en cada repositorio, no como tabla
  de catálogo — evaluar si conviene unificarlos en una tabla `catalogos` genérica
  si el número de categorías crece.
- No hay tests automatizados todavía.
