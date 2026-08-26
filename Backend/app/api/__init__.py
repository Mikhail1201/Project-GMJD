from app.api.rutas_usuarios import usuarios_bp
from app.api.rutas_roles import roles_bp
from app.api.rutas_estados import estados_bp
from app.api.rutas_areas import areas_bp
from app.api.rutas_parametros_ambientales import parametros_bp
from app.api.rutas_limites_ambientales import limites_bp
from app.api.rutas_mediciones import mediciones_bp
from app.api.rutas_alertas import alertas_bp
from app.api.rutas_incidentes_ambientales import incidentes_bp
from app.api.rutas_mantenimientos import mantenimientos_bp
from app.api.rutas_modelos_ia import modelos_ia_bp
from app.api.rutas_predicciones_ia import predicciones_bp

__all__ = [
    "usuarios_bp", "roles_bp", "estados_bp", "areas_bp", "parametros_bp",
    "limites_bp", "mediciones_bp", "alertas_bp", "incidentes_bp",
    "mantenimientos_bp", "modelos_ia_bp", "predicciones_bp",
]
