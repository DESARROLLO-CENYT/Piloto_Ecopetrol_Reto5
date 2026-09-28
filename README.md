# Piloto Reto 5 · Mapa de riesgos multicriterio

Piloto del **Índice de Criticidad Territorial (ICT)** para la convocatoria
*Transforma la Energía* (Reto 5, Grupo Ecopetrol), desarrollado por CEN&T
Ingenieros Consultores. Recorre de punta a punta el flujo de la propuesta:
arquitectura medallion (Bronce → Plata → Oro), modelo multicriterio explicable,
mapa de calor, alertas tempranas y una aplicación web para explorarlo.

> **Datos sintéticos.** Nada de lo que hay aquí es información real de
> Ecopetrol, de La Guajira ni de ninguna comunidad. Proyectos, paquetes de
> trabajo, comunidades, áreas protegidas, clima y el registro de riesgos los
> genera `src/generar_datos.py`. El piloto sirve para validar el mecanismo del
> modelo y el flujo de datos, no para sacar conclusiones sobre riesgos reales.

## Inicio rápido

Requisitos: [Git](https://git-scm.com/downloads), **Python 3.12** e internet
(la interfaz carga fuentes, mapas base, gráficos e iconos desde CDN).

```bash
git clone https://github.com/DESARROLLO-CENYT/Piloto_Ecopetrol_Reto5.git
cd Piloto_Ecopetrol_Reto5
py -3.12 iniciar.py
```

En Mac o Linux el último comando es `python3.12 iniciar.py`. En Windows también
sirve doble clic sobre `iniciar.bat`.

`iniciar.py` hace solo lo que falte, en este orden:

1. Crea el entorno virtual en una carpeta local del PC
   (`%LOCALAPPDATA%\reto5-piloto` en Windows, `~/.cache/reto5-piloto` en Mac/Linux).
2. Instala `requirements.txt` la primera vez (unos minutos) o cuando cambie.
3. Genera los datos si no existe la capa Oro (menos de un minuto).
4. Levanta la aplicación en `http://127.0.0.1:8000` y abre el navegador.

| Opción | Para qué |
|---|---|
| `--regenerar` | Vuelve a generar los datos aunque ya existan |
| `--red` | Permite abrir la aplicación desde otros PC de la red local (muestra la IP) |
| `--puerto 8001` | Usa otro puerto si el 8000 está ocupado |
| `--sin-navegador` | No abre el navegador |

`Ctrl+C` en la terminal detiene el servidor.

### Actualizar a la última versión

Desde la carpeta del repositorio:

```bash
git pull
py -3.12 iniciar.py
```

Si cambió `requirements.txt`, `iniciar.py` reinstala las dependencias solo.
Si cambió el modelo o el generador de datos, agrega `--regenerar`.

## Qué incluye

**Aplicación** (`app/`, FastAPI + Leaflet + Chart.js, sin paso de compilación):

- **Inicio**: resumen con el ICT promedio y la distribución de riesgos.
- **Mapa**: paquetes coloreados por nivel sobre mapa satelital y de calor,
  alertas, filtros, capas de contexto, pesos del modelo ajustables en vivo y
  tarjeta de detalle con el radar de criterios.
- **Explorar**: registro de riesgos ordenable y filtrable, riesgos por
  categoría y por semana, paquetes prioritarios.
- **Datos y modelo**: arquitectura medallion, qué datos se crearon, catálogo
  de tablas con su linaje y la explicación del ICT, todo leído en vivo de los
  archivos.

**Pipeline y modelo** (`src/`):

- `generar_datos.py`: datos sintéticos de entrada (capa Bronce), "sucios" a
  propósito: duplicados, vacíos, textos inconsistentes, ~12 % sin coordenadas.
- `bronce_a_plata.py`: limpieza, deduplicación, taxonomía y geolocalización.
- `plata_a_oro.py`: los cinco criterios, el ICT, niveles, escalamiento,
  tendencia, mapa de calor (KDE) y Getis-Ord Gi*.
- `validacion.py`: backtest y análisis de sensibilidad de los pesos.
- `exportar_gis.py`: GeoPackage para ArcGIS o QGIS.
- `modelo/ict.py`, `modelo/ahp.py`, `modelo/espacial.py`: el motor del ICT,
  la derivación de pesos por AHP y la estadística espacial.

Los parámetros del modelo (pesos, umbrales, radios de influencia) viven en
[`parametros.yaml`](parametros.yaml), separados del código.

## Comandos individuales

Con el entorno que crea `iniciar.py` (en Windows,
`%LOCALAPPDATA%\reto5-piloto\venv\Scripts\python.exe`; abajo abreviado como `python`):

```bash
python ejecutar_pipeline.py          # pasos 1-4: datos, limpieza, ICT y validación
python run_app.py                    # solo el servidor
python -m pytest tests/ -v           # pruebas del modelo
cd src && python exportar_gis.py     # GeoPackage en exports/
```

### Instalación manual (sin `iniciar.py`)

```bash
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe ejecutar_pipeline.py
.venv/Scripts/python.exe run_app.py
```

En Mac o Linux: `python3.12 -m venv .venv` y `.venv/bin/python` en lugar de
`.venv/Scripts/python.exe`.

## Guion de demo (5 a 7 minutos)

1. **Inicio** (`http://127.0.0.1:8000`): ICT promedio y riesgos por categoría
   con datos vivos. Señalar el chip "Datos sintéticos" de la barra superior.
2. **Mapa**: los 14 paquetes coloreados por nivel sobre el mapa de calor. Clic
   en una alerta del carrusel inferior o en un paquete: la tarjeta de detalle
   muestra el ICT, la causa de escalamiento y el **radar de criterios frente al
   promedio del portafolio**. Es el punto central: el modelo es explicable.
3. **Pestaña "Alertas"**: las causas están encadenadas al ICT para evitar
   falsos positivos.
4. **Pestaña "Modelo"**: mover los pesos y pulsar "Recalcular". Cambian en vivo
   el ranking de zonas prioritarias, los colores y las alertas, sin tocar
   código. "Restablecer" vuelve a los pesos por defecto.
5. **Pestaña "Filtros" y botón de capas**: riesgos por categoría, estado y
   tipo; comunidades, áreas protegidas, hidrología y vías; satélite o mapa claro.
6. **"Ver en datos"** desde la tarjeta de detalle: abre Explorar filtrado por
   ese paquete. Un clic en una barra de categoría filtra el registro.
7. **Datos y modelo**: qué entra en Bronce, qué limpia Plata, qué produce Oro,
   las imperfecciones plantadas, el catálogo de tablas y el ICT del paquete más
   crítico descompuesto por criterio.
8. **Validación**: mostrar el backtest y la sensibilidad, aclarando que el
   backtest es circular (ver limitaciones).
9. **Cierre**: el GeoPackage (`exports/reto5_piloto.gpkg`) abierto en QGIS o
   ArcGIS, para mostrar que la salida no depende de un software SIG.

## Limitaciones (leer antes de mostrar el piloto)

- **Backtest circular**: los eventos materializados sintéticos se generaron
  con las mismas variables que usa el modelo. Confirma que el mecanismo
  funciona, **no** que los pesos o criterios sean los correctos; eso requiere
  el histórico real de Ecopetrol.
- **Pesos supuestos**: los de `parametros.yaml` son un punto de partida, no
  una calibración con expertos (Fase 2 de la propuesta).
- **Geografía de referencia, entidades ficticias**: se usa el marco de La
  Guajira solo para ubicar objetos inventados. La silueta de la portada es un
  contorno aproximado, no el límite oficial del DANE o IGAC.
- **IA y ML fuera de alcance**, a propósito: están en la sección de opciones de
  mejora de la propuesta.
- **Este stack no es la arquitectura de producción.** La propuesta plantea
  Azure Data Lake Storage Gen2, Databricks con Sedona, ArcGIS Enterprise y
  Power BI; el piloto usa archivos locales y Python / GeoPandas con la misma
  lógica, para poder migrarla sin reescribirla.

## Estructura

```
iniciar.py / iniciar.bat     arranque con un solo comando
parametros.yaml              pesos, umbrales y radios del modelo
ejecutar_pipeline.py         corre los pasos 1-4 en orden
run_app.py                   levanta solo el servidor
requirements.txt             dependencias con versiones fijas
src/                         pipeline Bronce -> Plata -> Oro y el modelo
  modelo/                    ICT, AHP y estadística espacial
app/
  main.py                    API (FastAPI)
  catalogo.py                inventario vivo de las capas para /api/catalogo
  static/                    interfaz: HTML, CSS y JS sin compilación
tests/                       pruebas unitarias del modelo
multimedia/                  logos e imágenes de referencia de diseño
.claude/skills/reto5-design/ sistema de diseño de la interfaz
data/, exports/              se generan al correr el pipeline (no se versionan)
```

El diseño de la interfaz sigue la skill de proyecto
`.claude/skills/reto5-design/` (tokens, componentes y recetas derivados de las
imágenes de `multimedia/`). Si cambias `tokens.css` o `components.css`, hazlo
en la skill y cópialo a `app/static/`.
