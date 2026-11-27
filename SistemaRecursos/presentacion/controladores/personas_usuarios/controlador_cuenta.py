from flask import (
    Blueprint,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from dominio.gestion_personas_usuarios.cuenta import ESTADOS_CUENTA
from dominio.gestion_personas_usuarios.rol import PERMISOS, PERMISOS_POR_ROL, ROLES
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario_tras_error


class ControladorCuenta:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('cuentas', __name__, url_prefix='/cuentas')
        self.blueprint.add_url_rule(
            '/mi-contrasena',
            'cambiar_clave_propia',
            self.cambiar_clave_propia,
            methods=['GET', 'POST'],
        )
        self.blueprint.add_url_rule(
            '/<documento>/nueva', 'registrar_cuenta', self.registrar_cuenta, methods=['GET', 'POST']
        )
        self.blueprint.add_url_rule(
            '/<documento>/editar',
            'actualizar_cuenta',
            self.actualizar_cuenta,
            methods=['GET', 'POST'],
        )

        self.blueprint.add_url_rule('/activar', 'activar_cuenta', self.activar_cuenta, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/<documento>/restablecer', 'restablecer_clave', self.restablecer_clave,
                                    methods=['POST'])

    @recuperar_formulario_tras_error(lambda self: render_template('personas_usuarios/vista_cambiar_clave.html'))
    def cambiar_clave_propia(self):
        if request.method == 'POST':
            self.servicio.cambiar_clave_propia(
                g.usuario.id_usuario,
                request.form.get('clave_actual', ''),
                request.form.get('clave_nueva', ''),
                request.form.get('confirmacion', ''),
            )
            session.clear()
            flash('Contraseña actualizada. Inicia sesión con tu nueva contraseña.')
            return redirect(url_for('auth.iniciar_sesion'))
        return render_template('personas_usuarios/vista_cambiar_clave.html')

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, documento: self._mostrar_formulario_de_cuenta(documento, nueva=True))
    def registrar_cuenta(self, documento):
        if request.method == 'POST':
            creada = self.servicio.registrar_cuenta(
                documento,
                request.form.get('nombre_usuario', ''),
                g.usuario.id_usuario,
            )
            return self._mostrar_codigo_de_activacion(documento, creada, 201)
        return self._mostrar_formulario_de_cuenta(documento, nueva=True)

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, documento: self._mostrar_formulario_de_cuenta(documento))
    def actualizar_cuenta(self, documento):
        if request.method == 'POST':
            self.servicio.actualizar_cuenta(documento, request.form.to_dict(), g.usuario.id_usuario)
            flash('Cuenta actualizada.')
            return redirect(url_for('personas.consultar_persona', documento=documento))
        return self._mostrar_formulario_de_cuenta(documento)

    def activar_cuenta(self):
        if request.method == 'POST':
            try:
                self.servicio.activar_cuenta(*(request.form.get(campo, '') for campo in (
                    'usuario', 'codigo', 'clave_nueva', 'confirmacion',
                )))
            except ValueError as error:
                return render_template('personas_usuarios/vista_activar_cuenta.html', error=str(error)), 400
            session.clear()
            flash('Contraseña establecida. Ya puedes iniciar sesión.')
            return redirect(url_for('auth.iniciar_sesion'))
        return render_template('personas_usuarios/vista_activar_cuenta.html')

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, documento: self._mostrar_formulario_de_cuenta(documento))
    def restablecer_clave(self, documento):
        acceso = self.servicio.restablecer_clave(documento, request.form.get('motivo'),
                                                  request.form.get('version'), g.usuario.id_usuario)
        return self._mostrar_codigo_de_activacion(documento, acceso, 200)

    @staticmethod
    def _mostrar_codigo_de_activacion(documento, creada, codigo_http):
        respuesta = make_response(render_template('personas_usuarios/vista_cuenta.html', modo='codigo',
                                                  creada=creada, documento=documento,
                                                  restablecida=codigo_http == 200), codigo_http)
        respuesta.headers['Cache-Control'] = 'no-store, private'
        respuesta.headers['Pragma'] = 'no-cache'
        respuesta.headers['Referrer-Policy'] = 'no-referrer'
        return respuesta

    def _mostrar_formulario_de_cuenta(self, documento, nueva=False):
        cuenta = (
            self.servicio.consultar_propuesta_cuenta(documento)
            if nueva
            else self.servicio.consultar_cuenta(documento)
        )
        return render_template(
            'personas_usuarios/vista_cuenta.html',
            modo='formulario',
            documento=documento,
            cuenta=cuenta,
            nueva=nueva,
            estados=ESTADOS_CUENTA,
            roles=ROLES,
            permisos=PERMISOS,
            matriz=(
                PERMISOS_POR_ROL
                if not nueva and g.usuario.tiene_permiso('ROLES_CONSULTAR') else None
            ),
        )
