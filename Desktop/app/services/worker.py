import weakref
from typing import Callable

from PySide6.QtCore import QThread, Signal

from app.api.exceptions import ApiError


class ApiWorker(QThread):
    """Ejecuta una llamada bloqueante (requests) en un hilo aparte para no congelar la UI."""

    exito = Signal(object)
    error = Signal(str)

    _instancias: "weakref.WeakSet[ApiWorker]" = weakref.WeakSet()

    def __init__(self, funcion: Callable, *args, **kwargs):
        super().__init__()
        self._funcion = funcion
        self._args = args
        self._kwargs = kwargs
        # Espera a que el hilo termine de verdad antes de que Python pueda
        # recolectarlo; sin esto Qt a veces avisa "QThread: Destroyed while
        # thread is still running" por una carrera entre la señal finished
        # y el cierre real del hilo del sistema operativo.
        self.finished.connect(self.wait)
        ApiWorker._instancias.add(self)

    def run(self):
        try:
            resultado = self._funcion(*self._args, **self._kwargs)
        except ApiError as exc:
            self.error.emit(exc.mensaje)
        except Exception as exc:  # noqa: BLE001 - se reporta cualquier fallo inesperado a la UI
            self.error.emit(str(exc))
        else:
            self.exito.emit(resultado)

    @classmethod
    def esperar_todos(cls, timeout_ms: int = 3000):
        """Espera (con limite) a que terminen los workers que sigan vivos.

        Se llama al cerrar la ventana: si el usuario cierra la app mientras
        alguna peticion de red sigue en curso, esto evita que Qt destruya un
        QThread todavia corriendo (el warning 'QThread: Destroyed while
        thread is still running')."""
        for worker in list(cls._instancias):
            if worker.isRunning():
                worker.wait(timeout_ms)


def lanzar_worker(
    contenedor: list["ApiWorker"],
    funcion: Callable,
    on_exito: Callable,
    on_error: Callable,
    *args,
    **kwargs,
) -> "ApiWorker":
    """Crea y arranca un ApiWorker, guardandolo en `contenedor` (una lista
    que le pertenece a la pantalla que lo lanza) hasta que termine de
    verdad. Usar SIEMPRE una lista (nunca reasignar un solo atributo tipo
    `self._worker = ApiWorker(...)`): si el usuario cambia de pestaña o
    pagina rapido mientras la peticion anterior sigue en curso, reasignar
    el atributo suelta la referencia al hilo viejo TODAVIA CORRIENDO, y
    Python lo destruye a la fuerza -> crash real, no solo un warning."""
    worker = ApiWorker(funcion, *args, **kwargs)
    worker.exito.connect(on_exito)
    worker.error.connect(on_error)
    worker.finished.connect(lambda: contenedor.remove(worker) if worker in contenedor else None)
    contenedor.append(worker)
    worker.start()
    return worker
