from __future__ import annotations
from dominio.gestion_prestamos.prestamo import Prestamo
from dominio.resultados_consulta import PrestamoDetalle, ResultadoPrestamos, ResumenPrestamos
from dominio.gestion_recursos.i_repositorio_recurso import IRepositorioRecurso
from dominio.gestion_recursos.i_repositorio_bien_material import IRepositorioBienMaterial
from dominio.gestion_personas_usuarios.i_repositorio_persona import IRepositorioPersona
from dominio.gestion_prestamos.i_repositorio_prestamo import IRepositorioPrestamo
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_prestamos.solicitud_prestamo import SolicitudPrestamo
from dominio.gestion_prestamos.devolucion import Devolucion
from dominio.gestion_prestamos.validacion_prestamo import lista_ids, lista_dnis
from dominio.gestion_recursos.validacion_recurso import texto
from servicios.validacion_identificadores import identificador


class ServicioAplicacionPrestamo:
    filtros_estado = (
        "ACTIVO",
        "VENCIDO",
        "DEVUELTO",
        "PARCIALMENTE_DEVUELTO",
        "PENDIENTES",
        "PERDIDOS",
    )

    def __init__(self, repositorio_prestamos: IRepositorioPrestamo, repositorio_personas: IRepositorioPersona, repositorio_bienes: IRepositorioBienMaterial, repositorio_recursos: IRepositorioRecurso):
        self.repositorio: IRepositorioPrestamo = repositorio_prestamos
        self.personas: IRepositorioPersona = repositorio_personas
        self.bienes: IRepositorioBienMaterial = repositorio_bienes
        self.recursos: IRepositorioRecurso = repositorio_recursos

    @staticmethod
    def _lista(datos, campo):
        if hasattr(datos, "getlist"):
            return datos.getlist(campo)
        return datos.get(campo, [])

    def consultar_solicitantes(self, termino, limite=20):
        termino = (termino or "").strip()
        if len(termino) < 2 or len(termino) > 120:
            return []
        filas = self.personas.consultar_solicitantes(termino, limite=limite)
        resultados = []
        for fila in filas:
            resultados.append({
                "dni": fila["dni"],
                "nombre_completo": f"{fila['nombres']} {fila['apellidos']}".strip(),
                "documento_identidad": fila["documento_identidad"],
                "cui": fila["cui"],
                "tipo": fila["tipo"],
                "estado": fila["estado_persona"],
                "estado_matricula": fila["estado_matricula"],
                "elegible": bool(fila["elegible"]),
            })
        return resultados

    def consultar_bienes_disponibles(self, termino="", id_recurso=None):
        termino = (termino or "").strip()
        if len(termino) > 120:
            return []
        if len(termino) < 2 and not id_recurso:
            return []
        id_recurso_filtro = identificador(id_recurso) if id_recurso else None
        return self.bienes.consultar_bienes_disponibles(termino, id_recurso_filtro)

    def seleccionar_bien_para_prestamo(self, id_bien):
        bien = self.bienes.consultar_bien_material(identificador(id_bien))
        if not bien:
            raise LookupError("No se encontró el ejemplar seleccionado.")
        bien.validar_disponible()
        recurso = self.recursos.consultar_recurso(bien.id_recurso_ref)
        if not recurso:
            raise LookupError("No se encontró el recurso del ejemplar.")
        return {
            "id_bien": bien.id_bien,
            "id_recurso_ref": bien.id_recurso_ref,
            "codigo_inventario": bien.codigo_inventario,
            "recurso_nombre": recurso.nombre,
            "id_categoria_ref": recurso.id_categoria_ref,
            "ubicacion": bien.ubicacion,
        }

    def registrar_prestamo(self, datos, dni_encargado) -> Prestamo:
        dni_persona = validar_dni(datos.get("dni_persona"))
        dni_encargado = validar_dni(dni_encargado)
        ids_bienes = lista_ids(self._lista(datos, "bienes"), "Bienes")
        dnis_participantes = lista_dnis(self._lista(datos, "participantes"))
        if not ids_bienes:
            raise ValueError("Selecciona al menos un bien disponible.")

        tipo_prestamo = datos.get("tipo_prestamo", "INDIVIDUAL")
        participantes = self._preparar_participantes(dni_persona, dnis_participantes, tipo_prestamo)
        if datos.get("acepta_condiciones") != "1":
            raise ValueError(
                "Confirma que comunicaste el plazo y el permiso de salida antes de registrar la entrega."
            )

        salida_solicitada = datos.get("salida_solicitada") == "1"
        observaciones = texto(datos.get("observaciones", ""), "Observaciones", 220)
        if salida_solicitada:
            observaciones = "Salida externa autorizada. " + observaciones
        else:
            observaciones = "Uso dentro de la institución. " + observaciones

        solicitud = SolicitudPrestamo(
            dni_persona=dni_persona, dni_encargado=dni_encargado, ids_bienes=ids_bienes,
            tipo_prestamo=tipo_prestamo, observaciones=observaciones,
            participantes=participantes, salida_solicitada=salida_solicitada,
        )
        return self.repositorio.registrar_prestamo(solicitud)

    def _preparar_participantes(self, dni_persona, dnis_participantes, tipo_prestamo):
        if dni_persona in dnis_participantes:
            raise ValueError(
                "El solicitante se agrega automáticamente como responsable; no lo repitas entre los participantes."
            )
        if tipo_prestamo not in {"INDIVIDUAL", "GRUPAL"}:
            raise ValueError("Selecciona un tipo de préstamo válido.")
        if tipo_prestamo == "INDIVIDUAL" and dnis_participantes:
            raise ValueError("Un préstamo individual no puede incluir participantes adicionales.")
        if tipo_prestamo == "GRUPAL" and not dnis_participantes:
            raise ValueError("Selecciona al menos otro participante para el préstamo grupal.")

        participantes = []
        if tipo_prestamo == "GRUPAL":
            participantes.append({
                "dni_persona": dni_persona,
                "responsable": True,
                "rol_participacion": "Responsable",
            })
            for dni_participante in dnis_participantes:
                participantes.append({"dni_persona": dni_participante})
        return participantes

    def consultar_resumen_prestamos(self, dni, gestionar=False) -> ResumenPrestamos:
        alcance = None if gestionar else validar_dni(dni)
        resumen = self.repositorio.consultar_resumen_prestamos(alcance)
        return {
            "prestamos_pendientes": int(resumen["prestamos_pendientes"] or 0),
            "prestamos_vencidos": int(resumen["prestamos_vencidos"] or 0),
        }

    def consultar_prestamos(self, filtros, dni, gestionar=False) -> ResultadoPrestamos:
        dni = validar_dni(dni)
        valores = {
            "q": texto(filtros.get("q", ""), "Búsqueda", 120),
            "estado": filtros.get("estado", ""),
        }
        if valores["estado"] and valores["estado"] not in self.filtros_estado:
            raise ValueError("Selecciona un filtro de préstamos válido.")
        alcance = None if gestionar else dni
        return {"prestamos": self.repositorio.consultar_prestamos(valores, alcance)}

    def consultar_prestamo(self, id_prestamo, dni, gestionar=False) -> PrestamoDetalle:
        id_prestamo = identificador(id_prestamo)
        dni = validar_dni(dni)
        prestamo = self.repositorio.consultar_prestamo(id_prestamo)
        if not prestamo:
            raise LookupError("No se encontró el préstamo.")

        puede_consultar = gestionar or prestamo["dni_persona"] == dni
        if not puede_consultar:
            for participante in prestamo["participantes"]:
                if participante["dni_persona"] == dni:
                    puede_consultar = True
                    break
        if not puede_consultar:
            raise PermissionError("No tienes permiso para consultar este préstamo.")

        return prestamo

    def actualizar_prestamos_vencidos(self, dni_responsable) -> None:
        """Comando del encargado: persiste vencimientos e historial; no forma parte de una consulta."""
        self.repositorio.actualizar_prestamos_vencidos(validar_dni(dni_responsable))

    def registrar_devolucion(self, id_prestamo, datos, dni_encargado) -> None:
        ids_detalles = lista_ids(self._lista(datos, "detalles"), "Bienes a devolver")
        if not ids_detalles:
            raise ValueError("Selecciona al menos un bien que estés recibiendo físicamente.")

        dni_encargado = validar_dni(dni_encargado)
        devoluciones = []
        for id_detalle in ids_detalles:
            devolucion = Devolucion(
                id_detalle_ref=id_detalle,
                dni_encargado=dni_encargado,
                estado_devolucion=datos.get(f"estado_{id_detalle}", ""),
                observaciones=datos.get(f"observacion_{id_detalle}", ""),
            )
            devoluciones.append(devolucion)
        self.repositorio.registrar_devolucion(
            identificador(id_prestamo), devoluciones, dni_encargado
        )

    def reportar_perdida(self, id_prestamo, id_detalle, motivo, dni_encargado) -> None:
        self.repositorio.reportar_perdida(
            identificador(id_prestamo),
            identificador(id_detalle),
            texto(motivo, "Descripción de la pérdida", 255, True),
            validar_dni(dni_encargado),
        )
