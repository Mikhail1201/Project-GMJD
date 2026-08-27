class Catalogos:
    """Cache en memoria de los catalogos base (areas, parametros, usuarios) para
    evitar pedirlos a la API cada vez que una pantalla necesita mostrar un nombre."""

    def __init__(self):
        self.areas: list[dict] = []
        self.parametros: list[dict] = []
        self.usuarios: list[dict] = []

    def cargar(self, areas: list[dict], parametros: list[dict], usuarios: list[dict]):
        self.areas = areas or []
        self.parametros = parametros or []
        self.usuarios = usuarios or []

    def nombre_area(self, id_area) -> str:
        return next((a["nombre"] for a in self.areas if a["id_area"] == id_area), f"Área {id_area}")

    def nombre_parametro(self, id_parametro) -> str:
        return next(
            (p["nombre"] for p in self.parametros if p["id_parametro"] == id_parametro),
            f"Parámetro {id_parametro}",
        )

    def unidad_parametro(self, id_parametro) -> str:
        return next((p["unidad"] for p in self.parametros if p["id_parametro"] == id_parametro), "")

    def nombre_usuario(self, id_usuario) -> str:
        for u in self.usuarios:
            if u["id_usuario"] == id_usuario:
                return f"{u['nombre']} {u['apellido']}"
        return f"Usuario {id_usuario}"
