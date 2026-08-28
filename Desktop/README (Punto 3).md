# Guía sencilla y bitácora — Aplicación de Escritorio Monómeros

**Proyecto:** Monitoreo de Gas, Humedad y Temperatura en Monómeros S.A.
**Equipo:** Grupo 8 (Daniel, Miguel, Guillermo y Juan)
**Módulo:** Punto 3 - Aplicación de Escritorio en Python (20%)
**Tecnología:** Python 3 + PySide6 (Qt), consumiendo el backend Flask del Punto 1
**Carpeta del proyecto:** `Desktop/`

**Cómo se ejecuta:**
```bash
cd Desktop
pip install -r requirements.txt
python main.py
```
(Antes de correrla hay que tener el backend prendido, revisar `Desktop/.env` para que `BACKEND_URL` apunte a la URL correcta, ej. `http://127.0.0.1:8000`)

---

## 1. ¿Qué hace esta aplicación?

Es el "panel de control" que usaría un operario o un ingeniero de la planta para vigilar todo lo que el ESP32 (y el resto del sistema) va guardando en la base de datos, sin tener que meterse a Postman ni a la base de datos directamente. No es una página web ni una app de consola: es una ventana de escritorio de verdad, hecha con PySide6 (la versión oficial de Qt para Python), con menú lateral, tablas, gráficos tipo velocímetro y generación de reportes en PDF.

La aplicación **no** habla con la base de datos directamente. Todo lo que muestra en pantalla lo pide por internet (HTTP) al backend Flask del Punto 1, que es el único que sabe hablar con Neon/PostgreSQL:

```
App de Escritorio (PySide6)  --HTTP/JSON-->  Backend Flask  --SQL-->  Neon (PostgreSQL)
```

La app tiene 5 pantallas, todas accesibles desde un menú lateral que se puede colapsar con el botón ☰:

1. **Panel Principal (Dashboard):** vista general en vivo, con relojes tipo velocímetro (gauges) para los parámetros más importantes, una tabla con las últimas mediciones y otra con las alertas críticas/altas recientes. Se refresca sola cada 15 segundos.
2. **Historial de Mediciones:** tabla con TODAS las mediciones guardadas, con filtros (área, parámetro, calidad del dato, rango de fechas), paginación y exportación a PDF.
3. **Alertas:** tabla de alertas generadas automáticamente cuando una medición se sale de rango, con filtros por área/nivel y un botón para marcarlas como "atendidas".
4. **Incidentes Ambientales:** tabla de incidentes (algo más grave que una alerta, ej. una fuga real), con botón para crearlos manualmente y para marcarlos como resueltos.
5. **Reportes PDF:** formulario para generar un reporte en PDF de un área y un rango de fechas, incluyendo mediciones y/o alertas.

Además tiene un botón para cambiar entre modo claro y modo oscuro (se recuerda la próxima vez que se abre la app) y un indicador (pastilla de color) arriba que dice si hay conexión con el backend o no, revisándolo cada cierto tiempo, no solo al abrir la app.

---

## 2. Librerías utilizadas y para qué sirven

(Ver `Desktop/requirements.txt`)

| Librería | Para qué se usa |
|---|---|
| **PySide6** | Es el framework de interfaz gráfica (GUI). Con esto se construyen la ventana, el menú lateral, las tablas, los formularios, los diálogos y los gráficos tipo velocímetro (estos últimos dibujados a mano con QPainter, no son una librería de gráficos aparte). El profesor pidió explícitamente NO usar tkinter, por eso se escogió PySide6 (la versión con licencia libre de Qt para Python). |
| **requests** | Es el cliente HTTP. Con esto la app le hace peticiones GET/PUT/POST al backend Flask (consultar datos, atender alertas, crear incidentes, etc.). |
| **python-dotenv** | Lee el archivo `Desktop/.env` para poder configurar la URL del backend (`BACKEND_URL`) sin tener que escribirla a mano en el código. Así, si el backend cambia de puerto o de servidor, solo se edita el `.env`. |
| **reportlab** | Genera los reportes en PDF (Reportes PDF), con tablas, colores según el nivel de alerta y texto que se ajusta solo (usando objetos `Paragraph`) para que no se encimen las letras en las celdas. |

Aparte de esas 4, se usan únicamente librerías propias de Python que ya vienen instaladas (`datetime`, `re`, `json`, `weakref`, `pathlib`, etc.), no se agregó nada más.

---

## 3. Cómo está construida (arquitectura POO, carpeta por carpeta)

El profesor pidió que la app estuviera hecha con Programación Orientada a Objetos (POO), así que en vez de un solo archivo con todo el código, se organizó en paquetes, cada uno con una responsabilidad clara (como si fueran distintos departamentos de una empresa):

```
Desktop/
├── main.py                     Punto de entrada. Crea la QApplication,
│                                muestra la ventana principal y captura
│                                cualquier error no controlado (para que la
│                                app no se cierre de golpe sin avisar, sino
│                                que muestre un mensaje y lo guarde en
│                                Desktop/errores.log).
├── .env                        Configuración local (URL del backend).
├── requirements.txt            Lista de librerías (sección 2).
│
└── app/
    ├── config.py                Lee el .env: BACKEND_URL, tiempo de espera
    │                             de las peticiones (TIMEOUT_SEGUNDOS) y cada
    │                             cuánto se refresca el Dashboard solo
    │                             (INTERVALO_REFRESCO_MS).
    ├── state.py                  Clase Catalogos: guarda en memoria, desde
    │                             que arranca la app, la lista de áreas,
    │                             parámetros y usuarios, para no tener que
    │                             pedirla otra vez cada vez que se necesita
    │                             mostrar un nombre en vez de un ID.
    ├── utils.py                  Funciones para fechas y números: convierte
    │                             las fechas UTC que manda el backend a hora
    │                             de Colombia (America/Bogotá, UTC-5) y las
    │                             muestra en español (ej. "mar, 26 ago 2026,
    │                             03:45 p.m."); también arma el filtro de
    │                             fecha en UTC a partir de una fecha local
    │                             para que el filtro de "hoy" busque el día
    │                             de Bogotá y no el de Greenwich.
    │
    ├── api/
    │   ├── client.py             Clase ApiClient: el único punto de la app
    │   │                         que le habla al backend por HTTP. Tiene un
    │   │                         método por cada endpoint (ver sección 4) y
    │   │                         maneja los errores: si el backend responde
    │   │                         mal o se cae, convierte eso en un mensaje
    │   │                         corto y entendible en vez de mostrar la
    │   │                         página de error completa de Flask.
    │   └── exceptions.py         Clase ApiError: el tipo de error propio
    │                             que lanza ApiClient cuando algo falla.
    │
    ├── services/
    │   ├── worker.py             Clase ApiWorker (QThread): para que la
    │   │                         ventana no se "congele" mientras espera la
    │   │                         respuesta del backend, cada petición HTTP
    │   │                         se manda en un hilo aparte. Incluye una
    │   │                         función lanzar_worker() que usan todas las
    │   │                         pantallas para no pisarse ni destruir un
    │   │                         hilo que sigue trabajando.
    │   └── pdf_report.py         Clase GeneradorReportePDF: arma el PDF de
    │                             la pantalla "Reportes" con reportlab
    │                             (portada, tablas de mediciones/alertas,
    │                             colores según el nivel, pie de página).
    │
    └── ui/
        ├── theme.py              Colores y estilos (modo claro/oscuro). Aquí
        │                         se define la hoja de estilos (QSS, el
        │                         "CSS" de Qt) de toda la app.
        ├── main_window.py        Clase MainWindow: la ventana principal,
        │                         con el menú lateral, la barra de arriba
        │                         (estado de conexión y botón de tema) y el
        │                         contenedor que cambia entre las 5 pantallas.
        ├── flow_layout.py        Clase FlowLayout: acomoda los filtros de
        │                         cada pantalla en varias filas automáticamente
        │                         si no caben en una sola línea (responsive).
        ├── table_utils.py        Funciones y clase ItemOrdenable para que
        │                         las tablas se puedan ordenar dando clic en
        │                         el nombre de cada columna, y que ese orden
        │                         sea real (por fecha, por número, por nivel
        │                         de severidad) y no alfabético.
        ├── dialogs.py             Clase CrearIncidenteDialog: la ventana
        │                         emergente con el formulario para registrar
        │                         un incidente ambiental a mano.
        ├── widgets/
        │   └── gauge_widget.py    Clase GaugeWidget: el "reloj" tipo
        │                         velocímetro de carro que se dibuja a mano
        │                         (con QPainter) para mostrar en vivo un
        │                         valor (ej. temperatura) con aguja, marca
        │                         de zona segura en verde y pantalla digital.
        └── pages/                Una clase por cada pantalla del menú
            ├── dashboard_page.py     Panel Principal.
            ├── historial_page.py     Historial de Mediciones.
            ├── alertas_page.py       Alertas.
            ├── incidentes_page.py    Incidentes Ambientales.
            └── reportes_page.py      Reportes PDF.
```

En resumen: `config`/`state`/`utils` son "servicios de apoyo", `api/` es la única puerta de salida hacia el backend, `services/` hace el trabajo pesado en segundo plano (hilos y PDF), y `ui/` es todo lo que el usuario ve y toca. Cada pantalla (page) recibe el `ApiClient` y el `Catalogos` ya armados desde `MainWindow`, en vez de crear sus propias conexiones — así toda la app comparte un solo cliente HTTP y un solo caché de catálogos.

---

## 4. Endpoints del backend que consume la app y para qué

Todos estos se llaman desde `app/api/client.py` (clase `ApiClient`). El backend completo vive en la carpeta `Backend/` (Punto 1 del taller).

| Método y ruta | Para qué lo usa la app |
|---|---|
| `GET /health` | Revisa si el backend está vivo, para la pastilla de estado de conexión. |
| `GET /api/areas/` | Trae las áreas de la planta (ej. Planta A, Almacén) para llenar los filtros y el combo de "Crear Incidente". |
| `GET /api/parametros-ambientales/` | Trae los parámetros medibles (temperatura, humedad, gas, ruido) con su unidad, para los filtros y los gauges. |
| `GET /api/estados/` | Trae el catálogo de estados usado por otras tablas del sistema. |
| `GET /api/usuarios/` | Trae los usuarios/empleados, para mostrar quién atendió una alerta o es responsable de un incidente. |
| `GET /api/modelos-ia/` | Trae los modelos de IA registrados (catálogo de apoyo para predicciones). |
| `GET /api/predicciones-ia/` | Trae predicciones generadas por el modelo de IA (Punto 4). |
| `GET /api/mantenimientos/` | Trae el historial de mantenimientos de equipos. |
| `GET /api/mediciones/?pagina=&por_pagina=&...` | Trae las mediciones guardadas (temperatura, gas, etc.), con filtros de área, parámetro, calidad del dato y rango de fechas. La usan el Dashboard (últimas mediciones + gauges) y el Historial (tabla paginada). |
| `GET /api/alertas/?...` | Trae las alertas generadas cuando una medición se sale de rango. Las usa el Dashboard (críticas/altas recientes) y la pantalla de Alertas. |
| `PUT /api/alertas/<id>/atender` | Marca una alerta como atendida (con el usuario que la atendió). Botón "Atender seleccionada". |
| `GET /api/incidentes-ambientales/?...` | Trae los incidentes ambientales (más graves que una alerta) para la pantalla de Incidentes. |
| `POST /api/incidentes-ambientales/` | Crea un incidente nuevo a mano, desde el botón "+ Crear Incidente" (área, título, descripción, severidad, causa, responsable, alerta relacionada opcional). |
| `PUT /api/incidentes-ambientales/<id>/resolver` | Cierra un incidente, guardando qué acciones se tomaron para resolverlo. Botón "Resolver seleccionado". |

**Nota:** la app **nunca** crea mediciones (`POST /api/mediciones/`) — eso lo hace el ESP32 (Punto 2), porque las mediciones vienen de un sensor real/simulado, no de una persona escribiéndolas a mano. Lo único que sí puede crear una persona desde la app es un Incidente Ambiental, porque decidir que algo es "grave" y asignarle un responsable requiere criterio humano, no un sensor.

---

## 5. ¿Cómo explicarlo? (guión fácil)

**1. ¿Qué hicimos?**
"Profesor, hicimos una aplicación de escritorio en Python con PySide6 (no tkinter) que consume la API del backend para mostrar en tiempo real todo lo que la planta de Monómeros va midiendo, sin tocar la base de datos directamente."

**2. ¿Cómo está organizada la app por dentro?**
"La separamos en capas: una capa 'api' que es la única que le habla al backend por HTTP, una capa 'services' que corre las peticiones en hilos aparte para que la ventana no se congele y arma los PDF, y una capa 'ui' con una clase por cada pantalla del menú, todo bajo Programación Orientada a Objetos."

**3. ¿Qué muestra cada pantalla?**
"El Panel Principal tiene gráficos tipo velocímetro con los valores en vivo, el Historial deja filtrar y ordenar todas las mediciones con paginación, Alertas y Incidentes dejan atender/resolver casos, y Reportes genera un PDF con lo que se necesite mostrarle a alguien más."

**4. ¿Por qué la app no puede subir mediciones ella misma?**
"Porque las mediciones representan lo que un sensor detectó en la planta; eso lo hace el ESP32 del Punto 2. Lo que sí puede crear una persona desde la app es un incidente ambiental, porque ahí sí se necesita el criterio de alguien para calificar la gravedad y asignar un responsable."

**5. ¿Cómo se conecta con el backend?**
"Con la librería requests, apuntando a la URL que está en el archivo `.env` (`BACKEND_URL`). Si el backend está apagado o falla, la app no se cae: muestra un mensaje de error entendible y sigue funcionando."
