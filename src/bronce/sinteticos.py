"""
Paso 1 del piloto: genera datos SINTETICOS de entrada (capa Bronce).

Todo lo que produce este script es ficticio: proyectos, paquetes de trabajo,
comunidades, areas protegidas, riesgos y clima. Se usa el marco geografico de
La Guajira solo como referencia de ubicacion, no representa informacion real
de Ecopetrol ni de ninguna comunidad.

El registro de riesgos se genera deliberadamente "sucio" (duplicados, nulos,
texto inconsistente, ~12% sin coordenadas) para poder probar el paso
Bronce -> Plata sobre un caso realista.

Cada riesgo trae la calificacion de la matriz RAM de Ecopetrol: consecuencia potencial de 0 a 5 en
Personas, Economica, Ambiental, Clientes e Imagen (segun la categoria), probabilidad inherente de A a E
y la residual con los controles. La probabilidad llega escrita de varias formas ('C', 'c',
'C - Ha ocurrido en la empresa', '3'), como en un Excel real.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString

from comun.config import BRONCE, CRS_GEOGRAFICO, SEMILLA_ALEATORIA, asegurar_directorios, cargar_parametros
from comun.marco_guajira import centro_factible_mas_cercano, punto_en_tierra, tierra_interior
from bronce import cronograma_sintetico, fechas_riesgo_sintetico, riesgo_actividad_sintetico, textos_sinteticos

rng = np.random.default_rng(SEMILLA_ALEATORIA)
random.seed(SEMILLA_ALEATORIA)

CATEGORIAS_RIESGO = [
    "social_comunidad", "ambiental", "seguridad_fisica",
    "logistico_acceso", "climatico", "contractual",
]
ESTADOS = ["latente", "proximo_a_materializarse", "materializado"]
TIPOS = ["amenaza", "oportunidad"]

# Matriz RAM: consecuencia potencial de 0 a 5 por dimension segun la categoria del riesgo (rango min-max).
# La primera dimension es la principal de esa categoria; en los paquetes "calientes" sube un nivel.
DIMENSIONES_RAM = {"PE": "cons_personas", "EC": "cons_economica", "MA": "cons_ambiental", "CL": "cons_clientes", "IM": "cons_imagen"}
PERFIL_RAM = {
    "social_comunidad": {"IM": (2, 4), "CL": (0, 3), "EC": (1, 3), "PE": (0, 2), "MA": (0, 1)},
    "ambiental": {"MA": (1, 4), "IM": (1, 3), "EC": (0, 3), "PE": (0, 1), "CL": (0, 1)},
    "seguridad_fisica": {"PE": (1, 4), "EC": (1, 3), "IM": (1, 3), "MA": (0, 1), "CL": (0, 1)},
    "logistico_acceso": {"EC": (1, 4), "CL": (1, 3), "PE": (0, 2), "IM": (0, 2), "MA": (0, 1)},
    "climatico": {"EC": (1, 4), "PE": (0, 3), "MA": (0, 3), "CL": (0, 2), "IM": (0, 1)},
    "contractual": {"EC": (1, 4), "CL": (1, 3), "IM": (0, 2), "PE": (0, 0), "MA": (0, 0)},
}
PESOS_PROB = {"normal": [0.12, 0.28, 0.30, 0.20, 0.10], "caliente": [0.0, 0.05, 0.20, 0.40, 0.35]}   # A..E
CONTROLES = {
    "social_comunidad": "Mesa de diálogo y plan de relacionamiento con la comunidad",
    "ambiental": "Plan de manejo ambiental, kit antiderrames e inspecciones",
    "seguridad_fisica": "Esquema de seguridad, rutas autorizadas y reporte de novedades",
    "logistico_acceso": "Rutas alternas, inventario de reserva y monitoreo de vías",
    "climatico": "Alertas tempranas IDEAM, obras de drenaje y plan de contingencia",
    "contractual": "Seguimiento de hitos, pólizas y comité de contratos",
}
TEXTO_PROB = {"A": "A - No ha ocurrido en la industria", "B": "B - Ha ocurrido en la industria", "C": "C - Ha ocurrido en la empresa",
              "D": "D - Sucede varias veces al año en la empresa", "E": "E - Sucede varias veces al año en la unidad"}


def calificacion_ram(categoria: str, caliente: bool) -> dict:
    """Consecuencias potenciales por dimension (0-5), probabilidad inherente y residual (A-E). Los controles bajan la
    probabilidad 0, 1 o 2 letras (no se modela la reduccion de la consecuencia)."""
    perfil = PERFIL_RAM[categoria]
    principal = next(iter(perfil))
    cons = {}
    for dim, (lo, hi) in perfil.items():
        c = int(rng.integers(lo, hi + 1))
        if caliente and dim == principal:
            c = min(5, c + 1)
        cons[DIMENSIONES_RAM[dim]] = c
    letras = "ABCDE"
    prob = letras[int(rng.choice(5, p=PESOS_PROB["caliente" if caliente else "normal"]))]
    baja = int(rng.choice(3, p=[0.3, 0.5, 0.2]))
    residual = letras[max(0, letras.index(prob) - baja)]
    return {**cons, "probabilidad": prob, "probabilidad_residual": residual, "controles": CONTROLES[categoria]}


def _ensuciar_probabilidad(letra: str) -> str:
    """Como llega en un Excel real: 'C', 'c', 'C - Ha ocurrido en la empresa' o el numero de la columna."""
    r = rng.random()
    if r < 0.15:
        return letra.lower()
    if r < 0.30:
        return TEXTO_PROB[letra]
    if r < 0.36:
        return str("ABCDE".index(letra) + 1)
    return letra


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
    nombres_proyecto = [f"Proyecto {i + 1}" for i in range(n_proyectos)]    # 1 al norte, 2 al centro, 3 al sur
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


def generar_registro_riesgos(gdf_paquetes, gdf_comunidades, gdf_areas, dias_historico=180, n_riesgos=200, actividades=None):
    """Registro de riesgos sucio a proposito y la clave de evaluacion de las categorias (ver textos_sinteticos).
    Con `actividades` (el cronograma), cada riesgo pega en una actividad de su paquete y su texto habla de ella."""
    filas = []
    categorias_reales, tipos = [], []
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

        ram = calificacion_ram(categoria, es_caliente and tipo == "amenaza")
        categorias_reales.append(categoria)
        tipos.append(tipo)

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
            **{k: ram[k] for k in DIMENSIONES_RAM.values()},
            "probabilidad": _ensuciar_probabilidad(ram["probabilidad"]),
            "probabilidad_residual": _ensuciar_probabilidad(ram["probabilidad_residual"]),
            "controles": ram["controles"],
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
    # actividad a la que pega cada riesgo (antes del texto: el texto se adapta a ella), con su propio generador aleatorio
    r_act = np.random.default_rng(SEMILLA_ALEATORIA + 17)
    verdad, claves_act = None, None
    if actividades is not None:
        verdad = riesgo_actividad_sintetico.elegir_todas(df, categorias_reales, tipos, actividades, hoy, r_act)
        claves_act = [riesgo_actividad_sintetico.clave_de(a, actividades) for a in verdad]
        # fechas coherentes con el estado, el nivel RAM y la actividad (reemplazan las sorteadas arriba)
        matriz = {int(k): list(v) for k, v in cargar_parametros(oficial=True)["ram"]["matriz"].items()}
        df = fechas_riesgo_sintetico.asignar(df, verdad, riesgo_actividad_sintetico.actividades_limpias(actividades), matriz, hoy,
                                             np.random.default_rng(SEMILLA_ALEATORIA + 19))
    # texto libre realista (descripcion, causa, accion) y ~8 % sin categoria legible, con su propio generador aleatorio
    df, clave = textos_sinteticos.redactar(df, categorias_reales, tipos, SEMILLA_ALEATORIA + 11, claves_act)

    # --- Ensuciar el dataset a proposito ---
    n = len(df)

    # 1) ~12% sin coordenadas (simula riesgos reportados solo con texto/paquete)
    idx_sin_coord = rng.choice(n, size=int(n * 0.12), replace=False)
    df.loc[idx_sin_coord, ["lat", "lon"]] = np.nan

    # 2) Nulos dispersos en campos opcionales
    # (una dimension RAM sin calificar: el evaluador la dejo en blanco)
    for col, frac in [("causa", 0.05), ("fecha_ejecucion_accion", 0.08), ("id_evento_riesgo", 0.03), ("cons_clientes", 0.04)]:
        idx = rng.choice(n, size=int(n * frac), replace=False)
        df.loc[idx, col] = None

    # 2b) Fechas como las escribe la gente: dia/mes/ano, cruzadas, un ano de mas o sin fecha de materializacion
    if verdad is not None:
        df = fechas_riesgo_sintetico.ensuciar(df, np.random.default_rng(SEMILLA_ALEATORIA + 23))

    # 3) Duplicados (mismo riesgo reportado dos veces, con pequenas variaciones)
    n_dup = int(n * 0.06)
    duplicados = df.sample(n=n_dup, random_state=SEMILLA_ALEATORIA).copy()
    duplicados["id_riesgo"] = duplicados["id_riesgo"] + "-DUP"
    duplicados["categoria"] = duplicados["categoria"].apply(lambda v: _ensuciar_texto(str(v), prob=0.8))
    df = pd.concat([df, duplicados], ignore_index=True)

    # 4) La actividad afectada, escrita como la escribe cada quien (codigo, nombre, nada, o un codigo equivocado)
    if verdad is not None:
        df["actividad_afectada"] = riesgo_actividad_sintetico.como_la_escriben(df, dict(zip(clave["id_riesgo"], verdad)), actividades, r_act)
        clave["actividad_real"] = verdad
    return df, clave.drop(columns=["plantilla"])


def main():
    asegurar_directorios()

    gdf_proy, gdf_paq = generar_proyectos_y_paquetes()
    gdf_com = generar_comunidades()
    gdf_areas = generar_areas_protegidas()
    gdf_hidro = generar_hidrologia()
    gdf_vias = generar_vias()
    df_clima = generar_clima()
    hoy = date.today()      # fecha de corte del dato: el avance y las fechas proyectadas son las de este dia
    df_cronograma, df_actividades, fechas_proyecto = cronograma_sintetico.generar(gdf_paq, hoy, SEMILLA_ALEATORIA)
    gdf_proy = gdf_proy.merge(fechas_proyecto, on="id_proyecto", how="left")
    # cada riesgo pega en una actividad de su paquete (ver bronce/riesgo_actividad_sintetico.py)
    df_riesgos, clave = generar_registro_riesgos(gdf_paq, gdf_com, gdf_areas, actividades=df_actividades)
    cols = list(df_riesgos.columns)
    cols.insert(cols.index("id_paquete_trabajo") + 1, cols.pop(cols.index("actividad_afectada")))
    df_riesgos = df_riesgos[cols]

    gdf_proy.to_file(BRONCE / "proyectos.geojson", driver="GeoJSON")
    gdf_paq.to_file(BRONCE / "paquetes_trabajo.geojson", driver="GeoJSON")
    gdf_com.to_file(BRONCE / "comunidades.geojson", driver="GeoJSON")
    gdf_areas.to_file(BRONCE / "areas_protegidas.geojson", driver="GeoJSON")
    gdf_hidro.to_file(BRONCE / "hidrologia.geojson", driver="GeoJSON")
    gdf_vias.to_file(BRONCE / "vias.geojson", driver="GeoJSON")
    df_clima.to_csv(BRONCE / "clima_sintetico.csv", index=False)
    df_riesgos.to_excel(BRONCE / "registro_riesgos.xlsx", index=False)
    clave.to_csv(BRONCE / "clave_categorias_sinteticas.csv", index=False)
    df_cronograma.to_csv(BRONCE / "cronograma_paquetes.csv", index=False)
    df_actividades.to_csv(BRONCE / "actividades_cronograma.csv", index=False)

    print("Datos sinteticos generados en:", BRONCE)
    print(f"  proyectos:        {len(gdf_proy)}")
    print(f"  paquetes trabajo: {len(gdf_paq)}")
    print(f"  comunidades:      {len(gdf_com)}")
    print(f"  areas protegidas: {len(gdf_areas)}")
    print(f"  hidrologia:       {len(gdf_hidro)}")
    print(f"  vias:             {len(gdf_vias)}")
    print(f"  registros clima:  {len(df_clima)}")
    print(f"  cronograma:       {len(df_cronograma)} paquetes, {len(df_actividades)} actividades (con repetidas), corte {hoy}")
    print(f"  riesgos (con duplicados y nulos a proposito): {len(df_riesgos)}")
    print(f"    sin coordenadas: {df_riesgos['lat'].isna().sum()} ({df_riesgos['lat'].isna().mean():.1%})")
    print(f"    sin actividad afectada: {df_riesgos['actividad_afectada'].isna().sum()}")


if __name__ == "__main__":
    main()
