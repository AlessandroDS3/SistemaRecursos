from datetime import date, datetime, timezone


class ConflictoRecursoError(ValueError):
    pass


def texto(valor, campo, limite, obligatorio=False):
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise ValueError(f"{campo}: debe ser texto.")
    valor = valor.strip()
    if (obligatorio and not valor) or len(valor) > limite:
        raise ValueError(
            f'{campo}: {"obligatorio, " if obligatorio else ""}máximo {limite} caracteres.'
        )
    return valor


def entero(valor, campo):
    try:
        if isinstance(valor, bool):
            raise ValueError
        numero = int(valor)
        if numero < 1 or str(numero) != str(valor).strip():
            raise ValueError
        return numero
    except (ValueError, TypeError):
        raise ValueError(f"{campo}: selecciona un identificador válido.") from None


def fecha(valor, campo):
    try:
        if isinstance(valor, datetime):
            valor = valor.date()
        return valor if isinstance(valor, date) else date.fromisoformat(valor)
    except (ValueError, TypeError):
        raise ValueError(f"{campo}: introduce una fecha válida.") from None


def instante_utc(valor, campo):
    """Normaliza instantes a UTC sin zona, como las columnas DATETIME del sistema."""
    if not isinstance(valor, datetime):
        raise ValueError(f"{campo}: introduce una fecha y hora válidas.")
    if valor.tzinfo is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)
    return valor
