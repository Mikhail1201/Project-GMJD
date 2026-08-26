import os

import requests
from dotenv import load_dotenv

load_dotenv()


class NeonAuthClient:
    ORIGEN_CONFIABLE = "http://localhost:5000"

    def __init__(self, base_url=None, admin_email=None, admin_password=None):
        self.base_url = base_url or os.getenv("NEON_AUTH_URL")
        self.admin_email = admin_email or os.getenv("NEON_AUTH_ADMIN_EMAIL")
        self.admin_password = admin_password or os.getenv("NEON_AUTH_ADMIN_PASSWORD")
        self._sesion_admin = None

    def _obtener_sesion_admin(self) -> requests.Session:
        if self._sesion_admin is not None:
            return self._sesion_admin

        session = requests.Session()
        session.headers.update({"Origin": self.ORIGEN_CONFIABLE})

        resp = session.post(
            f"{self.base_url}/sign-in/email",
            json={"email": self.admin_email, "password": self.admin_password},
            timeout=10,
        )
        if not resp.ok:
            raise Exception(f"Login admin falló {resp.status_code}: {resp.text}")

        self._sesion_admin = session
        return session

    def crear_usuario(self, email: str, password: str, name: str) -> dict:
        session = self._obtener_sesion_admin()
        resp = session.post(
            f"{self.base_url}/admin/create-user",
            json={"email": email, "password": password, "name": name},
            timeout=10,
        )

        if resp.status_code == 401:
            self._sesion_admin = None
            session = self._obtener_sesion_admin()
            resp = session.post(
                f"{self.base_url}/admin/create-user",
                json={"email": email, "password": password, "name": name},
                timeout=10,
            )

        if not resp.ok:
            raise Exception(f"{resp.status_code}: {resp.text}")

        return resp.json()["user"]


cliente_auth = NeonAuthClient()
