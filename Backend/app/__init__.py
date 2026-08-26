from flask import Flask, jsonify, render_template
from sqlalchemy import text

from app.core.database import engine
from app.api import (
    usuarios_bp, roles_bp, estados_bp, areas_bp, parametros_bp,
    limites_bp, mediciones_bp, alertas_bp, incidentes_bp,
    mantenimientos_bp, modelos_ia_bp, predicciones_bp,
)


def create_app() -> Flask:
    app = Flask(__name__)

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
