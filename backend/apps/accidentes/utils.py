"""Cálculo de días hábiles (lunes-viernes).

NOTA: los festivos colombianos (Ley 51/1983) se incorporarán con un
calendario configurable por IPS en una iteración posterior; por ahora el
cálculo excluye solo fines de semana, que es el caso conservador (nunca
extiende el plazo real).
"""
import datetime as dt


def sumar_dias_habiles(fecha: dt.date, dias: int) -> dt.date:
    """Devuelve la fecha que resulta de sumar `dias` hábiles a `fecha`."""
    actual = fecha
    restantes = dias
    while restantes > 0:
        actual += dt.timedelta(days=1)
        if actual.weekday() < 5:  # 0-4 = lunes a viernes
            restantes -= 1
    return actual


def dias_habiles_entre(desde: dt.date, hasta: dt.date) -> int:
    """Días hábiles estrictamente posteriores a `desde` hasta `hasta` inclusive."""
    if hasta <= desde:
        return 0
    total, actual = 0, desde
    while actual < hasta:
        actual += dt.timedelta(days=1)
        if actual.weekday() < 5:
            total += 1
    return total
