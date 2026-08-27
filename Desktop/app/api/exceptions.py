class ApiError(Exception):
    def __init__(self, mensaje: str, status_code: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status_code = status_code
