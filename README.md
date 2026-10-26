# Veyl Jr

Transcribe tus reuniones de Meet, Zoom o Teams en vivo y las guarda como archivos Markdown en tu computador. Para macOS.

- Transcripción en vivo, separando **Yo** (tu micrófono) y **Otros** (el audio del computador).
- Cada reunión queda en `~/Documents/Veyl Jr/Reuniones/` como un `.md` con fecha, duración y la transcripción con marcas de tiempo. El archivo se actualiza después de cada frase, así que un cierre inesperado no pierde lo anterior.
- Lista de reuniones guardadas en la misma ventana (doble clic para abrir).

**Lo que no hace:** no guarda audio, no usa IA generativa, no busca en tus documentos y no tiene servidor propio.

**Lo que sí debes saber:** el audio sale de tu computador hacia [AssemblyAI](https://www.assemblyai.com), que lo transcribe con tu propia clave y la cobra a tu cuenta. Revisa su política de datos antes de usarlo con información sensible.

> **Avisa a los participantes** al inicio de la reunión que la estás transcribiendo. En Chile lo exige la Ley 21.719; en otros países hay reglas parecidas. La app lo recuerda antes de la primera grabación.

## 1. Requisitos

- macOS 13 o superior, Python 3.11+ y Homebrew.
- Una clave de API de AssemblyAI.
- Audífonos (recomendado): sin ellos, tu micrófono también capta a los demás y sus frases salen dos veces.

## 2. Captura del audio de los demás (una sola vez)

macOS no deja grabar el audio del sistema directamente, así que se usa BlackHole, un dispositivo de audio virtual gratuito.

1. Instala BlackHole: `brew install blackhole-2ch` (reinicia si no aparece).
2. Abre **Configuración de Audio MIDI** (Aplicaciones → Utilidades).
3. Presiona **+** → **Crear dispositivo de salida múltiple**. Marca tus audífonos o parlantes **y** BlackHole 2ch. Deja tus audífonos como dispositivo principal y activa "Corrección de deriva" en BlackHole.
4. Elige ese dispositivo de salida múltiple como salida: en **Configuración del Sistema → Sonido → Salida** (para Meet en el navegador), o en la configuración de audio de Zoom/Teams como "Altavoz".

Así sigues escuchando normal y BlackHole recibe una copia del audio. Con salida múltiple las teclas de volumen del Mac no funcionan; ajusta el volumen dentro de Zoom, Meet o Teams.

## 3. Instalación

```bash
git clone https://github.com/EHRC/veyl-jr.git
cd veyl-jr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # y escribe tu ASSEMBLYAI_API_KEY en .env
```

La primera vez, macOS puede pedir permiso para usar el micrófono a la Terminal (o a la app desde la que lo corras); BlackHole cuenta como micrófono.

## 4. Uso

```bash
python main.py                          # ventana: título, Iniciar, Detener y guardar
python main.py --demo                   # prueba la ventana con frases de ejemplo (sin audio ni clave)
python main.py --consola --titulo "Cliente X"   # sin ventana; Ctrl+C termina y guarda
python main.py --dispositivos           # lista los dispositivos de entrada
```

Una reunión guardada se ve así:

```markdown
# Revisión semanal

- Fecha: 2026-10-26 15:04
- Duración: 00:42:10
- Participantes: Otros, Yo

## Transcripción

**[00:00:05] Otros:** Hola, ¿me escuchan?

**[00:01:02] Yo:** Sí, perfecto.
```

## 5. Configuración (`.env`)

| Variable | Para qué | Por defecto |
| --- | --- | --- |
| `ASSEMBLYAI_API_KEY` | Clave de AssemblyAI (obligatoria) | — |
| `STT_MODEL` | Modelo de transcripción | `universal-streaming-multilingual` |
| `PALABRAS_CLAVE` | Nombres o siglas que deben salir bien escritos, separados por coma | vacío |
| `DISPOSITIVO_OTROS` | Parte del nombre del dispositivo con el audio de los demás | `BlackHole` |
| `DISPOSITIVO_MIC` | Parte del nombre de tu micrófono | micrófono por defecto |
| `TRANSCRIBIR_MIC` | `false` transcribe solo a los demás (la mitad del costo) | `true` |
| `CARPETA_REUNIONES` | Dónde se guardan las reuniones | `~/Documents/Veyl Jr/Reuniones` |

## 6. Pruebas

```bash
python pruebas/test_reuniones.py
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
