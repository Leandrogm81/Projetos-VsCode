from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps

# Configurar logging básico
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        print("Verificando token de autenticação...")
        logger.info("Iniciando verificação de token")
        token = None
        
        # Verificar se o token está no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            print(f"Header Authorization encontrado: {auth_header}")
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
                print(f"Token extraído: {token[:20]}...")  # Log parcial por segurança
            except IndexError:
                print("Formato de token inválido!")
                logger.warning("Formato de Authorization inválido")
                return jsonify({'message': 'Formato de token inválido! Use: Bearer <token>'}), 401
        else:
            print("Nenhum header Authorization encontrado")
            logger.warning("Requisição sem token de autenticação")
        
        if not token:
            print("Token ausente - retornando 401")
            logger.warning("Token de acesso obrigatório não fornecido")
            return jsonify({'message': 'Token de acesso é obrigatório!'}), 401
        
        try:
            # Decodificar o token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'username': data['username'],
                'role': data['role'],
                'name': data['name']
            }
            print(f"Token válido! Usuário: {current_user['username']}, Role: {current_user['role']}")
            logger.info(f"Autenticação bem-sucedida para {current_user['username']}")
        except jwt.ExpiredSignatureError:
            print("Token expirado!")
            logger.warning("Token JWT expirado")
            return jsonify({'message': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            print("Token inválido!")
            logger.error("Token JWT inválido")
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