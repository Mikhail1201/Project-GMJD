from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.core.auth import cliente_auth
from app.models.usuario import Usuario
from app.repositories.usuario_repo import UsuarioRepository

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')
repo = UsuarioRepository()


@usuarios_bp.get('/')
def listar_usuarios():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'
    return jsonify([u.a_dict() for u in repo.listar(incluir_eliminados)]), 200


@usuarios_bp.get('/<int:id_usuario>')
def obtener_usuario(id_usuario):
    usuario = repo.obtener(id_usuario)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.a_dict()), 200


@usuarios_bp.post('/')
def crear_usuario():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "apellido", "correo"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if not data.get("password"):
        return jsonify({"error": "El campo 'password' es requerido"}), 400

    nombre_completo = f"{data['nombre']} {data['apellido']}"

    try:
        usuario_auth = cliente_auth.crear_usuario(
            email=data["correo"],
            password=data["password"],
            name=nombre_completo,
        )
    except Exception as e:
        return jsonify({"error": f"No se pudo crear el usuario en Neon Auth: {e}"}), 502

    usuario = Usuario(
        nombre=data["nombre"],
        apellido=data["apellido"],
        correo=data["correo"],
        id_rol=data.get("id_rol"),
        id_estado=data.get("id_estado"),
    )

    try:
        nuevo = repo.crear(usuario, auth_user_id=usuario_auth["id"])
    except IntegrityError:
        return jsonify({"error": "Correo ya registrado o rol/estado inválido"}), 409

    return jsonify(nuevo.a_dict()), 201


@usuarios_bp.put('/<int:id_usuario>')
def actualizar_usuario(id_usuario):
    data = request.get_json(silent=True) or {}

    try:
        usuario = repo.actualizar(id_usuario, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "Correo ya registrado o rol/estado inválido"}), 409

    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify(usuario.a_dict()), 200


@usuarios_bp.delete('/<int:id_usuario>')
def eliminar_usuario(id_usuario):
    if not repo.eliminar(id_usuario):
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({"mensaje": "Usuario desactivado correctamente"}), 200
