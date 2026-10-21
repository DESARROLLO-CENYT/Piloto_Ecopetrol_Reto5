"""Avance y fechas de actividades, paquetes y proyectos: Plata -> Oro.

Entradas (Plata): actividades.parquet, cronograma.parquet, paquetes.geojson, proyectos.geojson, riesgos.geojson (sinteticos).
Salidas (Oro):    data/gold/cronograma_actividades.csv  una fila por actividad
                  data/gold/cronograma_paquetes.csv     una fila por paquete
                  data/gold/cronograma_proyectos.csv    una fila por proyecto

Todo sale de las actividades (ver modelo/cronograma.py): cada una pesa una parte de su paquete y cada paquete pesa en su
proyecto segun su presupuesto, asi que el avance de un proyecto es la suma de lo que aporta cada actividad.

Para cada nivel se comparan el avance REAL con el PLANEADO a la fecha de corte (indice de cumplimiento) y la fecha de
fin PLANEADA con la PROYECTADA (el atraso proyectado). En los paquetes, ademas, ese atraso se compara con la holgura:
si la pasa, el paquete empieza a atrasar a su proyecto.

Cada actividad cuenta ademas los riesgos que le pegan (cada riesgo del registro apunta a una actividad, ver
modelo/actividad_riesgo.py): cuantas amenazas abiertas tiene, cuantas de nivel RAM alto o muy alto y cuantos riesgos ya
se materializaron en ella.

Uso:  python -m oro.cronograma
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from comun.config import ORO, PLATA, asegurar_directorios
from modelo import cronograma as m


def riesgos_por_actividad(riesgos: pd.DataFrame | None, ids: pd.Index) -> pd.DataFrame:
    """Riesgos del registro que pegan en cada actividad: total, amenazas abiertas, de ellas las de RAM residual alta o muy
    alta, y los ya materializados."""
    cols = ["riesgos", "amenazas_abiertas", "amenazas_altas", "riesgos_materializados"]
    if riesgos is None or "id_actividad" not in riesgos:
        return pd.DataFrame(0, index=ids, columns=cols)
    r = riesgos[riesgos["id_actividad"].notna()]
    abierta = (r["tipo"] == "amenaza") & (r["estado"] != "materializado")
    out = pd.DataFrame({
        "riesgos": r.groupby("id_actividad").size(),
        "amenazas_abiertas": abierta.groupby(r["id_actividad"]).sum(),
        "amenazas_altas": (abierta & r["nivel_residual"].isin(["H", "VH"])).groupby(r["id_actividad"]).sum(),
        "riesgos_materializados": (r["estado"] == "materializado").groupby(r["id_actividad"]).sum(),
    })
    return out.reindex(ids).fillna(0).astype(int)[cols]


def construir(act: pd.DataFrame, cron: pd.DataFrame, paquetes: pd.DataFrame, proyectos: pd.DataFrame,
              riesgos: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Las tres tablas de Oro a partir de lo que dejo Plata. Funcion pura (sin leer archivos)."""
    corte = pd.to_datetime(act["fecha_corte"]).max()
    nom_paq = paquetes.set_index("id_paquete")["nombre"]
    nom_proy = proyectos.set_index("id_proyecto")["nombre"]

    # --- paquetes ---------------------------------------------------------------------------------------------------
    p = cron.set_index("id_paquete")
    p.insert(0, "nombre", nom_paq.reindex(p.index))
    p.insert(1, "id_proyecto", paquetes.set_index("id_paquete")["id_proyecto"].reindex(p.index))
    p["peso_en_proyecto"] = (p["presupuesto_usd"] / p.groupby("id_proyecto")["presupuesto_usd"].transform("sum")).round(4)
    p["atraso_sobre_holgura_dias"] = (p["atraso_proyectado_dias"] - p["holgura_dias"]).clip(lower=0)
    sin_terminar = act[act["estado"] != "completada"].sort_values(["id_paquete", "orden"])
    p["actividad_en_curso"] = act[act["estado"] == "en_curso"].groupby("id_paquete")["nombre"].first().reindex(p.index)
    p["siguiente_actividad"] = sin_terminar[sin_terminar["estado"] == "por_iniciar"].groupby("id_paquete")["nombre"].first().reindex(p.index)
    cols_paq = ["nombre", "id_proyecto", "ruta_critica", "presupuesto_usd", "peso_en_proyecto", "holgura_dias", "avance", "avance_plan",
                "indice_cumplimiento", "fecha_inicio_plan", "fecha_fin_plan", "fecha_inicio_proyectada", "fecha_fin_proyectada",
                "atraso_proyectado_dias", "atraso_sobre_holgura_dias", "duracion_meses", "meses_restantes", "n_actividades",
                "n_completadas", "n_en_curso", "actividad_en_curso", "siguiente_actividad", "fecha_corte"]
    paq = p[cols_paq].reset_index()

    # --- proyectos --------------------------------------------------------------------------------------------------
    pq = p[["id_proyecto", "presupuesto_usd", "holgura_dias", "fecha_fin_proyectada", "atraso_proyectado_dias"]]
    pr = m.consolidar_proyectos(act, pq, corte)
    pr.insert(0, "nombre", nom_proy.reindex(pr.index))
    pr["fecha_corte"] = corte
    proy = pr.reset_index()

    # --- actividades ------------------------------------------------------------------------------------------------
    a = act.copy()
    a["nombre_paquete"] = a["id_paquete"].map(nom_paq)
    a["nombre_proyecto"] = a["id_proyecto"].map(nom_proy)
    a["aporte_avance_pp"] = (a["peso_en_proyecto"] * a["avance"] * 100).round(3)       # puntos de avance que ya aporta al proyecto
    a["aporte_total_pp"] = (a["peso_en_proyecto"] * 100).round(3)                       # puntos que aportara al terminar
    a["atraso_proyectado_dias"] = (a["fecha_fin_proyectada"] - a["fecha_fin_plan"]).dt.days
    a["por_ejecutar"] = a["estado"] != "completada"
    a = a.join(riesgos_por_actividad(riesgos, pd.Index(a["id_actividad"])), on="id_actividad")
    cols_act = ["id_actividad", "id_paquete", "nombre_paquete", "id_proyecto", "nombre_proyecto", "orden", "nombre", "disciplina",
                "estado", "avance", "peso_en_paquete", "peso_en_proyecto", "aporte_avance_pp", "aporte_total_pp", "por_ejecutar",
                "fecha_inicio_plan", "fecha_fin_plan", "fecha_inicio_real", "fecha_fin_real", "fecha_inicio_proyectada",
                "fecha_fin_proyectada", "atraso_proyectado_dias", "riesgos", "amenazas_abiertas", "amenazas_altas",
                "riesgos_materializados", "fecha_corte"]
    return {"actividades": a[cols_act], "paquetes": paq, "proyectos": proy}


def main() -> int:
    asegurar_directorios()
    faltan = [n for n in ("actividades.parquet", "cronograma.parquet", "paquetes.geojson", "proyectos.geojson") if not (PLATA / n).exists()]
    if faltan:
        print(f"Faltan en Plata: {', '.join(faltan)}. Corre antes plata.sinteticos")
        return 1
    act = pd.read_parquet(PLATA / "actividades.parquet")
    cron = pd.read_parquet(PLATA / "cronograma.parquet")
    paquetes = gpd.read_file(PLATA / "paquetes.geojson").drop(columns="geometry")
    proyectos = gpd.read_file(PLATA / "proyectos.geojson").drop(columns="geometry")
    riesgos = gpd.read_file(PLATA / "riesgos.geojson").drop(columns="geometry") if (PLATA / "riesgos.geojson").exists() else None
    t = construir(act, cron, paquetes, proyectos, riesgos)
    t["actividades"].to_csv(ORO / "cronograma_actividades.csv", index=False, encoding="utf-8")
    t["paquetes"].to_csv(ORO / "cronograma_paquetes.csv", index=False, encoding="utf-8")
    t["proyectos"].to_csv(ORO / "cronograma_proyectos.csv", index=False, encoding="utf-8")
    print(f"Oro del cronograma generado: {len(t['actividades'])} actividades, {len(t['paquetes'])} paquetes, {len(t['proyectos'])} proyectos")
    for _, f in t["proyectos"].iterrows():
        print(f"  {f['id_proyecto']}: avance {f['avance'] * 100:.1f} % (plan {f['avance_plan'] * 100:.1f} %), "
              f"fin plan {f['fecha_fin_plan']:%Y-%m-%d}, fin proyectado {f['fecha_fin_proyectada']:%Y-%m-%d} ({f['atraso_proyectado_dias']:+d} días)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
