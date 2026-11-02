"""Erixcel React hook validation; read-only."""
def format_reason(kind, errors, doc):
    return ("Erixcel React / " + kind + ": errores detectados tras editar el frontend:\n"
            + "\n".join("- " + issue for issue in errors[:20])
            + "\nConvenciones: " + doc
            + "\nCorrige lo indicado, sin alterar el comportamiento, y vuelve a comprobarlo.")
