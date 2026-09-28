"""Corre el pipeline completo del piloto (Pasos 1-4) en orden.

Uso:  .venv/Scripts/python.exe ejecutar_pipeline.py
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / "src"
PY = sys.executable

PASOS = [
    ("Paso 1: generar datos sinteticos", "generar_datos.py"),
    ("Paso 2: Bronce -> Plata", "bronce_a_plata.py"),
    ("Paso 3: Plata -> Oro (modelo ICT)", "plata_a_oro.py"),
    ("Paso 4: validacion (backtest + sensibilidad)", "validacion.py"),
]

for titulo, script in PASOS:
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")
    resultado = subprocess.run([PY, script], cwd=SRC)
    if resultado.returncode != 0:
        print(f"\nFallo en: {script}")
        sys.exit(resultado.returncode)

print("\nPipeline completo. Para ver el mapa: .venv/Scripts/python.exe run_app.py")
