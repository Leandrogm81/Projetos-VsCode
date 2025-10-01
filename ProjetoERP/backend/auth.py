from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps

# Simple in-memory user store for demo (use database in production)
users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'role': 'admin',
        'name': 'Administrador'
    },
    'vendedor': {
        'password': generate_password_hash('vendedor123'),
        'role': 'vendedor',
        'name': 'Usuário Vendedor'
    },
    'tecnico': {
        'password': generate_password_hash('tecnico123'),
        'role': 'tecnico',
        'name': 'Técnico Instalador'
    }
}

def authenticate_user(username, password):
    """Autentica um usuário com nome de usuário e senha"""
    if username in users and check_password_hash(users[username]['password'], password):
        return users[username]
    return None

def generate_token(user_data):
    """Gera um token JWT para o usuário"""
    payload = {
        'username': user_data['username'],
        'role': user_data['role'],
        'name': user_data['name'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    """Decorator para exigir token JWT válido"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Verificar se o token está no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'message': 'Formato de token inválido! Use: Bearer <token>'}), 401
        
        if not token:
            return jsonify({'message': 'Token de acesso é obrigatório!'}), 401
        
        try:
            # Decodificar o token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'username': data['username'],
                'role': data['role'],
                'name': data['name']
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def role_required(role):
    """Decorator para exigir role específica"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obter usuário do token (já verificado por token_required)
            current_user = kwargs.get('current_user') or args[0] if args else None
            
            if not current_user or current_user['role'] != role:
                return jsonify({'message': 'Acesso negado! Permissões insuficientes.'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator