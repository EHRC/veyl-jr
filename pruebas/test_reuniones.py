"""Pruebas de reuniones.py y stt.construir_url. Sin audio ni red.

  python pruebas/test_reuniones.py     (o pytest, si lo tienes)
"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reuniones import Reunion, hhmmss, listar  # noqa: E402
from stt import construir_url  # noqa: E402

INICIO = datetime(2026, 10, 26, 15, 4)


def test_guarda_con_la_primera_frase_y_al_terminar():
    with tempfile.TemporaryDirectory() as tmp:
        r = Reunion(Path(tmp), "Revisión semanal", inicio=INICIO)
        assert not r.ruta.exists()
        r.agregar("Otros", "Hola, ¿me escuchan?", INICIO + timedelta(seconds=5))
        assert r.ruta.exists() and "en curso" in r.ruta.read_text(encoding="utf-8")
        r.agregar("Yo", "Sí, perfecto.", INICIO + timedelta(minutes=1, seconds=2))
        ruta = r.terminar(INICIO + timedelta(minutes=42, seconds=10))
        texto = ruta.read_text(encoding="utf-8")
        assert ruta.name == "2026-10-26 1504 - Revisión semanal.md"
        assert "- Duración: 00:42:10" in texto
        assert "- Participantes: Otros, Yo" in texto
        assert "**[00:00:05] Otros:** Hola, ¿me escuchan?" in texto
        assert "**[00:01:02] Yo:** Sí, perfecto." in texto
        assert not list(Path(tmp).glob(".*.tmp"))  # sin temporales sueltos


def test_sin_frases_no_deja_archivo():
    with tempfile.TemporaryDirectory() as tmp:
        r = Reunion(Path(tmp), "Vacía", inicio=INICIO)
        assert r.terminar() is None
        assert listar(Path(tmp)) == []


def test_titulo_limpio_y_sin_pisar_otra_reunion():
    with tempfile.TemporaryDirectory() as tmp:
        a = Reunion(Path(tmp), "  Cliente / Q4: ¿avance?  ", inicio=INICIO)
        a.agregar("Otros", "uno")
        b = Reunion(Path(tmp), "Cliente / Q4: ¿avance?", inicio=INICIO)
        b.agregar("Otros", "dos")
        assert a.ruta.name == "2026-10-26 1504 - Cliente Q4 avance.md"
        assert b.ruta.name == "2026-10-26 1504 - Cliente Q4 avance (2).md"
        assert Reunion(Path(tmp), "", inicio=INICIO).ruta.name == "2026-10-26 1504 - Reunión.md"


def test_listar_mas_reciente_primero():
    with tempfile.TemporaryDirectory() as tmp:
        for dia in (3, 1, 2):
            Reunion(Path(tmp), "R", inicio=INICIO.replace(day=dia)).agregar("Yo", "x")
        assert [p.name[:10] for p in listar(Path(tmp))] == ["2026-10-03", "2026-10-02", "2026-10-01"]
        assert listar(Path(tmp) / "no-existe") == []


def test_hhmmss():
    assert hhmmss(0) == "00:00:00"
    assert hhmmss(3725.9) == "01:02:05"


def test_construir_url():
    url = construir_url("wss://x/v3/ws", 48000, "universal-streaming-multilingual", ["Veyl"])
    assert "sample_rate=48000" in url and "keyterms_prompt" in url
    assert "language_codes" not in url
    assert "language_codes" in construir_url("wss://x", 16000, "universal-3-5-pro", [])


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"ok  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas ok")
