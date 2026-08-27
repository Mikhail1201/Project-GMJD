import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.main_window import MainWindow

ARCHIVO_ERRORES = Path(__file__).parent / "errores.log"


def _manejar_excepcion_no_capturada(tipo, valor, tb):
    """Si algo inesperado revienta fuera de un try/except, lo dejamos
    registrado en errores.log y avisamos con un dialogo, en vez de que la
    app se cierre en silencio sin ninguna pista de que paso."""
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    try:
        with open(ARCHIVO_ERRORES, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now().isoformat()} ---\n{texto}")
    except OSError:
        pass

    print(texto, file=sys.stderr)

    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(
            None,
            "Error inesperado",
            "Ocurrió un error inesperado y se guardó el detalle en errores.log.\n\n"
            f"{tipo.__name__}: {valor}",
        )


def main():
    sys.excepthook = _manejar_excepcion_no_capturada

    app = QApplication(sys.argv)

    # MainWindow aplica el tema (claro/oscuro) guardado por el usuario
    # en su __init__, antes de construir el resto de la interfaz.
    ventana = MainWindow()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
