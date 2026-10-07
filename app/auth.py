"""Contraseñas derivadas con scrypt y sesiones locales con caducidad."""
import hashlib
import hmac
import secrets
import threading
import time
from .repository import RecursoMySQLRepository


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1)
    return 'scrypt$' + salt.hex() + '$' + digest.hex()


def verify_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        result = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(result.hex(), expected)
    except (ValueError, TypeError):
        return False


class UsuarioRepository(RecursoMySQLRepository):
    def crear_usuario(self, username, password):
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute('INSERT INTO usuario_sistema (nombreUsuario,contrasenaHash) VALUES (%s,%s)',
                           (username, password_hash(password)))

    def obtener(self, username):
        with self.connection() as conn, conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM usuario_sistema WHERE nombreUsuario=%s', (username,))
            return cursor.fetchone()


class AuthService:
    def __init__(self, repository):
        self.repository = repository
        self.sessions = {}
        self.attempts = {}
        self.lock = threading.Lock()
        self.dummy_hash = password_hash(secrets.token_hex(16))

    def login(self, username, password, address):
        now = time.monotonic()
        with self.lock:
            attempts = [t for t in self.attempts.get(address, []) if now-t < 60]
            if len(attempts) >= 5:
                raise PermissionError('Demasiados intentos. Espera un minuto antes de volver a intentar.')
            self.attempts[address] = attempts + [now]
        user = self.repository.obtener(username)
        valid = verify_password(password, user['contrasenaHash'] if user else self.dummy_hash)
        if not user or not valid or not user['activo']:
            return None
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.attempts.pop(address, None)
            self.sessions = {k:v for k,v in self.sessions.items() if v['expires'] > now}
            self.sessions[token] = {'username': user['nombreUsuario'], 'expires': now + 8*3600}
        return token

    def session(self, token):
        with self.lock:
            item = self.sessions.get(token)
            if item and item['expires'] > time.monotonic():
                return item['username']
            self.sessions.pop(token, None)
            return None

    def logout(self, token):
        with self.lock:
            self.sessions.pop(token, None)
