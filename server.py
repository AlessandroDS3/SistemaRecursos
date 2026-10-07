"""Servidor local de desarrollo con persistencia MySQL."""
import argparse
import json
import logging
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import urlsplit

from app.domain import TipoRecurso, EstadoBienMaterial, ValidationError
from app.repository import RecursoMySQLRepository
from app.config import load_config
import mysql.connector
from app.service import GestionRecursosService, ConflictError
from app.personas import GestionPersonasService
from app.persona_repository import PersonaMySQLRepository
from app.auth import AuthService, UsuarioRepository

BASE = Path(__file__).resolve().parent


def make_server(database, port=8000):
    repository = RecursoMySQLRepository(database)
    repository.initialize()
    service = GestionRecursosService(repository)
    personas = PersonaMySQLRepository(database)
    personas_service = GestionPersonasService(personas)
    auth = AuthService(UsuarioRepository(database))

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value, mime="application/json; charset=utf-8", cookie=None):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def token(self):
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get('Cookie', ''))
                return cookies['recurso_session'].value if 'recurso_session' in cookies else ''
            except CookieError:
                return ''

        def redirect_login(self):
            self.send_response(303)
            self.send_header('Location', '/login')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_GET(self):
            path = urlsplit(self.path).path
            username = auth.session(self.token())
            if path not in ('/login', '/static/js/login.js', '/static/css/styles.css', '/static/img/logo-escuela.png') and not username:
                if path.startswith('/api/'):
                    return self.reply(401, {'error': 'Inicia sesión para continuar.'})
                return self.redirect_login()
            if path == '/api/sesion':
                return self.reply(200, {'usuario': username})
            if path == '/api/personas':
                try:
                    return self.reply(200, {'personas': personas.listar_personas()})
                except mysql.connector.Error:
                    return self.reply(503, {'error': 'No se pudo consultar MySQL. Revisa la conexión.'})
            if path == "/api/catalogo":
                try:
                    return self.reply(200, {"recursos": repository.listar(), "categorias": repository.categorias(),
                        "tipos": [t.value for t in TipoRecurso], "estados": [e.value for e in EstadoBienMaterial]})
                except mysql.connector.Error:
                    return self.reply(503, {"error": "MySQL no está disponible. Revisa la conexión."})
            files = {
                '/': ('templates/index.html', 'text/html'),
                '/personas': ('templates/personas.html', 'text/html'),
                '/login': ('templates/login.html', 'text/html'),
                '/static/js/app.js': ('static/js/app.js', 'text/javascript'),
                '/static/js/login.js': ('static/js/login.js', 'text/javascript'),
                '/static/img/logo-escuela.png': ('static/img/logo-escuela.png', 'image/png'),
                '/static/js/personas.js': ('static/js/personas.js', 'text/javascript'),
                '/static/js/session.js': ('static/js/session.js', 'text/javascript'),
                '/static/css/styles.css': ('static/css/styles.css', 'text/css'),
            }
            if path in files:
                name, mime = files[path]
                return self.reply(200, (BASE / name).read_bytes(), mime + "; charset=utf-8" if mime.startswith("text/") else mime)
            return self.reply(404, {"error": "Ruta no encontrada."})

        def do_POST(self):
            # El frontend usa JSON y mismo origen; no se habilita CORS.
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            allowed = {expected_origin, f"http://localhost:{self.server.server_port}"}
            if self.headers.get("Origin") and self.headers["Origin"] not in allowed:
                return self.reply(403, {"error": "Origen no permitido."})
            if self.headers.get_content_type() != "application/json":
                return self.reply(415, {"error": "Se requiere application/json."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16384:
                    return self.reply(413, {"error": "El cuerpo debe tener entre 1 y 16384 bytes."})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValidationError("Se requiere un objeto JSON.")
                path = urlsplit(self.path).path
                if path == '/api/login':
                    username, password = data.get('usuario'), data.get('contrasena')
                    if not isinstance(username, str) or not isinstance(password, str) or not 1 <= len(username) <= 80 or not 1 <= len(password) <= 128:
                        return self.reply(400, {'error': 'Completa el usuario y la contraseña.'})
                    try:
                        token = auth.login(username.strip(), password, self.client_address[0])
                    except PermissionError as exc:
                        return self.reply(429, {'error': str(exc)})
                    if not token:
                        return self.reply(401, {'error': 'Usuario o contraseña incorrectos.'})
                    auth.logout(self.token())
                    return self.reply(200, {'ok': True}, cookie=f'recurso_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800')
                if not auth.session(self.token()):
                    return self.reply(401, {'error': 'Inicia sesión para continuar.'})
                if path == '/api/logout':
                    auth.logout(self.token())
                    return self.reply(200, {'ok': True}, cookie='recurso_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
                if path == '/api/personas':
                    return self.reply(201, {'idPersona': personas_service.registrar(data)})
                if path == "/api/recursos":
                    return self.reply(201, {"idRecurso": service.registrar(data)})
                match = re.fullmatch(r"/api/recursos/([1-9][0-9]*)/bienes", path)
                if match:
                    return self.reply(201, {"idBien": service.agregar_bien(int(match[1]), data)})
                return self.reply(404, {"error": "Ruta no encontrada."})
            except (ValidationError, ValueError, UnicodeDecodeError) as exc:
                return self.reply(409 if isinstance(exc, ConflictError) else 400, {"error": str(exc)})
            except LookupError as exc:
                return self.reply(404, {"error": str(exc)})
            except Exception:
                logging.exception("Error al guardar")
                return self.reply(500, {"error": "No se pudo guardar. Intenta de nuevo."})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Catálogo local de recursos · MySQL")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--config", type=Path, default=BASE / "config.ini")
    args = parser.parse_args()
    try:
        server = make_server(load_config(args.config), args.port)
    except (ValueError, mysql.connector.Error) as exc:
        raise SystemExit(f"No se pudo iniciar: {exc}. Revisa config.ini y el servicio MySQL.") from None
    with server:
        print(f"Catálogo disponible en http://127.0.0.1:{server.server_port} · Ctrl+C para salir", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
