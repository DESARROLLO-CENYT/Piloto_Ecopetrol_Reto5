"""
Paso 1 del piloto: genera datos SINTETICOS de entrada (capa Bronce).

Todo lo que produce este script es ficticio: proyectos, paquetes de trabajo,
comunidades, areas protegidas, riesgos y clima. Se usa el marco geografico de
La Guajira solo como referencia de ubicacion, no representa informacion real
de Ecopetrol ni de ninguna comunidad.

El registro de riesgos se genera deliberadamente "sucio" (duplicados, nulos,
texto inconsistente, ~12% sin coordenadas) para poder probar el paso
Bronce -> Plata sobre un caso realista.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString

from comun.config import BRONCE, CRS_GEOGRAFICO, SEMILLA_ALEATORIA, asegurar_directorios
from comun.marco_guajira import centro_factible_mas_cercano, punto_en_tierra, tierra_interior

rng = np.random.default_rng(SEMILLA_ALEATORIA)
random.seed(SEMILLA_ALEATORIA)

CATEGORIAS_RIESGO = [
    "social_comunidad", "ambiental", "seguridad_fisica",
    "logistico_acceso", "climatico", "contractual",
]
ESTADOS = ["latente", "proximo_a_materializarse", "materializado"]
TIPOS = ["amenaza", "oportunidad"]


MARGEN_COSTA = 0.02     # grados (~2 km): los puntos sinteticos quedan al menos a esta distancia de la costa y la frontera
MARGEN_BORDE = 0.012    # grados: lineas y areas quedan dentro del limite OFICIAL (el contorno de referencia esta simplificado a 0,01)


def _punto_aleatorio():
    """Punto (lon, lat) al azar sobre tierra firme de La Guajira (no en el mar ni fuera del departamento)."""
    return punto_en_tierra(rng, MARGEN_COSTA)


def _circulo(cx, cy, radio_deg, quad_segs=16):
    """Poligono circular (aproximado) centrado en (cx, cy). quad_segs controla
    cuantos segmentos aproximan cada cuadrante (16 -> circulo de 64 lados)."""
    return Point(cx, cy).buffer(radio_deg, quad_segs=quad_segs)


# Tamano base de un proyecto: los paquetes de trabajo se reparten en una cuadricula de 3 columnas dentro de este
# rectangulo (en grados) y el poligono del proyecto es el circulo que lo envuelve, asi que todo queda dentro del proyecto.
ANCHO_PROYECTO, ALTO_PROYECTO = 0.28, 0.20
RADIO_PROYECTO = 0.19
# Zona aproximada de cada proyecto (lon, lat). El centro real es el punto mas cercano donde el proyecto cabe entero en tierra.
ZONAS_PROYECTO = [(-72.25, 11.75), (-72.30, 11.35), (-72.90, 10.85)]   # norte (Alta Guajira), centro (Maicao), sur (Perija)


def _escala_que_cabe() -> float:
    """Mayor escala (1, 0,85, 0,7...) con la que los tres proyectos caben enteros en tierra."""
    for escala in (1.0, 0.85, 0.7, 0.55):
        if all(centro_factible_mas_cercano(z, RADIO_PROYECTO * escala) for z in ZONAS_PROYECTO):
            return escala
    raise RuntimeError("Los proyectos no caben en La Guajira ni con la escala minima")


def generar_proyectos_y_paquetes(n_proyectos=3, paquetes_por_proyecto=(4, 6)):
    """3 proyectos ficticios con 4-6 paquetes de trabajo (poligonos) cada uno, TODOS dentro de tierra firme de La Guajira."""
    proyectos, paquetes = [], []
    nombres_proyecto = ["Proyecto Sintetico Norte", "Proyecto Sintetico Centro", "Proyecto Sintetico Sur"]
    escala = _escala_que_cabe()
    ancho_proy, alto_proy, radio = ANCHO_PROYECTO * escala, ALTO_PROYECTO * escala, RADIO_PROYECTO * escala

    for i in range(n_proyectos):
        cx, cy = centro_factible_mas_cercano(ZONAS_PROYECTO[i], radio)
        poligono_proyecto = _circulo(cx, cy, radio)
        id_proyecto = f"PRY-{i+1:02d}"
        proyectos.append({
            "id_proyecto": id_proyecto,
            "nombre": nombres_proyecto[i],
            "geometry": poligono_proyecto,
        })

        n_paq = rng.integers(paquetes_por_proyecto[0], paquetes_por_proyecto[1] + 1)
        cols, filas = 3, int(np.ceil(n_paq / 3))
        paso_x = ancho_proy / cols
        paso_y = alto_proy / filas
        x0, y0 = cx - ancho_proy / 2, cy - alto_proy / 2

        for j in range(n_paq):
            col, fila = j % cols, j // cols
            pcx = x0 + paso_x * (col + 0.5)
            pcy = y0 + paso_y * (fila + 0.5)
            geom = _circulo(pcx, pcy, min(paso_x, paso_y) * 0.42)
            paquetes.append({
                "id_paquete": f"{id_proyecto}-PT{j+1:02d}",
                "id_proyecto": id_proyecto,
                "nombre": f"Paquete {j+1} - {nombres_proyecto[i]}",
                "ruta_critica": bool(rng.random() < 0.3),
                "geometry": geom,
            })

    gdf_proy = gpd.GeoDataFrame(proyectos, crs=CRS_GEOGRAFICO)
    gdf_paq = gpd.GeoDataFrame(paquetes, crs=CRS_GEOGRAFICO)
    return gdf_proy, gdf_paq


def generar_comunidades(n=18):
    nombres_base = ["Wayuu", "Rancheria", "Caserio", "Asentamiento", "Comunidad"]
    filas = []
    for i in range(n):
        lon, lat = _punto_aleatorio()
        filas.append({
            "id_comunidad": f"COM-{i+1:03d}",
            "nombre": f"{random.choice(nombres_base)} Sintetico {i+1}",
            "poblacion_aprox": int(rng.integers(30, 1200)),
            "conflictividad": round(float(rng.beta(2, 5)), 3),  # sesgado a valores bajos
            "geometry": Point(lon, lat),
        })
    return gpd.GeoDataFrame(filas, crs=CRS_GEOGRAFICO)


def generar_areas_protegidas(n=6):
    categorias = ["Parque Natural (ficticio)", "Reserva Forestal (ficticia)", "Zona Ramsar (ficticia)"]
    filas = []
    for i in range(n):
        radio = rng.uniform(0.025, 0.075)
        for _ in range(200):                       # el area entera debe caber en tierra
            cx, cy = _punto_aleatorio()
            geom = _circulo(cx, cy, radio)
            if tierra_interior(MARGEN_BORDE).contains(geom):
                break
        else:
            raise RuntimeError("No se encontro donde ubicar un area protegida en tierra")
        filas.append({
            "id_area": f"APR-{i+1:02d}",
            "nombre": f"Area Protegida Sintetica {i+1}",
            "categoria": random.choice(categorias),
            "sensibilidad": round(float(rng.uniform(0.4, 1.0)), 3),
            "geometry": geom,
        })
    return gpd.GeoDataFrame(filas, crs=CRS_GEOGRAFICO)


def generar_hidrologia(n=8):
    filas = []
    for i in range(n):
        for _ in range(200):
            lon0, lat0 = _punto_aleatorio()
            puntos = [(lon0, lat0)]
            for _ in range(rng.integers(2, 5)):
                lon0 += rng.uniform(-0.08, 0.08)
                lat0 += rng.uniform(-0.15, -0.02)  # tiende a fluir hacia el sur, ficticio
                puntos.append((lon0, lat0))
            linea = LineString(puntos).intersection(tierra_interior(MARGEN_BORDE))    # lo que se sale del departamento se corta
            if linea.geom_type == "MultiLineString":
                linea = max(linea.geoms, key=lambda g: g.length)
            if linea.geom_type == "LineString" and linea.length > 0.1:
                break
        else:
            raise RuntimeError("No se encontro donde ubicar un arroyo en tierra")
        filas.append({
            "id_cuerpo_agua": f"HID-{i+1:02d}",
            "nombre": f"Arroyo Sintetico {i+1}",
            "geometry": linea,
        })
    return gpd.GeoDataFrame(filas, crs=CRS_GEOGRAFICO)


def generar_vias(n=10):
    tipos = ["primaria", "secundaria", "terciaria_dificil_acceso"]
    filas = []
    for i in range(n):
        for _ in range(500):                       # el tramo entero debe ir por tierra
            lon0, lat0 = _punto_aleatorio()
            lon1 = lon0 + rng.uniform(-0.3, 0.3)
            lat1 = lat0 + rng.uniform(-0.3, 0.3)
            tramo = LineString([(lon0, lat0), (lon1, lat1)])
            if tierra_interior(MARGEN_BORDE).contains(tramo):
                break
        else:
            raise RuntimeError("No se encontro donde ubicar una via en tierra")
        filas.append({
            "id_via": f"VIA-{i+1:02d}",
            "tipo": random.choice(tipos),
            "geometry": tramo,
        })
    return gpd.GeoDataFrame(filas, crs=CRS_GEOGRAFICO)


def generar_clima(dias=120, n_estaciones=5):
    """Serie diaria SINTETICA (simulada, no es del IDEAM), con un evento de lluvia extrema plantado."""
    filas = []
    estaciones = []
    for e in range(n_estaciones):
        lon, lat = _punto_aleatorio()
        estaciones.append((f"EST-{e+1:02d}", lon, lat))

    fecha_inicio = date.today() - timedelta(days=dias)
    dia_evento_extremo = rng.integers(dias - 20, dias - 5)  # cerca del final, para alertas recientes

    for d in range(dias):
        fecha = fecha_inicio + timedelta(days=d)
        for id_est, lon, lat in estaciones:
            precip = max(0.0, rng.normal(4, 6))
            viento = max(0, rng.normal(15, 8))
            if d == dia_evento_extremo:
                precip += rng.uniform(60, 120)  # evento extremo sintetico
                viento += rng.uniform(20, 40)
            filas.append({
                "id_estacion": id_est,
                "fecha": fecha.isoformat(),
                "lon": lon, "lat": lat,
                "precipitacion_mm": round(precip, 1),
                "temperatura_c": round(rng.normal(29, 2), 1),
                "viento_kmh": round(viento, 1),
            })
    return pd.DataFrame(filas)


def _ensuciar_texto(valor, prob=0.35):
    """Introduce inconsistencias de mayusculas/espacios, como en Excel real."""
    if rng.random() < prob:
        opciones = [valor.upper(), valor.replace("_", " ").title(), f" {valor} ", valor.capitalize()]
        return random.choice(opciones)
    return valor


def generar_registro_riesgos(gdf_paquetes, gdf_comunidades, gdf_areas, dias_historico=180, n_riesgos=200):
    filas = []
    ids_paquete = gdf_paquetes["id_paquete"].tolist()

    # Zonas "calientes" plantadas: 3 paquetes reciben muchos riesgos severos
    paquetes_calientes = random.sample(ids_paquete, 3)

    hoy = date.today()

    for i in range(n_riesgos):
        id_paquete = random.choice(
            paquetes_calientes * 4 + ids_paquete  # sobre-representa las zonas calientes
        )
        paquete = gdf_paquetes.loc[gdf_paquetes["id_paquete"] == id_paquete].iloc[0]
        centro = paquete.geometry.centroid

        es_caliente = id_paquete in paquetes_calientes
        categoria = random.choice(CATEGORIAS_RIESGO)
        tipo = "oportunidad" if rng.random() < 0.18 else "amenaza"

        probabilidad = int(rng.integers(3, 6)) if (es_caliente and tipo == "amenaza") else int(rng.integers(1, 6))
        impacto = int(rng.integers(3, 6)) if (es_caliente and tipo == "amenaza") else int(rng.integers(1, 6))

        estado = random.choices(ESTADOS, weights=[0.55, 0.25, 0.20])[0]
        dias_atras = int(rng.integers(1, dias_historico))
        fecha_identificacion = hoy - timedelta(days=dias_atras)

        fecha_materializacion = None
        if estado == "materializado":
            fecha_materializacion = fecha_identificacion + timedelta(days=int(rng.integers(1, 30)))

        # Accion de tratamiento: a veces vencida (para probar reglas de escalamiento)
        fecha_accion = hoy + timedelta(days=int(rng.integers(-15, 45)))

        # Ubicacion: jitter alrededor del centroide del paquete, siempre dentro del paquete (que esta en tierra)
        lon, lat = centro.x, centro.y
        for _ in range(20):
            x, y = centro.x + rng.normal(0, 0.02), centro.y + rng.normal(0, 0.02)
            if paquete.geometry.contains(Point(x, y)):
                lon, lat = x, y
                break

        fila = {
            "id_riesgo": f"RSK-{i+1:04d}",
            "id_evento_riesgo": f"EVT-{rng.integers(1000, 9999)}",
            "descripcion": f"Riesgo sintetico de tipo {categoria} en {id_paquete}",
            "causa": f"Causa sintetica asociada a {categoria}",
            "categoria": _ensuciar_texto(categoria),
            "tipo": tipo,
            "probabilidad": probabilidad,
            "impacto": impacto,
            "estado": _ensuciar_texto(estado),
            "id_proyecto": paquete["id_proyecto"],
            "id_paquete_trabajo": id_paquete,
            "fecha_identificacion": fecha_identificacion.isoformat(),
            "fecha_materializacion": fecha_materializacion.isoformat() if fecha_materializacion else None,
            "accion_tratamiento": f"Accion sintetica {i+1}",
            "fecha_ejecucion_accion": fecha_accion.isoformat(),
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "fuente": random.choice(["excel_riesgos_2025.xlsx", "excel_riesgos_2026.xlsx", "reporte_campo.xlsx"]),
        }
        filas.append(fila)

    df = pd.DataFrame(filas)

    # --- Ensuciar el dataset a proposito ---
    n = len(df)

    # 1) ~12% sin coordenadas (simula riesgos reportados solo con texto/paquete)
    idx_sin_coord = rng.choice(n, size=int(n * 0.12), replace=False)
    df.loc[idx_sin_coord, ["lat", "lon"]] = np.nan

    # 2) Nulos dispersos en campos opcionales
    for col, frac in [("causa", 0.05), ("fecha_ejecucion_accion", 0.08), ("id_evento_riesgo", 0.03)]:
        idx = rng.choice(n, size=int(n * frac), replace=False)
        df.loc[idx, col] = None

    # 3) Duplicados (mismo riesgo reportado dos veces, con pequenas variaciones)
    n_dup = int(n * 0.06)
    duplicados = df.sample(n=n_dup, random_state=SEMILLA_ALEATORIA).copy()
    duplicados["id_riesgo"] = duplicados["id_riesgo"] + "-DUP"
    duplicados["categoria"] = duplicados["categoria"].apply(lambda v: _ensuciar_texto(str(v), prob=0.8))
    df = pd.concat([df, duplicados], ignore_index=True)

    return df


def main():
    asegurar_directorios()

    gdf_proy, gdf_paq = generar_proyectos_y_paquetes()
    gdf_com = generar_comunidades()
    gdf_areas = generar_areas_protegidas()
    gdf_hidro = generar_hidrologia()
    gdf_vias = generar_vias()
    df_clima = generar_clima()
    df_riesgos = generar_registro_riesgos(gdf_paq, gdf_com, gdf_areas)

    gdf_proy.to_file(BRONCE / "proyectos.geojson", driver="GeoJSON")
    gdf_paq.to_file(BRONCE / "paquetes_trabajo.geojson", driver="GeoJSON")
    gdf_com.to_file(BRONCE / "comunidades.geojson", driver="GeoJSON")
    gdf_areas.to_file(BRONCE / "areas_protegidas.geojson", driver="GeoJSON")
    gdf_hidro.to_file(BRONCE / "hidrologia.geojson", driver="GeoJSON")
    gdf_vias.to_file(BRONCE / "vias.geojson", driver="GeoJSON")
    df_clima.to_csv(BRONCE / "clima_sintetico.csv", index=False)
    df_riesgos.to_excel(BRONCE / "registro_riesgos.xlsx", index=False)

    print("Datos sinteticos generados en:", BRONCE)
    print(f"  proyectos:        {len(gdf_proy)}")
    print(f"  paquetes trabajo: {len(gdf_paq)}")
    print(f"  comunidades:      {len(gdf_com)}")
    print(f"  areas protegidas: {len(gdf_areas)}")
    print(f"  hidrologia:       {len(gdf_hidro)}")
    print(f"  vias:             {len(gdf_vias)}")
    print(f"  registros clima:  {len(df_clima)}")
    print(f"  riesgos (con duplicados y nulos a proposito): {len(df_riesgos)}")
    print(f"    sin coordenadas: {df_riesgos['lat'].isna().sum()} ({df_riesgos['lat'].isna().mean():.1%})")


if __name__ == "__main__":
    main()
