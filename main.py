"""Veyl Jr: transcribe tus reuniones y las guarda en tu computador.

  python main.py                         ventana
  python main.py --consola [--titulo X]  sin ventana; Ctrl+C para terminar y guardar
  python main.py --demo                  ventana con frases de ejemplo (sin audio ni API)
  python main.py --dispositivos          lista los dispositivos de entrada
"""
import argparse
import sys
import threading

from config import Config, cargar_config
from motor import AVISO, MotorAudio
from reuniones import Reunion, hhmmss


def consola(cfg: Config, titulo: str) -> int:
    if not cfg.assemblyai_key:
        print("Falta ASSEMBLYAI_API_KEY: copia .env.example a .env y agrega tu clave.")
        return 1
    print(AVISO)
    reunion = Reunion(cfg.carpeta_reuniones, titulo)
    candado = threading.Lock()

    def on_turno(hablante: str, texto: str) -> None:
        with candado:
            turno = reunion.agregar(hablante, texto)
        print(f"[{hhmmss(turno.segundo)}] {hablante}: {texto}")

    motor = MotorAudio(cfg, lambda h, t: None, on_turno, lambda m: print(f"· {m}"))
    motor.iniciar()
    print(f"Grabando en {reunion.ruta}\nCtrl+C para terminar y guardar.\n")
    try:
        while motor.activo():
            motor.hilo.join(0.5)
    except KeyboardInterrupt:
        print("\nTerminando…")
        motor.parar()
    with candado:
        ruta = reunion.terminar()
    print(f"Guardada en {ruta}" if ruta else "Sin frases: no se guardó nada.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Veyl Jr: transcribe y guarda tus reuniones.")
    p.add_argument("--consola", action="store_true", help="sin ventana")
    p.add_argument("--demo", action="store_true", help="frases de ejemplo, sin audio ni API")
    p.add_argument("--dispositivos", action="store_true", help="lista los dispositivos de entrada")
    p.add_argument("--titulo", default="", help="título de la reunión (modo consola)")
    args = p.parse_args()

    if args.dispositivos:
        from audio import listar_dispositivos
        listar_dispositivos()
        return 0
    cfg = cargar_config()
    if args.consola:
        return consola(cfg, args.titulo)
    from ventana import abrir
    return abrir(cfg, demo=args.demo)


if __name__ == "__main__":
    sys.exit(main())
