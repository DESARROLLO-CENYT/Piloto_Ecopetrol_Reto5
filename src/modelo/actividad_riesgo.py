"""A que actividad del cronograma pega cada riesgo: se lee lo que trae el registro y, si falta o no cuadra, se infiere.

Funciones puras (sin leer archivos). El registro trae la columna `actividad_afectada` escrita a mano: el codigo de la
actividad, su nombre o su disciplina con cualquier ortografia, nada, o un codigo equivocado. Se resuelve asi:

  1. Codigo de una actividad del mismo paquete                         -> origen "registro"
  2. Nombre o disciplina de una actividad del mismo paquete            -> origen "nombre"
  3. Vacio o sin reconocer                                             -> se infiere, origen "inferida"
  4. Codigo de otro paquete, o una actividad que no cuadra con el estado del riesgo (una amenaza abierta en una actividad
     ya terminada, o una materializada en una que no habia empezado)  -> se infiere y se marca para revisar, "corregida"

La inferencia mira el momento del riesgo y su texto:
  * un riesgo latente solo puede pegar en lo que falta por hacer (actividades en curso o por iniciar); uno proximo a
    materializarse, en lo que se esta ejecutando o arranca en los proximos 45 dias; uno materializado, en la actividad que
    se ejecutaba el dia en que ocurrio;
  * entre esas, gana la que mas palabras del texto (descripcion y causa) apuntan a su disciplina, con un empujon por la
    categoria del riesgo (un riesgo contractual suele pegar en compras o ingenieria) y otro por estar en ejecucion.
Las palabras son reglas escritas a mano, no salen de los datos: el acierto se mide contra la clave del dato sintetico.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

PATRON_CODIGO = re.compile(r"PRY-\d{2}-PT\d{2}-A\d{2}")

# disciplina (normalizada) -> palabras del texto que apuntan a ella (normalizadas, sin tildes)
PALABRAS = {
    "ingenieria": ["ingenieria", "diseno", "especificaciones", "alcance", "planos"],
    "social": ["consulta previa", "autoridades tradicionales", "compensacion del paso", "compromisos sociales",
               "inversion social", "familias", "acuerdos de la consulta"],
    "ambiental": ["licencia ambiental", "autoridad ambiental", "permiso", "vertimiento", "viveros", "compensacion ambiental"],
    "compras": ["suministro", "proveedor", "transformadores", "equipos", "materiales", "nacionalizacion", "puerto",
                "carga", "cargue", "peajes", "polizas", "tractomulas", "camiones", "transportadores", "entrega"],
    "civil": ["frente de obra", "excavacion", "taludes", "despeje", "cauce", "obra", "maquinaria", "polvo", "predio",
              "cuadrilla", "cantidades de obra", "jagueyes", "arroyo", "acceso", "campamento", "corredor"],
    "electromecanica": ["montaje", "torres", "cable", "material electrico", "trabajos en altura", "estructuras",
                        "personal tecnico", "nomina"],
    "puesta en servicio": ["pruebas", "puesta en servicio", "energizacion", "infraestructura del proyecto"],
    "gestion": ["cierre", "documentacion", "residuos", "liquidacion"],
}
# categoria del riesgo -> disciplinas que suele afectar (empujon de 0 a 1)
AFINIDAD = {
    "social_comunidad": {"social": 1.0, "civil": 0.6, "electromecanica": 0.4},
    "ambiental": {"ambiental": 1.0, "civil": 0.7, "electromecanica": 0.3},
    "seguridad_fisica": {"civil": 0.8, "electromecanica": 0.8, "compras": 0.7, "puesta en servicio": 0.3},
    "logistico_acceso": {"compras": 1.0, "civil": 0.6, "electromecanica": 0.6},
    "climatico": {"civil": 1.0, "electromecanica": 0.7, "puesta en servicio": 0.4},
    "contractual": {"compras": 1.0, "ingenieria": 0.8, "civil": 0.5, "electromecanica": 0.5, "gestion": 0.4, "puesta en servicio": 0.3},
}
PESO_AFINIDAD = 0.5
BONO_EN_CURSO = 0.4
PROXIMO_DIAS = 45


def normalizar(t) -> str:
    """'  Montaje ELECTROMECÁNICO ' -> 'montaje electromecanico'."""
    if t is None or (isinstance(t, float) and np.isnan(t)):
        return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.strip().lower())


def puntaje_texto(texto: str, categoria: str) -> dict[str, float]:
    """Cuanto apunta el texto (ya normalizado) a cada disciplina, mas el empujon de la categoria."""
    out = {d: float(sum(1 for p in palabras if p in texto)) for d, palabras in PALABRAS.items()}
    for d, w in AFINIDAD.get(categoria, {}).items():
        out[d] = out.get(d, 0.0) + PESO_AFINIDAD * w
    return out


def _pronto(acts: pd.DataFrame, corte: pd.Timestamp) -> pd.Series:
    """Actividades que se estan ejecutando o arrancan en los proximos PROXIMO_DIAS dias."""
    return (acts["estado"] == "en_curso") | (pd.to_datetime(acts["fecha_inicio_proyectada"]) <= corte + pd.Timedelta(days=PROXIMO_DIAS))


def _durante(acts: pd.DataFrame, fm: pd.Timestamp, corte: pd.Timestamp) -> pd.Series:
    """Actividades que se estaban ejecutando el dia `fm`."""
    return acts["fecha_inicio_real"].notna() & (acts["fecha_inicio_real"] <= fm) & (acts["fecha_fin_real"].fillna(corte) >= fm)


def candidatas(acts: pd.DataFrame, estado: str, fecha_materializacion, corte: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    """Actividades del paquete donde el riesgo puede pegar segun su momento, y cuales estaban en ejecucion entonces."""
    if estado != "materializado":
        c = acts[acts["estado"] != "completada"]
        if estado == "proximo_a_materializarse" and _pronto(c, corte).any():
            c = c[_pronto(c, corte)]
        if c.empty:
            c = acts.tail(1)
        return c, c["estado"] == "en_curso"
    fm = min(pd.Timestamp(fecha_materializacion), corte) if pd.notna(fecha_materializacion) else corte
    c = acts[_durante(acts, fm, corte)]
    if c.empty:
        c = acts[acts["fecha_inicio_real"].notna() & (acts["fecha_inicio_real"] <= fm)]
    if c.empty:
        c = acts.head(1)
    return c, _durante(c, fm, corte)


def inferir(texto: str, categoria: str, estado: str, fecha_materializacion, acts: pd.DataFrame, corte: pd.Timestamp) -> str:
    """La actividad (id) mas probable de un paquete. `acts`: actividades de Plata del paquete, en orden."""
    c, en_curso = candidatas(acts, estado, fecha_materializacion, corte)
    p = puntaje_texto(texto, categoria)
    total = np.array([p.get(normalizar(d), 0.0) for d in c["disciplina"]]) + BONO_EN_CURSO * en_curso.to_numpy()
    return str(c["id_actividad"].iloc[int(np.argmax(total))])


def cuadra(act: pd.Series, estado: str, fecha_materializacion, corte: pd.Timestamp) -> bool:
    """La actividad registrada es posible para el momento del riesgo."""
    if estado != "materializado":
        if act["estado"] == "completada":
            return False
        return estado != "proximo_a_materializarse" or bool(_pronto(act.to_frame().T, corte).iloc[0])
    if pd.isna(fecha_materializacion):        # sin fecha no se puede descartar: basta con que ya hubiera empezado
        return pd.notna(act["fecha_inicio_real"]) and act["fecha_inicio_real"] <= corte
    fm = min(pd.Timestamp(fecha_materializacion), corte)
    return bool(_durante(act.to_frame().T, fm, corte).iloc[0])


def resolver(riesgos: pd.DataFrame, actividades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Columnas id_actividad, actividad, actividad_origen y revisar_actividad para cada riesgo (mismo indice), y el
    reporte de lo que paso. `riesgos` con estado ya normalizado y fecha_materializacion como fecha."""
    corte = pd.to_datetime(actividades["fecha_corte"]).max()
    acts = actividades.sort_values(["id_paquete", "orden"])
    por_paquete = {p: g for p, g in acts.groupby("id_paquete")}
    por_id = acts.set_index("id_actividad")
    filas, rep = [], {"riesgos_actividad_por_codigo": 0, "riesgos_actividad_por_nombre": 0, "riesgos_actividad_inferidas": 0,
                      "riesgos_actividad_codigo_de_otro_paquete": 0, "riesgos_actividad_no_cuadra_con_el_estado": 0}
    for idx, r in riesgos.iterrows():
        paquete = r["id_paquete_trabajo"]
        mias = por_paquete.get(paquete)
        if mias is None:
            filas.append((idx, None, None, None, False))
            continue
        estado = r["estado"]
        crudo = r.get("actividad_afectada")
        texto = normalizar(f"{r.get('descripcion', '')} {r.get('causa', '')}")
        codigo = PATRON_CODIGO.search(str(crudo).upper()) if pd.notna(crudo) else None
        elegida, origen = None, None
        if codigo:
            cod = codigo.group(0)
            if cod in mias["id_actividad"].values:
                elegida, origen = cod, "registro"
                rep["riesgos_actividad_por_codigo"] += 1
            else:
                origen = "corregida"
                rep["riesgos_actividad_codigo_de_otro_paquete"] += 1
        elif normalizar(crudo):
            n = normalizar(crudo)
            hit = mias[(mias["nombre"].map(normalizar) == n) | (mias["disciplina"].map(normalizar) == n)]
            if len(hit):
                elegida, origen = str(hit["id_actividad"].iloc[0]), "nombre"
                rep["riesgos_actividad_por_nombre"] += 1
        if elegida and not cuadra(por_id.loc[elegida], estado, r.get("fecha_materializacion"), corte):
            elegida, origen = None, "corregida"
            rep["riesgos_actividad_no_cuadra_con_el_estado"] += 1
        if elegida is None:
            elegida = inferir(texto, r.get("categoria", ""), estado, r.get("fecha_materializacion"), mias, corte)
            if origen is None:
                origen = "inferida"
                rep["riesgos_actividad_inferidas"] += 1
        filas.append((idx, elegida, por_id.at[elegida, "nombre"], origen, origen == "corregida"))
    out = pd.DataFrame(filas, columns=["_i", "id_actividad", "actividad", "actividad_origen", "revisar_actividad"]).set_index("_i")
    out.index.name = riesgos.index.name
    rep["riesgos_actividad_corregidas"] = int((out["actividad_origen"] == "corregida").sum())
    rep["riesgos_sin_actividad"] = int(out["id_actividad"].isna().sum())
    return out, rep


def exactitud(riesgos: pd.DataFrame, actividades: pd.DataFrame, verdad: pd.Series) -> dict:
    """Cuanto acierta la inferencia: sobre las que hubo que inferir o corregir, y aplicada a todos (como si ninguno
    trajera la actividad). `verdad`: actividad real por id de riesgo (sin sufijo -DUP), del dato sintetico."""
    corte = pd.to_datetime(actividades["fecha_corte"]).max()
    por_paquete = {p: g for p, g in actividades.sort_values(["id_paquete", "orden"]).groupby("id_paquete")}
    base = riesgos["id_riesgo"].str.replace(r"-DUP\d*$", "", regex=True)
    real = base.map(verdad)
    hay = real.notna()
    rep = {}
    inferidas = hay & riesgos["actividad_origen"].isin(["inferida", "corregida"])
    if inferidas.any():
        rep["actividad_exactitud_inferidas"] = round(float((riesgos.loc[inferidas, "id_actividad"] == real[inferidas]).mean()), 3)
    a_ciegas = [inferir(normalizar(f"{r.get('descripcion', '')} {r.get('causa', '')}"), r.get("categoria", ""), r["estado"],
                        r.get("fecha_materializacion"), por_paquete[r["id_paquete_trabajo"]], corte)
                for _, r in riesgos[hay].iterrows()]
    if a_ciegas:
        rep["actividad_exactitud_a_ciegas"] = round(float((pd.Series(a_ciegas, index=riesgos[hay].index) == real[hay]).mean()), 3)
    return rep
