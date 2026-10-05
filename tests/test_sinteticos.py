"""Los datos inventados deben quedar sobre tierra firme de La Guajira (no en el mar ni en otro departamento)."""
import sys
from pathlib import Path

import geopandas as gpd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bronce import sinteticos as s  # noqa: E402
from comun import marco_guajira as marco  # noqa: E402


def test_el_contorno_de_referencia_es_la_guajira():
    t = marco.tierra()
    assert t.is_valid and t.geom_type == "Polygon"
    area_km2 = gpd.GeoSeries([t], crs=4326).to_crs(3116).area.iloc[0] / 1e6
    assert area_km2 == pytest.approx(20670, rel=0.01)            # area oficial del departamento
    assert marco.esta_en_tierra(gpd.GeoSeries.from_xy([-72.45], [11.55], crs=4326).iloc[0])     # Riohacha, en la costa, a ~2 km del mar
    assert not marco.esta_en_tierra(gpd.GeoSeries.from_xy([-72.7], [12.1], crs=4326).iloc[0])   # mar abierto al norte
    assert not marco.esta_en_tierra(gpd.GeoSeries.from_xy([-71.0], [11.0], crs=4326).iloc[0])   # Venezuela


def test_un_centro_factible_deja_el_circulo_entero_en_tierra():
    cx, cy = marco.centro_factible_mas_cercano((-72.25, 11.75), 0.19)
    circulo = gpd.GeoSeries.from_xy([cx], [cy], crs=4326).iloc[0].buffer(0.19)
    assert marco.tierra().contains(circulo)
    assert marco.centro_factible_mas_cercano((-72.25, 11.75), 5.0) is None    # un circulo de 5 grados no cabe


def test_proyectos_y_paquetes_caen_en_tierra_y_los_paquetes_dentro_de_su_proyecto():
    proy, paq = s.generar_proyectos_y_paquetes()
    zona = marco.tierra_interior(s.MARGEN_BORDE)
    assert proy.geometry.apply(zona.contains).all()
    assert paq.geometry.apply(zona.contains).all()
    por_id = proy.set_index("id_proyecto").geometry
    assert all(g.within(por_id[i]) for g, i in zip(paq.geometry, paq["id_proyecto"]))
    # norte, centro y sur siguen en ese orden
    lats = [g.centroid.y for g in proy.geometry]
    assert lats[0] > lats[1] > lats[2]


def test_comunidades_areas_rios_y_vias_caen_en_tierra():
    zona = marco.tierra_interior(s.MARGEN_BORDE).buffer(1e-9)       # tolerancia de coma flotante: los rios se cortan justo en ese borde
    assert s.generar_comunidades().geometry.apply(zona.contains).all()
    assert s.generar_areas_protegidas().geometry.apply(zona.contains).all()
    assert s.generar_hidrologia().geometry.apply(zona.contains).all()
    assert s.generar_vias().geometry.apply(zona.contains).all()


def test_las_estaciones_del_clima_simulado_caen_en_tierra():
    clima = s.generar_clima(dias=2, n_estaciones=5).drop_duplicates("id_estacion")
    puntos = gpd.GeoSeries.from_xy(clima["lon"], clima["lat"], crs=4326)
    assert puntos.apply(marco.tierra_interior(s.MARGEN_COSTA).contains).all()


def test_cada_riesgo_con_coordenadas_cae_dentro_de_su_paquete():
    proy, paq = s.generar_proyectos_y_paquetes()
    com, areas = s.generar_comunidades(), s.generar_areas_protegidas()
    riesgos = s.generar_registro_riesgos(paq, com, areas).dropna(subset=["lat", "lon"])
    geom = paq.set_index("id_paquete").geometry
    puntos = gpd.GeoSeries.from_xy(riesgos["lon"], riesgos["lat"], crs=4326)
    assert all(geom[i].contains(p) for i, p in zip(riesgos["id_paquete_trabajo"], puntos))
