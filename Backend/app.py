from flask import Flask, render_template
from sqlalchemy import text

from extensions import engine
from api.usuarios.routes import usuarios_bp
from api.areas.routes import areas_bp
from api.estados.routes import estados_bp
from api.roles.routes import roles_bp
from api.mediciones.routes import mediciones_bp
from api.parametros_ambientales.routes import parametros_bp
from api.limites_ambientales.routes import limites_bp
from api.mediciones.routes import mediciones_bp
from api.modelos_ia.routes import modelos_ia_bp

# --- verificación rápida de conexión (opcional, solo para debug al arrancar) ---
with engine.connect() as con:
    result = con.execute(text("SELECT version();"))
    print(result.scalar())

app = Flask(__name__)

# --- registro de blueprints ---
app.register_blueprint(usuarios_bp)
app.register_blueprint(areas_bp)
app.register_blueprint(estados_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(mediciones_bp)
app.register_blueprint(parametros_bp)
app.register_blueprint(limites_bp)
app.register_blueprint(mediciones_bp)
app.register_blueprint(modelos_ia_bp)

@app.get('/')
def home():
    return 'Hello, World!'

@app.get('/formulario-usuario')
def formulario_usuario():
    return render_template('formulario_usuario.html')

if __name__ == '__main__':
    app.run(debug=True)