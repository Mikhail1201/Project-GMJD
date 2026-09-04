class Catalogos:
    """Cache en memoria de los catalogos base (areas, parametros, usuarios y
    sensores) para evitar pedirlos a la API cada vez que una pantalla necesita
    mostrar un nombre."""

    def __init__(self):
        self.areas: list[dict] = []
        self.parametros: list[dict] = []
        self.usuarios: list[dict] = []
        self.sensores: list[dict] = []

    def cargar(self, areas: list[dict], parametros: list[dict], usuarios: list[dict],
               sensores: list[dict] | None = None):
        # sensores va con default para no romper a quien llame con 3 argumentos
        # y para que la app siga arrancando si ese endpoint falla.
        self.areas = areas or []
        self.parametros = parametros or []
        self.usuarios = usuarios or []
        self.sensores = sensores or []

    def nombre_area(self, id_area) -> str:
        return next((a["nombre"] for a in self.areas if a["id_area"] == id_area), f"Área {id_area}")

    def nombre_parametro(self, id_parametro) -> str:
        return next(
            (p["nombre"] for p in self.parametros if p["id_parametro"] == id_parametro),
            f"Parámetro {id_parametro}",
        )

    def unidad_parametro(self, id_parametro) -> str:
        return next((p["unidad"] for p in self.parametros if p["id_parametro"] == id_parametro), "")

    def nombre_sensor(self, id_sensor) -> str:
        if id_sensor is None:
            return "Sin sensor"
        return next(
            (s["codigo"] for s in self.sensores if s["id_sensor"] == id_sensor),
            f"Sensor {id_sensor}",
        )

    def sensores_de_area(self, id_area) -> list[dict]:
        return [s for s in self.sensores if s["id_area"] == id_area]

    def nombre_usuario(self, id_usuario) -> str:
        for u in self.usuarios:
            if u["id_usuario"] == id_usuario:
                return f"{u['nombre']} {u['apellido']}"
        return f"Usuario {id_usuario}"
