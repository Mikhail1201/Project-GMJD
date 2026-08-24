from flask import Flask
from sqlalchemy import text

from extensions import engine
from api.usuarios.routes import usuarios_bp
from api.areas.routes import areas_bp

# --- verificación rápida de conexión (opcional, solo para debug al arrancar) ---
with engine.connect() as con:
    result = con.execute(text("SELECT version();"))
    print(result.scalar())

app = Flask(__name__)

# --- registro de blueprints ---
app.register_blueprint(usuarios_bp)
app.register_blueprint(areas_bp)

@app.get('/')
def home():
    return 'Hello, World!'


if __name__ == '__main__':
    app.run(debug=True)