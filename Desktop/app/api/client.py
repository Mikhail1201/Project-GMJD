import re
from datetime import datetime
from html import unescape
from pathlib import Path

import requests

from app.api.exceptions import ApiError
from app.config import BACKEND_URL, TIMEOUT_SEGUNDOS

ARCHIVO_ERRORES_BACKEND = Path(__file__).resolve().parents[2] / "errores_backend.log"


class ApiClient:
    """Cliente HTTP para el backend Flask/PostgreSQL (Neon) del proyecto Monomeros."""

    def __init__(self, base_url: str = BACKEND_URL, timeout: int = TIMEOUT_SEGUNDOS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _request(self, metodo: str, ruta: str, **kwargs):
        url = f"{self.base_url}{ruta}"
        try:
            resp = self._session.request(metodo, url, timeout=self.timeout, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            raise ApiError(f"No se pudo conectar con el backend en {self.base_url}") from exc
        except requests.exceptions.Timeout as exc:
            raise ApiError("El backend tardo demasiado en responder") from exc

        if not resp.ok:
            raise ApiError(_extraer_mensaje_error(url, resp), status_code=resp.status_code)

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # --- Salud -----------------------------------------------------------
    def salud(self) -> dict:
        return self._request("GET", "/health")

    # --- Catalogos ---------------------------------------------------------
    def listar_areas(self) -> list[dict]:
        return self._request("GET", "/api/areas/")

    def listar_parametros(self) -> list[dict]:
        return self._request("GET", "/api/parametros-ambientales/")

    def listar_estados(self) -> list[dict]:
        return self._request("GET", "/api/estados/")

    def listar_usuarios(self) -> list[dict]:
        return self._request("GET", "/api/usuarios/")

    def listar_modelos_ia(self) -> list[dict]:
        return self._request("GET", "/api/modelos-ia/")

    def listar_predicciones_ia(self, **filtros) -> dict:
        return self._request("GET", "/api/predicciones-ia/", params=_limpiar(filtros))

    def listar_mantenimientos(self, **filtros) -> list[dict]:
        return self._request("GET", "/api/mantenimientos/", params=_limpiar(filtros))

    # --- Sensores --------------------------------------------------------
    def listar_sensores(self, **filtros) -> list[dict]:
        return self._request("GET", "/api/sensores/", params=_limpiar(filtros))

    def obtener_sensor(self, id_sensor: int) -> dict:
        return self._request("GET", f"/api/sensores/{id_sensor}")

    def crear_sensor(
        self,
        codigo: str,
        nombre: str,
        id_area: int,
        id_parametro: int,
        descripcion: str | None = None,
        ubicacion_detalle: str | None = None,
        modelo: str | None = None,
        fabricante: str | None = None,
        numero_serie: str | None = None,
        protocolo: str | None = None,
        rango_minimo: float | None = None,
        rango_maximo: float | None = None,
        frecuencia_muestreo_seg: int | None = None,
        responsable_id: int | None = None,
    ) -> dict:
        payload = _limpiar({
            "codigo": codigo,
            "nombre": nombre,
            "id_area": id_area,
            "id_parametro": id_parametro,
            "descripcion": descripcion,
            "ubicacion_detalle": ubicacion_detalle,
            "modelo": modelo,
            "fabricante": fabricante,
            "numero_serie": numero_serie,
            "protocolo": protocolo,
            "rango_minimo": rango_minimo,
            "rango_maximo": rango_maximo,
            "frecuencia_muestreo_seg": frecuencia_muestreo_seg,
            "responsable_id": responsable_id,
        })
        return self._request("POST", "/api/sensores/", json=payload)

    def actualizar_sensor(self, id_sensor: int, **campos) -> dict:
        return self._request("PUT", f"/api/sensores/{id_sensor}", json=_limpiar(campos))

    def marcar_sensor_principal(self, id_sensor: int) -> dict:
        return self._request("PUT", f"/api/sensores/{id_sensor}/principal")

    def registrar_calibracion_sensor(self, id_sensor: int, meses_proxima: int = 12) -> dict:
        return self._request(
            "PUT",
            f"/api/sensores/{id_sensor}/calibracion",
            json={"meses_proxima": meses_proxima},
        )

    def eliminar_sensor(self, id_sensor: int) -> dict:
        return self._request("DELETE", f"/api/sensores/{id_sensor}")

    # --- Mediciones ----------------------------------------------------
    def listar_mediciones(self, pagina: int = 1, por_pagina: int = 50, **filtros) -> dict:
        params = _limpiar(filtros)
        params["pagina"] = pagina
        params["por_pagina"] = por_pagina
        return self._request("GET", "/api/mediciones/", params=params)

    # --- Alertas ---------------------------------------------------------
    def listar_alertas(self, **filtros) -> list[dict]:
        return self._request("GET", "/api/alertas/", params=_limpiar(filtros))

    def atender_alerta(self, id_alerta: int, atendida_por: int) -> dict:
        return self._request(
            "PUT", f"/api/alertas/{id_alerta}/atender", json={"atendida_por": atendida_por}
        )

    # --- Incidentes ambientales -----------------------------------------
    def listar_incidentes(self, **filtros) -> list[dict]:
        return self._request("GET", "/api/incidentes-ambientales/", params=_limpiar(filtros))

    def crear_incidente(
        self,
        id_area: int,
        titulo: str,
        descripcion: str,
        severidad: str,
        id_alerta: int | None = None,
        causa: str | None = None,
        responsable_id: int | None = None,
    ) -> dict:
        payload = _limpiar({
            "id_area": id_area,
            "titulo": titulo,
            "descripcion": descripcion,
            "severidad": severidad,
            "id_alerta": id_alerta,
            "causa": causa,
            "responsable_id": responsable_id,
        })
        return self._request("POST", "/api/incidentes-ambientales/", json=payload)

    def resolver_incidente(self, id_incidente: int, acciones_realizadas: str) -> dict:
        return self._request(
            "PUT",
            f"/api/incidentes-ambientales/{id_incidente}/resolver",
            json={"acciones_realizadas": acciones_realizadas},
        )


def _limpiar(filtros: dict) -> dict:
    """Quita del diccionario los valores None/'' para no ensuciar el query string."""
    return {k: v for k, v in filtros.items() if v not in (None, "")}


def _extraer_mensaje_error(url: str, resp: requests.Response) -> str:
    """Convierte la respuesta de error del backend en un mensaje corto y
    legible para mostrar en la UI.

    Cuando Flask corre en modo debug y algo revienta (ej. se cae la
    conexion a Neon), devuelve una pagina HTML entera con el traceback en
    vez de JSON — sin este manejo, esa pagina completa se mostraba tal
    cual en pantalla. Aqui se detecta ese caso, se saca solo el tipo de
    excepcion y el mensaje, y el HTML completo se guarda en
    errores_backend.log para poder diagnosticar despues sin ensuciar la
    interfaz."""
    texto = resp.text or ""

    try:
        datos = resp.json()
        if isinstance(datos, dict) and "error" in datos:
            return str(datos["error"])
    except ValueError:
        pass

    texto_normalizado = texto.strip().lower()
    if texto_normalizado.startswith("<!doctype") or texto_normalizado.startswith("<html"):
        resumen = _resumir_error_html(texto, resp.status_code)
        _registrar_error_backend(url, resp.status_code, texto)
        return resumen

    if texto.strip():
        return texto.strip()[:300]
    return f"Error HTTP {resp.status_code} en el backend"


def _resumir_error_html(html: str, status_code: int) -> str:
    tipo = re.search(r"<h1>(.*?)</h1>", html, re.DOTALL)
    detalle = re.search(r'<p class="errormsg">(.*?)</p>', html, re.DOTALL)

    tipo_texto = unescape(tipo.group(1)).strip() if tipo else ""
    detalle_texto = re.sub(r"\s+", " ", unescape(detalle.group(1))).strip() if detalle else ""

    # El mensaje de detalle de SQLAlchemy/Werkzeug ya suele empezar con el
    # mismo nombre de excepcion del <h1>, asi que mostrar ambos duplicaria
    # el texto. Preferimos el detalle (mas informativo) y solo agregamos
    # el tipo por separado si no viene incluido ahi.
    if detalle_texto:
        if tipo_texto and not detalle_texto.startswith(tipo_texto.split(":")[0]):
            return f"{tipo_texto}: {detalle_texto[:220]}"
        return detalle_texto[:250]
    if tipo_texto:
        return tipo_texto
    return f"Error interno del servidor (HTTP {status_code}). Ver errores_backend.log para el detalle."


def _registrar_error_backend(url: str, status_code: int, html: str):
    try:
        with open(ARCHIVO_ERRORES_BACKEND, "a", encoding="utf-8") as f:
            f.write(
                f"\n--- {datetime.now().isoformat()} | {status_code} | {url} ---\n"
                f"{html[:8000]}\n"
            )
    except OSError:
        pass
