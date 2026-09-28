"""
Paso 4 del piloto: validacion del modelo multicriterio.

1) Backtest: compara el ICT actual contra los riesgos que ya se
   materializaron. Es circular (los eventos sinteticos se generaron con las
   mismas variables que usa el modelo), asi que NO valida si los criterios o
   pesos son los correctos: solo confirma que el mecanismo de calculo,
   agregacion y ranking funciona como se espera. La validacion real requiere
   historial verdadero de Ecopetrol (Fase 4 de la propuesta).

2) Sensibilidad: perturba cada peso +/-20% (renormalizando el resto) y mide
   cuanto cambia el ranking de paquetes (correlacion de Spearman) y el nivel
   de criticidad asignado, para detectar que criterios dominan el resultado.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from config import ORO, PLATA, cargar_parametros
from modelo import ict as m_ict
from plata_a_oro import calcular_ict_para_fecha, cargar_plata


def backtest_materializados(datos, tabla_ict: pd.DataFrame) -> pd.DataFrame:
    riesgos = datos["riesgos"]
    materializados = riesgos[riesgos["estado"] == "materializado"]
    n_materializados = materializados.groupby("id_paquete_trabajo").size()

    resumen = tabla_ict[["ICT", "nivel"]].copy()
    resumen["n_riesgos_materializados"] = n_materializados.reindex(resumen.index).fillna(0).astype(int)

    top_k = max(1, round(len(resumen) * 0.3))
    top_ict = resumen.sort_values("ICT", ascending=False).head(top_k)
    precision_top_k = (top_ict["n_riesgos_materializados"] > 0).mean()

    correlacion = resumen["ICT"].corr(resumen["n_riesgos_materializados"], method="spearman")

    print("--- Backtest (circular, ver docstring) ---")
    print(resumen.sort_values("ICT", ascending=False))
    print(f"\nCorrelacion de Spearman ICT vs. riesgos materializados: {correlacion:.2f}")
    print(f"Precision del top {int(top_k)} ({top_k/len(resumen):.0%} de los paquetes con mayor ICT): "
          f"{precision_top_k:.0%} contienen al menos un riesgo materializado")
    return resumen


def analisis_sensibilidad(datos, params, hoy: pd.Timestamp, variacion=0.2) -> pd.DataFrame:
    tabla_base, crudos, _, bounds = calcular_ict_para_fecha(datos, params, hoy)
    ranking_base = tabla_base["ICT"].rank(ascending=False)

    filas = []
    for criterio in m_ict.CRITERIOS:
        for signo, etiqueta in [(1, "+20%"), (-1, "-20%")]:
            pesos_mod = dict(params["pesos"])
            pesos_mod[criterio] = max(0.0, pesos_mod[criterio] * (1 + signo * variacion))
            total = sum(pesos_mod.values())
            pesos_mod = {k: v / total for k, v in pesos_mod.items()}

            tabla_mod, _ = m_ict.ensamblar_ict(crudos, pesos_mod, list(tabla_base.index), bounds=bounds)
            ranking_mod = tabla_mod["ICT"].rank(ascending=False)

            rho, _ = spearmanr(ranking_base, ranking_mod)
            cambio_nivel = (
                tabla_mod["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
                != tabla_base["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
            ).sum()

            filas.append({
                "criterio": criterio, "variacion": etiqueta,
                "correlacion_ranking_spearman": round(rho, 3),
                "paquetes_que_cambian_de_nivel": int(cambio_nivel),
            })

    df = pd.DataFrame(filas)
    print("\n--- Analisis de sensibilidad (+/-20% por criterio) ---")
    print(df.to_string(index=False))
    print("\nLectura: correlacion mas baja y mas paquetes cambiando de nivel = "
          "el modelo es mas sensible a ese criterio; conviene fijar su peso con "
          "especial cuidado en los talleres de la Fase 2.")
    return df


def main():
    params = cargar_parametros()
    datos = cargar_plata()
    hoy = pd.Timestamp.now().normalize()

    tabla_ict = gpd.read_file(ORO / "paquetes_ict.geojson").set_index("id_paquete")

    resumen_backtest = backtest_materializados(datos, tabla_ict)
    resumen_sensibilidad = analisis_sensibilidad(datos, params, hoy)

    resumen_backtest.to_csv(ORO / "validacion_backtest.csv")
    resumen_sensibilidad.to_csv(ORO / "validacion_sensibilidad.csv", index=False)
    print(f"\nResultados guardados en {ORO}")


if __name__ == "__main__":
    main()
