import logging

from flask import Flask, jsonify, render_template
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from app.core.database import engine
from app.api import (
    usuarios_bp, roles_bp, estados_bp, areas_bp, parametros_bp,
    limites_bp, mediciones_bp, alertas_bp, incidentes_bp,
    mantenimientos_bp, modelos_ia_bp, predicciones_bp, sensores_bp,
)


def create_app() -> Flask:
    app = Flask(__name__)

    # Sin esto, con debug=True cualquier excepcion no controlada (ej. se
    # cae la conexion a Neon) devuelve la pagina HTML interactiva del
    # depurador de Werkzeug en vez de un error JSON. Eso rompe a cualquier
    # cliente que espere JSON (la app de escritorio terminaba mostrando
    # el HTML crudo en pantalla). El traceback completo se sigue viendo
    # en la consola donde corre el backend (app.logger.exception abajo).
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.errorhandler(Exception)
    def manejar_error_no_controlado(error):
        # Los errores HTTP normales (404, 405, 400 por abort(), etc.) deben
        # conservar su codigo real; solo las excepciones genuinamente no
        # controladas (crash real, ej. se cae la conexion a Neon) caen
        # como 500 con el tipo y mensaje de la excepcion.
        if isinstance(error, HTTPException):
            return jsonify({"error": error.description}), error.code

        app.logger.exception("Excepcion no controlada en %s", error)
        return jsonify({
            "error": f"{type(error).__name__}: {error}",
        }), 500

    app.register_blueprint(usuarios_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(estados_bp)
    app.register_blueprint(areas_bp)
    app.register_blueprint(parametros_bp)
    app.register_blueprint(limites_bp)
    app.register_blueprint(mediciones_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(incidentes_bp)
    app.register_blueprint(mantenimientos_bp)
    app.register_blueprint(modelos_ia_bp)
    app.register_blueprint(predicciones_bp)
    app.register_blueprint(sensores_bp)

    @app.get('/')
    def home():
        return 'Hello, World!'

    @app.get('/formulario-usuario')
    def formulario_usuario():
        return render_template('formulario_usuario.html')

    @app.get('/health')
    def health():
        with engine.connect() as con:
            version = con.execute(text("SELECT version();")).scalar()
        return jsonify({"status": "ok", "database": version}), 200

    return app
