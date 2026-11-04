def identificador(valor):
    try:
        if isinstance(valor, bool):
            raise ValueError
        numero = int(valor)
        if numero < 1 or str(numero) != str(valor).strip():
            raise ValueError
        return numero
    except (ValueError, TypeError):
        raise ValueError("Selecciona un identificador válido.") from None
