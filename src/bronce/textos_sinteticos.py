"""
Textos SINTETICOS del registro de riesgos: descripcion, causa y accion de tratamiento redactadas como en un registro real
(texto libre de Excel o de un reporte de campo), para que el paso Bronce -> Plata tenga que leerlas con el clasificador
de texto (src/modelo/texto.py).

A proposito, como en un registro real:
  * el vocabulario se cruza entre categorias ("bloqueo de la via" puede ser social o logistico; "lluvias", climatico o
    logistico), asi que clasificar no es trivial;
  * ~8 % de los riesgos llega sin categoria o con una ilegible ("Otro", "N/A", "Por definir"), y ~3 % con una categoria
    equivocada (quien diligencio el Excel eligio otra);
  * ~4 % menciona un municipio lejano al de su paquete (un error de digitacion o de ubicacion).
Usa su propio generador aleatorio para no cambiar el resto de los datos sinteticos. No nombra comunidades, rancherias ni
personas reales: solo los municipios de La Guajira, como referencia de ubicacion.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

MUNICIPIO_PROYECTO = {"PRY-01": "Uribia", "PRY-02": "Maicao", "PRY-03": "San Juan del Cesar"}
MUNICIPIO_LEJANO = {"PRY-01": ["San Juan del Cesar", "Fonseca", "Distracción"], "PRY-02": ["Distracción", "Urumita"],
                    "PRY-03": ["Uribia", "Manaure"]}
CATEGORIA_ILEGIBLE = ["", "Otro", "N/A", "Por definir", "Varios"]

AMENAZAS = {
    "seguridad_fisica": [
        "Extorsión a contratistas del frente de obra en zona rural de {municipio}",
        "Hurto de cable y material eléctrico en el campamento",
        "Amenazas a trabajadores por grupos armados en el corredor hacia {municipio}",
        "Robo de combustible y herramientas durante la noche en el patio de maquinaria",
        "Retención ilegal de un vehículo de la obra en la vía a {municipio}",
        "Cobro ilegal de peajes informales para dejar pasar la carga del proyecto",
        "Ataque con explosivos artesanales a la infraestructura del proyecto",
        "Asalto a camiones de suministro en la troncal cerca de {municipio}",
    ],
    "social_comunidad": [
        "Bloqueo de la vía de acceso por la comunidad wayuu que exige empleo local",
        "Inconformidad de las autoridades tradicionales con el proceso de consulta previa",
        "Paro de transportadores locales que exigen contratar vehículos de {municipio}",
        "Reclamos de la comunidad por afectación de jagüeyes y fuentes de agua",
        "Protesta de pobladores por compromisos sociales incumplidos en {municipio}",
        "Desacuerdo entre familias de la comunidad por la compensación del paso de la línea",
        "Toma pacífica del campamento por líderes comunitarios",
        "La comunidad no permite el ingreso de la cuadrilla al predio sin acuerdo previo",
    ],
    "ambiental": [
        "Derrame de aceite de la maquinaria sobre el suelo cerca de un arroyo",
        "Afectación de bosque seco tropical por el despeje del corredor",
        "Incumplimiento de obligaciones de la licencia ambiental en el frente de obra",
        "Polvo de la obra que afecta viviendas vecinas en {municipio}",
        "Intervención de un cauce sin permiso de ocupación durante la temporada de lluvias",
        "Manejo inadecuado de residuos sólidos y aceites usados en el campamento",
        "Atropellamiento de fauna silvestre por el tránsito de maquinaria",
        "Requerimiento de la autoridad ambiental por vertimientos sin permiso",
    ],
    "climatico": [
        "Inundación del frente de obra por crecientes súbitas de arroyos",
        "Lluvias intensas que suspenden las excavaciones varios días",
        "Vendaval que daña estructuras temporales y torres en montaje en {municipio}",
        "Sequía prolongada que limita el agua disponible para la obra",
        "Erosión de taludes recién intervenidos por aguaceros fuertes",
        "Altas temperaturas que obligan a reducir la jornada en campo",
        "Tormenta eléctrica que obliga a detener los trabajos en altura",
        "Creciente que inunda el acceso al campamento en {municipio}",
    ],
    "logistico_acceso": [
        "Vías destapadas intransitables que retrasan la llegada de materiales",
        "Retraso en el transporte de equipos pesados por el estado de los puentes",
        "Desabastecimiento de combustible en {municipio} para la maquinaria",
        "Cierre de la vía principal que obliga a desvíos largos para la carga",
        "Demoras en la nacionalización de equipos importados en el puerto",
        "Falta de transporte para el personal desde {municipio}",
        "Daño de la carretera por el paso de tractomulas sobredimensionadas",
        "El frente de obra solo tiene acceso en temporada seca",
    ],
    "contractual": [
        "Incumplimiento del contratista en la entrega de la ingeniería de detalle",
        "Retraso del proveedor en la entrega de transformadores",
        "Reclamación del contratista por mayores cantidades de obra",
        "Falta de liquidez del subcontratista para pagar la nómina",
        "Cambio de alcance sin aprobar que paraliza un frente de trabajo",
        "Disputa contractual por la interpretación de las especificaciones técnicas",
        "Alta rotación del personal técnico del contratista en {municipio}",
        "Demora en la aprobación de pólizas y garantías del contrato",
    ],
}
OPORTUNIDADES = {
    "seguridad_fisica": ["Convenio con la fuerza pública que mejora la seguridad del corredor hacia {municipio}",
                         "Red de comunicación comunitaria que avisa a tiempo sobre incidentes en la vía"],
    "social_comunidad": ["Acuerdo con la comunidad para contratar mano de obra local capacitada",
                         "Programa de inversión social que fortalece la relación con las autoridades tradicionales de {municipio}"],
    "ambiental": ["Compensación ambiental con viveros comunitarios de bosque seco",
                  "Reutilización del material de excavación en obras del municipio de {municipio}"],
    "climatico": ["Temporada seca más larga de lo normal que permite adelantar excavaciones",
                  "Pronóstico de lluvias bajo lo normal que facilita el montaje en {municipio}"],
    "logistico_acceso": ["Mejoramiento de la vía terciaria en convenio con la alcaldía de {municipio}",
                         "Nueva ruta de cargue que acorta el transporte de equipos"],
    "contractual": ["Proveedor regional que reduce los tiempos de entrega de materiales",
                    "Negociación que adelanta la entrega de equipos principales"],
}
CAUSAS = {
    "seguridad_fisica": ["Presencia de economías ilegales en la zona", "Contrabando de combustible en la frontera",
                         "Poca presencia de la fuerza pública en el área rural", "Rutas de transporte sin escolta ni horarios controlados",
                         "Antecedentes de extorsión en el municipio"],
    "social_comunidad": ["Expectativas de empleo no atendidas", "Acuerdos de la consulta previa sin seguimiento",
                         "Socialización insuficiente del proyecto con las autoridades tradicionales",
                         "Necesidades básicas insatisfechas en el área de influencia", "Disputas por el territorio entre familias"],
    "ambiental": ["Mantenimiento deficiente de equipos", "Plan de manejo ambiental sin seguimiento",
                  "Cercanía a ecosistemas sensibles", "Falta de permisos de ocupación de cauce", "Capacitación ambiental insuficiente"],
    "climatico": ["Temporada de lluvias más intensa de lo normal", "Variabilidad climática por el fenómeno de La Niña",
                  "Drenajes temporales insuficientes", "Frente de obra en zona inundable", "Vientos fuertes en la temporada seca"],
    "logistico_acceso": ["Red vial terciaria en mal estado", "Dependencia de un solo corredor de acceso",
                         "Lejanía de los centros de abastecimiento", "Planeación logística sin rutas alternas", "Trámites aduaneros demorados"],
    "contractual": ["Contratista sin experiencia en la región", "Cláusulas de penalización débiles",
                    "Cadena de suministro global congestionada", "Alcance del contrato incompleto", "Pagos atrasados al subcontratista"],
}
ACCIONES = {
    "seguridad_fisica": ["Coordinar con la fuerza pública y ajustar el esquema de seguridad", "Cambiar horarios y rutas de la carga",
                         "Reforzar vigilancia y control de acceso al campamento"],
    "social_comunidad": ["Mesa de diálogo con las autoridades tradicionales", "Plan de contratación de mano de obra local",
                         "Seguimiento mensual de los acuerdos de la consulta previa"],
    "ambiental": ["Activar el plan de contingencia de derrames", "Tramitar el permiso de ocupación de cauce",
                  "Inspección ambiental semanal del frente de obra"],
    "climatico": ["Construir drenajes y seguir las alertas del IDEAM", "Reprogramar las excavaciones a la temporada seca",
                  "Protocolo de suspensión por tormenta eléctrica"],
    "logistico_acceso": ["Habilitar una ruta alterna y acopiar materiales con anticipación", "Contratar transporte de respaldo",
                         "Mantenimiento preventivo de la vía de acceso"],
    "contractual": ["Comité semanal de seguimiento al contratista", "Aplicar las multas del contrato y exigir un plan de choque",
                    "Buscar un proveedor alterno"],
}


# Actividades del cronograma que puede afectar cada plantilla, de la mas a la menos probable (claves de
# cronograma_sintetico.ACTIVIDADES). Es la "verdad" del dato sintetico: el registro la escribe como le parece a quien lo
# llena (codigo, nombre o nada) y Plata la tiene que reconstruir.
ACTIVIDADES_DE = {
    # seguridad fisica
    "Extorsión a contratistas del frente de obra en zona rural de {municipio}": ("civil", "montaje"),
    "Hurto de cable y material eléctrico en el campamento": ("montaje", "compras"),
    "Amenazas a trabajadores por grupos armados en el corredor hacia {municipio}": ("civil", "montaje"),
    "Robo de combustible y herramientas durante la noche en el patio de maquinaria": ("civil", "montaje"),
    "Retención ilegal de un vehículo de la obra en la vía a {municipio}": ("compras", "civil"),
    "Cobro ilegal de peajes informales para dejar pasar la carga del proyecto": ("compras",),
    "Ataque con explosivos artesanales a la infraestructura del proyecto": ("montaje", "pruebas", "civil"),
    "Asalto a camiones de suministro en la troncal cerca de {municipio}": ("compras",),
    # social
    "Bloqueo de la vía de acceso por la comunidad wayuu que exige empleo local": ("civil", "montaje", "social"),
    "Inconformidad de las autoridades tradicionales con el proceso de consulta previa": ("social",),
    "Paro de transportadores locales que exigen contratar vehículos de {municipio}": ("compras", "civil"),
    "Reclamos de la comunidad por afectación de jagüeyes y fuentes de agua": ("civil", "ambiental"),
    "Protesta de pobladores por compromisos sociales incumplidos en {municipio}": ("social", "civil"),
    "Desacuerdo entre familias de la comunidad por la compensación del paso de la línea": ("social",),
    "Toma pacífica del campamento por líderes comunitarios": ("civil", "montaje"),
    "La comunidad no permite el ingreso de la cuadrilla al predio sin acuerdo previo": ("civil", "social"),
    # ambiental
    "Derrame de aceite de la maquinaria sobre el suelo cerca de un arroyo": ("civil", "montaje"),
    "Afectación de bosque seco tropical por el despeje del corredor": ("civil",),
    "Incumplimiento de obligaciones de la licencia ambiental en el frente de obra": ("ambiental", "civil"),
    "Polvo de la obra que afecta viviendas vecinas en {municipio}": ("civil",),
    "Intervención de un cauce sin permiso de ocupación durante la temporada de lluvias": ("ambiental", "civil"),
    "Manejo inadecuado de residuos sólidos y aceites usados en el campamento": ("civil", "montaje", "cierre"),
    "Atropellamiento de fauna silvestre por el tránsito de maquinaria": ("civil", "compras"),
    "Requerimiento de la autoridad ambiental por vertimientos sin permiso": ("ambiental", "civil"),
    # climatico
    "Inundación del frente de obra por crecientes súbitas de arroyos": ("civil",),
    "Lluvias intensas que suspenden las excavaciones varios días": ("civil",),
    "Vendaval que daña estructuras temporales y torres en montaje en {municipio}": ("montaje",),
    "Sequía prolongada que limita el agua disponible para la obra": ("civil",),
    "Erosión de taludes recién intervenidos por aguaceros fuertes": ("civil",),
    "Altas temperaturas que obligan a reducir la jornada en campo": ("civil", "montaje"),
    "Tormenta eléctrica que obliga a detener los trabajos en altura": ("montaje", "pruebas"),
    "Creciente que inunda el acceso al campamento en {municipio}": ("civil", "montaje"),
    # logistico
    "Vías destapadas intransitables que retrasan la llegada de materiales": ("compras", "civil"),
    "Retraso en el transporte de equipos pesados por el estado de los puentes": ("compras", "montaje"),
    "Desabastecimiento de combustible en {municipio} para la maquinaria": ("civil", "montaje"),
    "Cierre de la vía principal que obliga a desvíos largos para la carga": ("compras",),
    "Demoras en la nacionalización de equipos importados en el puerto": ("compras",),
    "Falta de transporte para el personal desde {municipio}": ("civil", "montaje"),
    "Daño de la carretera por el paso de tractomulas sobredimensionadas": ("compras", "montaje"),
    "El frente de obra solo tiene acceso en temporada seca": ("civil",),
    # contractual
    "Incumplimiento del contratista en la entrega de la ingeniería de detalle": ("ingenieria",),
    "Retraso del proveedor en la entrega de transformadores": ("compras",),
    "Reclamación del contratista por mayores cantidades de obra": ("civil", "cierre"),
    "Falta de liquidez del subcontratista para pagar la nómina": ("civil", "montaje"),
    "Cambio de alcance sin aprobar que paraliza un frente de trabajo": ("ingenieria", "civil", "montaje"),
    "Disputa contractual por la interpretación de las especificaciones técnicas": ("ingenieria", "compras", "pruebas"),
    "Alta rotación del personal técnico del contratista en {municipio}": ("montaje", "pruebas", "ingenieria"),
    "Demora en la aprobación de pólizas y garantías del contrato": ("compras", "cierre"),
    # oportunidades
    "Convenio con la fuerza pública que mejora la seguridad del corredor hacia {municipio}": ("civil", "montaje"),
    "Red de comunicación comunitaria que avisa a tiempo sobre incidentes en la vía": ("compras", "civil"),
    "Acuerdo con la comunidad para contratar mano de obra local capacitada": ("civil", "montaje"),
    "Programa de inversión social que fortalece la relación con las autoridades tradicionales de {municipio}": ("social",),
    "Compensación ambiental con viveros comunitarios de bosque seco": ("ambiental", "cierre"),
    "Reutilización del material de excavación en obras del municipio de {municipio}": ("civil",),
    "Temporada seca más larga de lo normal que permite adelantar excavaciones": ("civil",),
    "Pronóstico de lluvias bajo lo normal que facilita el montaje en {municipio}": ("montaje",),
    "Mejoramiento de la vía terciaria en convenio con la alcaldía de {municipio}": ("compras", "civil"),
    "Nueva ruta de cargue que acorta el transporte de equipos": ("compras", "montaje"),
    "Proveedor regional que reduce los tiempos de entrega de materiales": ("compras",),
    "Negociación que adelanta la entrega de equipos principales": ("compras", "montaje"),
}


def redactar(df: pd.DataFrame, categorias: list[str], tipos: list[str], semilla: int,
             actividades: list[str | None] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reemplaza descripcion, causa y accion por texto libre realista y ensucia la categoria de ~8 % de los riesgos.
    Devuelve el registro y la clave de evaluacion (categoria verdadera de cada riesgo y si su texto nombra un municipio
    lejano), que solo existe porque los datos son sinteticos: con ella se mide cuanto acierta la IA y cuantos errores
    sembrados detecta."""
    r = np.random.default_rng(semilla)
    rnd = random.Random(semilla)
    otra = np.random.default_rng(semilla + 1000)   # solo para cambiar la plantilla cuando no habla de la actividad
    df = df.copy()
    lejanos, plantillas = [], []
    for i in range(len(df)):
        cat, tipo, proyecto = categorias[i], tipos[i], df.at[i, "id_proyecto"]
        lejano = r.random() < 0.04
        lejanos.append(bool(lejano))
        municipio = rnd.choice(MUNICIPIO_LEJANO[proyecto]) if lejano else MUNICIPIO_PROYECTO[proyecto]
        lista = (AMENAZAS if tipo == "amenaza" else OPORTUNIDADES)[cat]
        plantilla = rnd.choice(lista)
        act = actividades[i] if actividades is not None else None
        if act and act not in ACTIVIDADES_DE.get(plantilla, ()):
            # el texto tiene que hablar de la actividad a la que pega el riesgo (si la categoria tiene como)
            compatibles = [p for p in lista if act in ACTIVIDADES_DE.get(p, ())]
            if compatibles:
                plantilla = compatibles[int(otra.integers(len(compatibles)))]
        plantillas.append(plantilla)
        texto = plantilla.format(municipio=municipio)
        if lejano and "{municipio}" not in plantilla:
            texto += f" (reportado en {municipio})"
        df.at[i, "descripcion"] = texto
        df.at[i, "causa"] = rnd.choice(CAUSAS[cat]) if tipo == "amenaza" else "Condición favorable identificada en campo"
        df.at[i, "accion_tratamiento"] = rnd.choice(ACCIONES[cat]) if tipo == "amenaza" else "Plan para aprovechar la oportunidad"
        sorteo = r.random()
        if sorteo < 0.08:
            df.at[i, "categoria"] = rnd.choice(CATEGORIA_ILEGIBLE)
        elif sorteo < 0.11:
            df.at[i, "categoria"] = rnd.choice([c for c in AMENAZAS if c != cat])
    clave = pd.DataFrame({"id_riesgo": df["id_riesgo"], "categoria_real": categorias, "ubicacion_lejana": lejanos, "plantilla": plantillas})
    return df, clave
