import os
import requests

NEON_AUTH_URL = os.getenv("NEON_AUTH_URL")
ADMIN_EMAIL = os.getenv("NEON_AUTH_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("NEON_AUTH_ADMIN_PASSWORD")

# Debe coincidir con un origen registrado como "trusted origin" en Neon
ORIGEN_CONFIABLE = "http://localhost:5000"

_sesion_admin = None


def _obtener_sesion_admin() -> requests.Session:
    global _sesion_admin
    if _sesion_admin is not None:
        return _sesion_admin

    session = requests.Session()
    session.headers.update({"Origin": ORIGEN_CONFIABLE})  # aplica a todas las peticiones de esta sesión

    resp = session.post(
        f"{NEON_AUTH_URL}/sign-in/email",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if not resp.ok:
        raise Exception(f"Login admin falló {resp.status_code}: {resp.text}")

    _sesion_admin = session
    return session


def crear_usuario_auth(email: str, password: str, name: str) -> dict:
    session = _obtener_sesion_admin()
    resp = session.post(
        f"{NEON_AUTH_URL}/admin/create-user",
        json={"email": email, "password": password, "name": name},
        timeout=10,
    )

    if resp.status_code == 401:
        global _sesion_admin
        _sesion_admin = None
        session = _obtener_sesion_admin()
        resp = session.post(
            f"{NEON_AUTH_URL}/admin/create-user",
            json={"email": email, "password": password, "name": name},
            timeout=10,
        )

    if not resp.ok:
        raise Exception(f"{resp.status_code}: {resp.text}")

    data = resp.json()
    return data["user"]