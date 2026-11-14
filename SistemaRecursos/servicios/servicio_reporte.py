import csv
from datetime import date, datetime, time, timedelta, timezone
from dominio.gestion_personas_usuarios.personas import TipoPersona
from dominio.gestion_prestamos.prestamos import EstadoPrestamo, TipoPrestamo
from dominio.gestion_control.reportes import IRepositorioReporte
from dominio.compartido.validaciones import entero as identificador, texto
from io import StringIO


HORA_LIMA = timezone(timedelta(hours=-5))


class ServicioAplicacionReporte:
    def __init__(self, repositorio: IRepositorioReporte):
        self.repositorio = repositorio

    @staticmethod
    def _fecha(valor, nombre):
        if not valor:
            return None
        try:
            fecha = date.fromisoformat(valor)
            if valor != fecha.isoformat() or not 1000 <= fecha.year <= 9998:
                raise ValueError
            return fecha
        except (TypeError, ValueError):
            raise ValueError(f'{nombre}: introduce una fecha válida.') from None

    def _validar_filtros(self, datos):
        desde = self._fecha(datos.get('desde', ''), 'Desde')
        hasta = self._fecha(datos.get('hasta', ''), 'Hasta')
        if desde and hasta and desde > hasta:
            raise ValueError('La fecha desde no puede ser posterior a la fecha hasta.')
        filtros = dict(q=texto(datos.get('q', ''), 'Búsqueda', 120),
                       pagina=identificador(datos.get('pagina', 1)))
        for campo, opciones, nombre in (
            ('estado', EstadoPrestamo, 'estado del préstamo'),
            ('tipo_persona', TipoPersona, 'tipo de solicitante'),
            ('modalidad', TipoPrestamo, 'modalidad'),
        ):
            valor = datos.get(campo, '')
            if valor and valor not in {opcion.value for opcion in opciones}:
                raise ValueError(f'Selecciona un {nombre} válido.')
            filtros[campo] = valor
        filtros['desde_utc'] = (datetime.combine(desde, time.min, HORA_LIMA)
                                .astimezone(timezone.utc).replace(tzinfo=None)) if desde else None
        filtros['hasta_utc'] = (datetime.combine(hasta + timedelta(days=1), time.min, HORA_LIMA)
                                .astimezone(timezone.utc).replace(tzinfo=None)) if hasta else None
        return filtros

    def consultar_prestamos(self, datos):
        return self.repositorio.consultar_prestamos(self._validar_filtros(datos))

    @staticmethod
    def _celda_csv(valor):
        valor = '' if valor is None else str(valor)
        if valor.lstrip().startswith(('=', '+', '-', '@')) or valor.startswith(('\t', '\r', '\n')):
            return "'" + valor
        return valor

    @staticmethod
    def _fecha_csv(fecha):
        if fecha is None:
            return ''
        return fecha.replace(tzinfo=timezone.utc).astimezone(HORA_LIMA).strftime('%d/%m/%Y %H:%M')

    def exportar_prestamos(self, datos):
        resultado = self.repositorio.consultar_prestamos(self._validar_filtros(datos), paginar=False)
        salida = StringIO(newline='')
        escritor = csv.writer(salida, delimiter=';')
        escritor.writerow(['Préstamo', 'Modalidad', 'Estado del préstamo', 'Solicitante', 'DNI',
            'Tipo de solicitante', 'Integrantes', 'Inventario', 'Recurso', 'Entrega (Lima)',
            'Límite de devolución (Lima)', 'Devolución (Lima)', 'Condición al devolver', 'Situación del bien'])
        for fila in resultado['filas']:
            integrantes = '; '.join(p['nombre'] + ' (DNI: ' + p['dni'] + ')' for p in fila['integrantes'])
            valores = [fila['id_prestamo'], fila['tipo_prestamo'], fila['estado'], fila['solicitante'],
                fila['dni_persona'], fila['tipo_persona'], integrantes, fila['codigo_inventario'],
                fila['recurso'], self._fecha_csv(fila['fecha_entrega']),
                self._fecha_csv(fila['fecha_limite_devolucion']), self._fecha_csv(fila['fecha_devolucion']),
                fila['condicion_devolucion'], fila['situacion']]
            escritor.writerow([self._celda_csv(valor) for valor in valores])
        return salida.getvalue().encode('utf-8-sig')
