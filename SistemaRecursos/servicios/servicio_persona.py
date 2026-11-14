from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import comprobar_version, dni, entero, texto, version
from dominio.gestion_personas_usuarios.persona import IRepositorioPersona, Persona
from dominio.gestion_personas_usuarios.cuenta import proteger_administradores
from dominio.gestion_personas_usuarios.acceso import exigir_permiso


class ServicioAplicacionPersona:
    def __init__(self, repositorio: IRepositorioPersona):
        self.repositorio = repositorio

    def consultar_personas(self, filtros):
        return self.repositorio.consultar_personas(
            dict(
                q=texto(filtros.get('q'), 'Búsqueda', 120),
                estado=filtros.get('estado', ''),
                pagina=entero(filtros.get('pagina', 1), 'Página'),
            )
        )

    def consultar_persona(self, documento):
        fila = self.repositorio.consultar_persona(dni(documento))
        if fila is None:
            raise NoEncontrado('Persona inexistente.')
        persona = Persona.desde_datos(fila)
        return persona, version(persona.datos())

    def guardar_persona(self, datos, actor, documento_anterior=None):
        valores = dict(datos)
        if documento_anterior is None:
            valores['estado'] = 'ACTIVA'
        persona = Persona.desde_datos(valores)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'PERSONAS_GESTIONAR')
            if documento_anterior is not None:
                cuentas = operacion.consultar_cuentas_bloqueadas()
                anterior = operacion.consultar_persona(dni(documento_anterior), bloquear=True)
                if anterior is None:
                    raise NoEncontrado('Persona inexistente.')
                comprobar_version(
                    datos.get('version'), version(Persona.desde_datos(anterior).datos())
                )
                if persona.tipo != anterior['tipo']:
                    raise ValueError(
                        'El tipo institucional de una ficha registrada no se cambia en esta operación.'
                    )
                cuenta = next((c for c in cuentas if c['dni_persona'] == documento_anterior), None)
                if cuenta:
                    proteger_administradores(
                        cuentas, cuenta, dict(cuenta, estado_persona=persona.estado), entero(actor)
                    )
                    if cuenta['id_usuario'] == entero(actor) and persona.estado != 'ACTIVA':
                        raise ValueError('No puedes desactivar tu propia persona.')
            operacion.guardar_persona(persona, documento_anterior)
        return persona.dni

    def desactivar_persona(self, documento, actor):
        persona, actual = self.consultar_persona(documento)
        datos = dict(persona.datos(), estado='INACTIVA', version=actual)
        return self.guardar_persona(datos, actor, documento)

    def buscar_personas(self, termino):
        termino = texto(termino, 'Búsqueda', 120)
        return self.repositorio.buscar_personas(termino) if len(termino) >= 2 else []
