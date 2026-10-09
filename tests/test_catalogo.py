"""Catalogo de la vista Datos: las cifras de los reportes de calidad llegan a la pagina sin perder decimales."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))

import catalogo  # noqa: E402


def test_el_reporte_conserva_proporciones_y_deja_enteros_los_conteos(tmp_path):
    ruta = tmp_path / "reporte.csv"
    ruta.write_text("filas_plata,ia_exactitud_validacion_cruzada,ia_exactitud_sin_categoria,vacio\n200,0.918,1.0,\n",
                    encoding="utf-8")
    cifras = catalogo._cifras_reporte(ruta)
    assert cifras["filas_plata"] == 200 and isinstance(cifras["filas_plata"], int)
    assert cifras["ia_exactitud_validacion_cruzada"] == 0.918          # antes se volvia 0 y la pagina mostraba 0 %
    assert cifras["ia_exactitud_sin_categoria"] == 1
    assert cifras["vacio"] is None
