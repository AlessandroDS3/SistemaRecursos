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
from presentacion.seguridad import requiere_permiso


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
        return render_template('vista_cambiar_clave.html')

    @requiere_permiso('USUARIOS_GESTIONAR')
    def registrar_cuenta(self, documento):
        if request.method == 'POST':
            creada = self.servicio.registrar_cuenta(
                documento,
                request.form.get('nombre_usuario', ''),
                g.usuario.id_usuario,
            )
            respuesta = make_response(
                render_template(
                    'vista_cuenta_creada.html',
                    creada=creada,
                    documento=documento,
                ),
                201,
            )
            respuesta.headers['Cache-Control'] = 'no-store, private'
            respuesta.headers['Pragma'] = 'no-cache'
            respuesta.headers['Referrer-Policy'] = 'no-referrer'
            return respuesta
        propuesta = self.servicio.consultar_propuesta_cuenta(documento)
        return render_template(
            'vista_cuenta.html', documento=documento, cuenta=propuesta, nueva=True
        )

    @requiere_permiso('USUARIOS_GESTIONAR')
    def actualizar_cuenta(self, documento):
        if request.method == 'POST':
            self.servicio.actualizar_cuenta(documento, request.form.to_dict(), g.usuario.id_usuario)
            flash('Cuenta actualizada.')
            return redirect(url_for('personas.consultar_persona', documento=documento))
        cuenta = self.servicio.consultar_cuenta(documento)
        return render_template(
            'vista_cuenta.html',
            documento=documento,
            cuenta=cuenta,
            nueva=False,
            estados=ESTADOS_CUENTA,
        )
