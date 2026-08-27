from datetime import datetime, timedelta, timezone

# Offset fijo en vez de zoneinfo.ZoneInfo("America/Bogota"): Windows no
# trae la base de datos IANA de zonas horarias instalada por defecto
# (zoneinfo tira ZoneInfoNotFoundError sin el paquete "tzdata" instalado
# aparte). Colombia no tiene horario de verano, asi que GMT-5 fijo es
# exacto todo el año y no depende de ningun paquete extra.
ZONA_BOGOTA = timezone(timedelta(hours=-5), name="America/Bogota")

# El HTTP-date que devuelve Flask/Werkzeug SIEMPRE viene en UTC con el
# literal "GMT" (asi lo exige el estandar HTTP, RFC 7231) — nunca dice
# "GMT-5" ni nada parecido, sin importar en que zona horaria corra el
# servidor. Por eso el formato de abajo espera "GMT" tal cual: es lo que
# realmente manda el backend, y a partir de ahi se convierte a Bogota.
_FORMATOS_FECHA = (
    "%a, %d %b %Y %H:%M:%S GMT",  # formato HTTP-date que devuelve Flask/Werkzeug (UTC)
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)

MESES_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}
DIAS_ES = {0: "lun", 1: "mar", 2: "mié", 3: "jue", 4: "vie", 5: "sáb", 6: "dom"}


def parsear_fecha_hora(valor) -> datetime | None:
    """Parsea la fecha/hora que devuelve la API a un datetime real (o None
    si no se reconoce el formato). El formato HTTP-date (el que realmente
    manda el backend) se interpreta como UTC de verdad -con tzinfo-, para
    poder convertirlo despues a la hora local de Bogota al mostrarlo.

    Tambien se usa para poder ORDENAR una columna de fechas
    cronologicamente (un texto 'dd/mm/aaaa' no ordena bien como texto:
    '05/09' queda antes que '12/01' alfabeticamente aunque sea despues en
    el tiempo)."""
    if not valor:
        return None
    texto = str(valor)
    try:
        return datetime.strptime(texto, _FORMATOS_FECHA[0]).replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for formato in _FORMATOS_FECHA[1:]:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def formatear_fecha_hora(valor) -> str:
    """Convierte la fecha/hora de la API a la hora local de Bogota
    (GMT-5) en español, ej. 'mié 26 ago 2026, 09:15 a. m.'.

    La API devuelve fechas en formato HTTP-date en UTC (ej. 'Wed, 26 Aug
    2026 14:34:56 GMT'). Cortar ese string a ciegas con [:19] trunca
    minutos y segundos a la mitad; aqui se parsea de verdad, se convierte
    a America/Bogota y se reformatea entero. Si el formato no se
    reconoce, se devuelve el valor tal cual en vez de arriesgarse a
    mutilarlo.
    """
    fecha = parsear_fecha_hora(valor)
    if fecha is None:
        return str(valor) if valor else ""

    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(ZONA_BOGOTA)

    dia_semana = DIAS_ES[fecha.weekday()]
    mes = MESES_ES[fecha.month]
    hora12 = fecha.hour % 12 or 12
    periodo = "a. m." if fecha.hour < 12 else "p. m."
    return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year}, {hora12:02d}:{fecha.minute:02d} {periodo}"


def fecha_local_a_utc_str(anio: int, mes: int, dia: int) -> str:
    """Convierte la medianoche de un dia calendario en Bogota (GMT-5) a su
    equivalente en UTC, como texto 'YYYY-MM-DD HH:MM:SS'.

    El backend guarda fecha_hora en UTC y filtra con una comparacion
    directa (fecha_hora >= :fecha_desde). Si le mandamos la fecha elegida
    en el calendario tal cual (ej. '2026-08-26'), Postgres la interpreta
    como '2026-08-26 00:00:00 UTC' — que en Bogota son las 7pm del dia
    ANTERIOR (25 de agosto), asi que mediciones de la noche del 26 en
    Bogota quedaban excluidas de un filtro "26 de agosto". Convirtiendo
    la medianoche de Bogota a su UTC real (+5 horas) antes de mandarla,
    el filtro coincide con el dia calendario que el usuario ve y elige."""
    medianoche_bogota = datetime(anio, mes, dia, tzinfo=ZONA_BOGOTA)
    return medianoche_bogota.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parsear_numero(valor) -> float | None:
    """Convierte un valor numerico que puede venir como string desde la
    API (ej. '44.5000') a float, para poder ordenar una columna de
    valores numericamente en vez de alfabeticamente (donde '100' queda
    antes que '44' como texto)."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
