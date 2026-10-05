"""Corre el pipeline de datos del piloto (arquitectura medallion: Bronce -> Plata -> Oro).

    python ejecutar_pipeline.py                      todo, en orden de dependencias (necesita internet)
    python ejecutar_pipeline.py --sin-red            todo lo que no descarga: usa el Bronce que ya hay
    python ejecutar_pipeline.py --capa plata         solo una capa (bronce, plata, oro, consumo)
    python ejecutar_pipeline.py --fuente ideam       una fuente y todo lo que depende de ella
    python ejecutar_pipeline.py --lista              muestra el plan sin ejecutar
    python ejecutar_pipeline.py --auditar            al terminar, revisa la coherencia de las tres capas

La definicion de los pasos, su orden y sus dependencias esta en src/pipeline.py; la explicacion completa, en
docs/PIPELINE.md. Las descargas son de fuentes abiertas, sin clave ni registro.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pipeline import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
