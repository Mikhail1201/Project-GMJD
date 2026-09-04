# API — Project GMJD (Backend)

API REST en Flask para el monitoreo ambiental de Monomeros (temperatura, humedad y
gases). Todas las respuestas son JSON. Base URL local: `http://localhost:5000`.

## Convenciones generales

- **Formato de fecha/hora**: ISO 8601 (`YYYY-MM-DD` para fechas, `YYYY-MM-DDTHH:MM:SS`
  para timestamps). Si un campo de fecha se omite en la creación, el backend usa
  `CURRENT_TIMESTAMP`/`CURRENT_DATE` automáticamente donde aplica.
- **IDs de catálogo** (`id_rol`, `id_estado`): se consultan primero con
  `GET /api/roles/` y `GET /api/estados/` para poblar selects; no hay valores fijos
  entre ambientes.
- **Errores**: siempre devuelven `{"error": "mensaje"}` con el código HTTP
  correspondiente:
  - `400` — datos inválidos o campos faltantes
  - `404` — recurso no encontrado
  - `409` — conflicto de integridad referencial (FK inválida, único duplicado)
  - `502` — falla al comunicarse con Neon Auth (solo en creación de usuarios)
- **Soft delete**: los recursos con ciclo de vida (`usuarios`, `areas`, `alertas`,
  `incidentes_ambientales`, `modelos_ia`, `sensores`) no se borran físicamente; `DELETE`
  cambia su `id_estado` a "Eliminado". Por defecto, los listados excluyen estos
  registros — usar `?incluir_eliminados=true` (o `incluir_eliminadas` en areas/alertas)
  para verlos.
- **Logs append-only**: `mediciones` y `predicciones_ia` no tienen `DELETE`; solo se
  pueden corregir campos secundarios vía `PUT` (nunca los datos crudos del evento).
  `mantenimientos` sigue el mismo criterio.
- **Histórico versionado**: `limites_ambientales` no se borra ni se sobreescribe;
  las versiones se cierran con `fecha_fin` y se reemplazan por una nueva fila.

---

## Roles

### `GET /api/roles/`
Lista todos los roles (catálogo, sin paginación ni filtros).

**Respuesta 200**
```json
[
  { "id_rol": 1, "nombre": "admin" },
  { "id_rol": 2, "nombre": "empleado" }
]
```

---

## Estados

### `GET /api/estados/`
Lista todos los estados (catálogo, sin paginación ni filtros).

**Respuesta 200**
```json
[
  { "id_estado": 1, "nombre": "Activo" },
  { "id_estado": 2, "nombre": "Inactivo" },
  { "id_estado": 3, "nombre": "Eliminado" }
]
```

---

## Usuarios

Creación de cuentas integrada con **Neon Auth**: el backend crea el usuario en
Neon Auth y en la tabla `usuarios` en una sola operación síncrona. No hay
auto-registro; solo un admin crea cuentas.

### `GET /api/usuarios/`
| Query param | Tipo | Default | Descripción |
|---|---|---|---|
| `incluir_eliminados` | bool | `false` | Incluye usuarios con estado "Eliminado" |

**Respuesta 200**
```json
[
  {
    "id_usuario": 1, "nombre": "Ana", "apellido": "Gómez",
    "correo": "ana@ejemplo.com", "id_rol": 2, "id_estado": 1,
    "fecha_registro": "2026-08-20T10:00:00", "auth_user_id": "uuid..."
  }
]
```

### `GET /api/usuarios/<id_usuario>`
**Respuesta 200**: mismo objeto que arriba. **404** si no existe.

### `POST /api/usuarios/`
| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `nombre` | string | sí | |
| `apellido` | string | sí | |
| `correo` | string | sí | único |
| `password` | string | sí | mín. 8 caracteres; la define el admin |
| `id_rol` | int | no | default: rol "empleado" |
| `id_estado` | int | no | default: estado "Activo" |

**Respuesta 201**: usuario creado (mismos campos que `GET`).
**400**: faltan campos. **502**: falló la creación en Neon Auth.
**409**: correo duplicado o `id_rol`/`id_estado` inválido.

### `PUT /api/usuarios/<id_usuario>`
Campos editables: `nombre`, `apellido`, `correo`, `id_rol`, `id_estado`.
**200**: usuario actualizado. **400**: sin campos válidos. **404**: no existe.
**409**: conflicto de integridad.

### `DELETE /api/usuarios/<id_usuario>`
Soft delete (pasa `id_estado` a "Eliminado").
**200**: `{"mensaje": "Usuario desactivado correctamente"}`. **404**: no existe.

---

## Áreas

### `GET /api/areas/`
| Query param | Tipo | Default |
|---|---|---|
| `incluir_eliminadas` | bool | `false` |

### `GET /api/areas/<id_area>`
**404** si no existe.

### `POST /api/areas/`
| Campo | Tipo | Requerido |
|---|---|---|
| `nombre` | string | sí |
| `descripcion` | string | no |
| `ubicacion` | string | no |
| `responsable_id` | int | no (FK a usuarios) |
| `id_estado` | int | no |

**201** / **400** campo faltante / **409** FK inválida.

### `PUT /api/areas/<id_area>`
Campos editables: `nombre`, `descripcion`, `ubicacion`, `responsable_id`, `id_estado`.

### `DELETE /api/areas/<id_area>`
Soft delete.

---

## Sensores

Inventario de los equipos físicos que generan las mediciones. Entidad con ciclo
de vida (soft delete). Cada sensor pertenece a un área y mide un parámetro.

**Sensor principal.** Solo puede haber **un** sensor marcado como principal por
cada combinación `(id_area, id_parametro)` — lo garantiza un índice único parcial
en la base. Es el sensor que el backend asigna automáticamente a las mediciones
que llegan sin `id_sensor` (el caso del ESP32).

### `GET /api/sensores/`
| Query param | Tipo | Descripción |
|---|---|---|
| `id_area` | int | — |
| `id_parametro` | int | — |
| `id_estado` | int | — |
| `responsable_id` | int | — |
| `busqueda` | string | Coincidencia parcial en código, nombre, n.º de serie, modelo o fabricante |
| `solo_principales` | bool | Solo los marcados como principales |
| `calibracion_vencida` | bool | Solo aquellos cuya `fecha_proxima_calibracion` ya pasó |
| `incluir_eliminados` | bool | Incluye los de estado "Eliminado" |

**Respuesta 200** — lista. Además de las columnas de la tabla, cada elemento trae
los campos resueltos por JOIN: `nombre_area`, `nombre_parametro`,
`unidad_parametro`, `nombre_responsable` y `nombre_estado`.

```json
[ { "id_sensor": 3, "codigo": "SEN-A01-NH3",
    "nombre": "Detector de amoniaco - Planta de Amoniaco",
    "id_area": 1, "nombre_area": "Planta de Amoniaco",
    "id_parametro": 3, "nombre_parametro": "Gas Amoniaco (NH3)", "unidad_parametro": "ppm",
    "ubicacion_detalle": "Bloque A - Nivel 1, sobre la linea de sintesis",
    "modelo": "MQ-137", "fabricante": "Winsen", "numero_serie": "WS-MQ137-2201",
    "protocolo": "Analogico", "rango_minimo": "5.0000", "rango_maximo": "500.0000",
    "precision_sensor": "1.0000", "frecuencia_muestreo_seg": 5,
    "fecha_instalacion": "...", "fecha_ultima_calibracion": "...",
    "fecha_proxima_calibracion": "...", "es_principal": true,
    "responsable_id": 5, "nombre_responsable": "test new",
    "id_estado": 1, "nombre_estado": "Activo" } ]
```

### `GET /api/sensores/resolver?id_area=&id_parametro=`
Devuelve el sensor **principal** de esa combinación — el mismo criterio que usa
el backend para completar `mediciones.id_sensor`. Útil para depurar sin tener que
mirar la base. **400** si falta alguno de los dos parámetros; **404** si no hay
principal para esa combinación.

### `GET /api/sensores/<id_sensor>`

### `POST /api/sensores/`
| Campo | Tipo | Requerido |
|---|---|---|
| `codigo` | string | sí (único) |
| `nombre` | string | sí |
| `id_area` | int | sí |
| `id_parametro` | int | sí |
| `descripcion` | string | no |
| `ubicacion_detalle` | string | no |
| `modelo` / `fabricante` | string | no |
| `numero_serie` | string | no (único si se envía) |
| `protocolo` | string | no (lista cerrada, ver abajo) |
| `rango_minimo` / `rango_maximo` | number | no |
| `precision_sensor` | number | no |
| `frecuencia_muestreo_seg` | int | no |
| `fecha_instalacion` | datetime | no (default: ahora) |
| `fecha_ultima_calibracion` / `fecha_proxima_calibracion` | datetime | no |
| `responsable_id` | int | no |
| `id_estado` | int | no (default: "Activo") |

`protocolo` válidos: `1-Wire`, `I2C`, `SPI`, `Analogico`, `4-20 mA`, `Modbus RTU`,
`Modbus TCP`, `RS-232`, `RS-485`, `USB`, `Wi-Fi`.

**400** si falta un requerido, si el protocolo no es válido o si
`rango_minimo > rango_maximo`. **409** si el código o el n.º de serie ya existen,
o si alguna FK es inválida.

El sensor se crea **sin** `es_principal`: para marcarlo hay que llamar al endpoint
dedicado.

### `PUT /api/sensores/<id_sensor>`
Acepta cualquier campo del POST **menos `es_principal`**, que se cambia solo por
`PUT /<id>/principal` (si se pudiera editar aquí sería posible dejar dos sensores
principales de la misma área y parámetro, y la base lo rechazaría con un 409).

### `PUT /api/sensores/<id_sensor>/principal`
Marca el sensor como principal de su área y parámetro, y **quita la marca al
anterior** en la misma transacción. Desde ese momento, las mediciones nuevas de
esa combinación se le atribuyen a este sensor.

### `PUT /api/sensores/<id_sensor>/calibracion`
| Campo | Tipo | Requerido |
|---|---|---|
| `fecha` | datetime | no (default: ahora) |
| `meses_proxima` | int | no (default: 12) |

Registra la calibración y programa la siguiente sumando `meses_proxima`.
**400** si `meses_proxima` no es un entero positivo.

### `DELETE /api/sensores/<id_sensor>`
Soft delete: pasa a estado "Eliminado" y además pierde `es_principal`, para que
un equipo dado de baja deje de capturar las mediciones nuevas.

---

## Parámetros ambientales

Catálogo puro (DELETE real, no soft delete) — pero en la práctica, si un parámetro
ya tiene mediciones asociadas, el DELETE fallará con 409 por la FK desde
`mediciones` (que nunca se borra).

### `GET /api/parametros-ambientales/`
Sin filtros ni paginación.

### `GET /api/parametros-ambientales/<id_parametro>`

### `POST /api/parametros-ambientales/`
| Campo | Tipo | Requerido |
|---|---|---|
| `nombre` | string | sí |
| `unidad` | string | sí |
| `descripcion` | string | no |
| `limite_minimo` | number | no |
| `limite_maximo` | number | no |
| `nivel_riesgo` | string | no |

### `PUT /api/parametros-ambientales/<id_parametro>`
Campos editables: `nombre`, `unidad`, `descripcion`, `limite_minimo`, `limite_maximo`, `nivel_riesgo`.

### `DELETE /api/parametros-ambientales/<id_parametro>`
**200** / **404** / **409** si está en uso por mediciones, límites o predicciones.

---

## Límites ambientales

Histórico versionado: `POST` cierra automáticamente el límite vigente anterior
(misma combinación `id_parametro` + `id_area`) antes de insertar el nuevo,
en una sola transacción atómica.

### `GET /api/limites-ambientales/`
| Query param | Tipo | Default |
|---|---|---|
| `incluir_historico` | bool | `false` — si es `false` solo trae los vigentes (`fecha_fin IS NULL`) |
| `id_area` | int | — |
| `id_parametro` | int | — |

### `GET /api/limites-ambientales/<id_limite>`

### `POST /api/limites-ambientales/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_parametro` | int | sí |
| `id_area` | int | sí |
| `unidad` | string | sí |
| `limite_minimo` | number | uno de los dos requerido |
| `limite_maximo` | number | uno de los dos requerido |
| `fecha_inicio` | date | no (default: hoy) |
| `fuente_normativa` | string | no |

**201** / **400** si faltan campos o ambos límites son nulos / **409** FK inválida.

### `PUT /api/limites-ambientales/<id_limite>`
Solo corrige datos, **no fechas**: `limite_minimo`, `limite_maximo`, `unidad`,
`fuente_normativa`.

### `PUT /api/limites-ambientales/<id_limite>/cerrar`
Da de baja un límite vigente sin reemplazarlo.
| Campo (body opcional) | Tipo |
|---|---|
| `fecha_fin` | date (default: hoy) |

**200** / **404** si no existe o ya estaba cerrado.

*No hay `DELETE`.*

---

## Mediciones

Log append-only, con **paginación** (pensado para alto volumen).

### `GET /api/mediciones/`
| Query param | Tipo | Default |
|---|---|---|
| `pagina` | int | 1 |
| `por_pagina` | int | 50 (máx. 200) |
| `id_area` | int | — |
| `id_parametro` | int | — |
| `calidad_dato` | string | — (`valida` / `sospechosa` / `invalida`) |
| `id_sensor` | int | — |
| `fecha_desde` | datetime | — |
| `fecha_hasta` | datetime | — |

**Respuesta 200**
```json
{
  "datos": [ { "id_medicion": 1, "id_area": 2, "id_parametro": 3, "valor": 24.5,
               "fecha_hora": "...", "calidad_dato": "valida", "observacion": null,
               "id_sensor": 6 } ],
  "paginacion": { "pagina": 1, "por_pagina": 50, "total": 1500, "total_paginas": 30 }
}
```
**400** si `pagina`/`por_pagina` no son enteros.

### `GET /api/mediciones/<id_medicion>`

### `POST /api/mediciones/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_area` | int | sí |
| `id_parametro` | int | sí |
| `valor` | number | sí |
| `fecha_hora` | datetime | no (default: ahora) |
| `calidad_dato` | string | no (default: `valida`) |
| `observacion` | string | no |
| `id_sensor` | int | no (ver abajo) |

**400** si `calidad_dato` no es una de las 3 válidas. **409** FK inválida.

> **`id_sensor` se resuelve solo.** Si el POST no lo trae, el backend busca el
> sensor marcado como *principal* para ese `(id_area, id_parametro)` y lo asigna
> (queda `null` si no hay ninguno). Gracias a esto el ESP32 no necesita saber de
> qué sensor viene la lectura: sigue enviando únicamente área y parámetro.
> Un cliente que sí sepa el sensor puede mandarlo explícito y se respeta.
> Consultable con `GET /api/sensores/resolver?id_area=&id_parametro=`.

### `PUT /api/mediciones/<id_medicion>`
Solo `calidad_dato`, `observacion` o `id_sensor` — nunca `valor`, `fecha_hora`,
`id_area` ni `id_parametro` (el dato crudo del log no se reescribe).

*No hay `DELETE`.*

---

## Alertas

Entidad con ciclo de vida (soft delete) + flujo de atención.

### `GET /api/alertas/`
| Query param | Tipo | Default |
|---|---|---|
| `incluir_eliminadas` | bool | `false` |
| `id_area` | int | — |
| `nivel` | string | — (`bajo`/`medio`/`alto`/`critico`) |
| `solo_sin_atender` | bool | `false` |

Cada alerta incluye `nombre_area` y `nombre_atendio` (JOIN con `areas`/`usuarios`).

### `GET /api/alertas/<id_alerta>`

### `POST /api/alertas/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_medicion` | int | sí |
| `id_area` | int | sí |
| `tipo_alerta` | string | sí |
| `nivel` | string | sí (`bajo`/`medio`/`alto`/`critico`) |
| `descripcion` | string | sí |
| `fecha_hora` | datetime | no (default: ahora) |
| `id_estado` | int | no (default: "Activo") |

### `PUT /api/alertas/<id_alerta>`
Editables: `tipo_alerta`, `nivel`, `descripcion` (no `atendida_por`/`fecha_atencion`).

### `PUT /api/alertas/<id_alerta>/atender`
| Campo | Tipo | Requerido |
|---|---|---|
| `atendida_por` | int (id_usuario) | sí |

Marca `fecha_atencion = CURRENT_TIMESTAMP`. **404** si no existe o **ya estaba atendida**
(no permite reasignar).

### `DELETE /api/alertas/<id_alerta>`
Soft delete.

---

## Incidentes ambientales

Entidad con ciclo de vida (soft delete) + resolución con `fecha_fin` propia
(independiente del `id_estado`). `id_alerta` es opcional.

### `GET /api/incidentes-ambientales/`
| Query param | Tipo | Default |
|---|---|---|
| `incluir_eliminados` | bool | `false` |
| `id_area` | int | — |
| `severidad` | string | — (`baja`/`media`/`alta`/`critica`) |
| `solo_abiertos` | bool | `false` — filtra `fecha_fin IS NULL` |

### `GET /api/incidentes-ambientales/<id_incidente>`

### `POST /api/incidentes-ambientales/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_area` | int | sí |
| `titulo` | string | sí |
| `descripcion` | string | sí |
| `severidad` | string | sí |
| `id_alerta` | int | no |
| `fecha_inicio` | datetime | no (default: ahora) |
| `causa` | string | no |
| `id_estado` | int | no |
| `responsable_id` | int | no |

### `PUT /api/incidentes-ambientales/<id_incidente>`
Editables: `titulo`, `descripcion`, `severidad`, `causa`, `responsable_id`.

### `PUT /api/incidentes-ambientales/<id_incidente>/resolver`
| Campo | Tipo | Requerido |
|---|---|---|
| `acciones_realizadas` | string | sí |

Cierra el incidente (`fecha_fin = CURRENT_TIMESTAMP`). **404** si no existe o ya
estaba resuelto.

### `DELETE /api/incidentes-ambientales/<id_incidente>`
Soft delete.

---

## Mantenimientos

Log append-only.

### `GET /api/mantenimientos/`
| Query param | Tipo |
|---|---|
| `id_area` | int |
| `responsable_id` | int |
| `tipo` | string (`preventivo`/`correctivo`/`predictivo`) |
| `id_sensor` | int |
| `fecha_desde` / `fecha_hasta` | datetime |

### `GET /api/mantenimientos/<id_mantenimiento>`

### `POST /api/mantenimientos/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_area` | int | sí |
| `tipo` | string | sí |
| `descripcion` | string | sí |
| `fecha` | datetime | no (default: ahora) |
| `responsable_id` | int | no |
| `resultado` | string | no |
| `proximo_mantenimiento` | date | no |
| `id_sensor` | int | no |

`id_sensor` es opcional porque un mantenimiento puede ser de un área completa
(barrido general) o de un sensor puntual.

### `PUT /api/mantenimientos/<id_mantenimiento>`
Solo `resultado`, `proximo_mantenimiento`, `descripcion`, `id_sensor`.

*No hay `DELETE`.*

---

## Modelos de IA

Entidad con ciclo de vida (soft delete).

### `GET /api/modelos-ia/`
| Query param | Tipo | Default |
|---|---|---|
| `incluir_eliminados` | bool | `false` |

### `GET /api/modelos-ia/<id_modelo>`

### `POST /api/modelos-ia/`
| Campo | Tipo | Requerido |
|---|---|---|
| `nombre` | string | sí |
| `version` | string | sí |
| `tipo_modelo` | string | sí |
| `descripcion` | string | no |
| `fecha_entrenamiento` | datetime | no |
| `precision_modelo` | number | no |
| `id_estado` | int | no (default: "Activo") |

### `PUT /api/modelos-ia/<id_modelo>`
Editables: todos los campos anteriores.

### `DELETE /api/modelos-ia/<id_modelo>`
Soft delete.

---

## Predicciones de IA

Log append-only, con **paginación**.

### `GET /api/predicciones-ia/`
| Query param | Tipo | Default |
|---|---|---|
| `pagina` | int | 1 |
| `por_pagina` | int | 50 (máx. 200) |
| `id_modelo` | int | — |
| `id_area` | int | — |
| `id_parametro` | int | — |
| `nivel_riesgo` | string | — |
| `fecha_desde` / `fecha_hasta` | datetime | — (filtra sobre `periodo_predicho`) |

Misma forma de respuesta paginada que `mediciones` (`datos` + `paginacion`).

### `GET /api/predicciones-ia/<id_prediccion>`

### `POST /api/predicciones-ia/`
| Campo | Tipo | Requerido |
|---|---|---|
| `id_modelo` | int | sí |
| `id_area` | int | sí |
| `id_parametro` | int | sí |
| `periodo_predicho` | datetime | sí |
| `valor_predicho` | number | sí |
| `nivel_riesgo` | string | sí |
| `fecha_prediccion` | datetime | no (default: ahora) |
| `probabilidad` | number | no |
| `recomendacion` | string | no |

### `PUT /api/predicciones-ia/<id_prediccion>`
Solo `recomendacion`.

*No hay `DELETE`.*

---

## Endpoints auxiliares (no REST de tabla)

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Health check básico ("Hello, World!") |
| `/health` | GET | Verifica conexión a la base de datos, devuelve versión de Postgres |
| `/formulario-usuario` | GET | Formulario HTML de prueba para crear usuarios (admin) |
