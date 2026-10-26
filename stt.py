"""Transcripción en streaming con AssemblyAI (API v3 por WebSocket)."""
import asyncio
import json
from typing import Callable
from urllib.parse import urlencode

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

# Modelos que aceptan language_codes / prompt (familia Universal-3.x Pro)
_MODELOS_PRO = ("universal-3",)


def construir_url(base: str, frecuencia: int, modelo: str, palabras_clave: list[str]) -> str:
    params: dict[str, str] = {
        "sample_rate": str(frecuencia),
        "encoding": "pcm_s16le",
        "speech_model": modelo,
    }
    if modelo.startswith(_MODELOS_PRO):
        params["language_codes"] = json.dumps(["es"])
    if palabras_clave:
        params["keyterms_prompt"] = json.dumps(palabras_clave[:100], ensure_ascii=False)
    return f"{base}?{urlencode(params)}"


async def transcribir(
    captura,
    hablante: str,
    api_key: str,
    modelo: str,
    url_base: str,
    palabras_clave: list[str],
    on_parcial: Callable[[str, str], None],
    on_turno: Callable[[str, str], None],
    on_estado: Callable[[str], None],
    detener: asyncio.Event,
) -> None:
    """Envía el audio de `captura` y llama a on_turno(hablante, texto) al cerrar cada frase.
    Se reconecta solo si la conexión se cae."""
    espera = 1.0
    url = construir_url(url_base, captura.frecuencia, modelo, palabras_clave)

    while not detener.is_set():
        turnos_vistos: set[int] = set()  # turn_order se reinicia en cada sesión
        try:
            async with connect(url, additional_headers={"Authorization": api_key},
                               open_timeout=10, ping_interval=20) as ws:

                async def enviar():
                    while not detener.is_set():
                        try:
                            datos = await asyncio.wait_for(captura.cola.get(), timeout=0.5)
                        except asyncio.TimeoutError:
                            continue
                        await ws.send(datos)
                    await ws.send(json.dumps({"type": "Terminate"}))

                async def recibir():
                    nonlocal espera
                    async for mensaje in ws:
                        if isinstance(mensaje, bytes):
                            continue
                        datos = json.loads(mensaje)
                        tipo = datos.get("type")
                        if tipo == "Begin":
                            espera = 1.0  # conexión sana: reiniciamos el backoff
                            aplicado = (datos.get("configuration") or {}).get("model", modelo)
                            on_estado(f"{hablante}: escuchando ({aplicado})")
                        elif tipo == "Turn":
                            texto = (datos.get("utterance") or datos.get("transcript") or "").strip()
                            orden = datos.get("turn_order", -1)
                            if datos.get("end_of_turn"):
                                # Algunos modelos envían el cierre de turno dos veces
                                # (sin y con formato): guardamos una sola vez por turno.
                                if texto and orden not in turnos_vistos:
                                    turnos_vistos.add(orden)
                                    on_turno(hablante, texto)
                            elif texto:
                                on_parcial(hablante, texto)
                        elif tipo == "Termination":
                            return
                        elif tipo == "Error" or "error" in datos:
                            on_estado(f"{hablante}: error STT: {datos}")

                tarea_envio = asyncio.create_task(enviar())
                tarea_recibo = asyncio.create_task(recibir())
                hechas, pendientes = await asyncio.wait(
                    {tarea_envio, tarea_recibo}, return_when=asyncio.FIRST_COMPLETED)
                if tarea_envio in hechas and not tarea_recibo.done():
                    # Ya mandamos Terminate: esperamos la confirmación (y las últimas frases).
                    try:
                        await asyncio.wait_for(tarea_recibo, timeout=3)
                    except (asyncio.TimeoutError, ConnectionClosed):
                        pass
                for t in pendientes:
                    t.cancel()
                for t in hechas:
                    if t.exception() and not isinstance(t.exception(), ConnectionClosed):
                        raise t.exception()
                if not detener.is_set():
                    motivo = ws.close_reason or "sin motivo"
                    raise RuntimeError(f"el servidor cerró la sesión: {ws.close_code} {motivo}")
        except Exception as e:  # red, auth, etc.
            if detener.is_set():
                break
            mensaje = str(e) or e.__class__.__name__
            on_estado(f"{hablante}: conexión STT caída ({mensaje}); reintento en {espera:.0f}s")
            try:
                await asyncio.wait_for(detener.wait(), timeout=espera)
            except asyncio.TimeoutError:
                pass
            espera = min(espera * 2, 30)
            continue
