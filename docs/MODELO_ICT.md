# Índice de Criticidad Territorial (ICT)

**Pregunta que responde:** ¿qué paquetes de trabajo y qué zonas concentran la mayor exposición al riesgo, dónde un evento
podría escalar a crisis y qué conviene intervenir primero?

El ICT cruza el **registro de riesgos** (calificado con la matriz RAM de Ecopetrol) con el **territorio real** de cada
paquete. Hoy el registro y los paquetes son sintéticos; el territorio sale de datos abiertos oficiales:
- **ANT:** resguardos indígenas.
- **DANE:** censo 2018 y Marco Geoestadístico.
- **RUNAP:** áreas protegidas.
- **INVIAS e IGAC:** red vial.
- **IDEAM:** lluvia diaria de las estaciones.
- **CHIRPS:** lluvia mensual por satélite.
- **UNGRD:** emergencias.
- **Ministerio de Defensa:** delitos.

| | |
|---|---|
| Motor | `src/modelo/ict.py` (criterios), `src/modelo/territorio.py` (variables reales), `src/modelo/espacial.py` (kernel y Gi*), `src/modelo/texto.py` (IA sobre el texto) |
| Paso del pipeline | `oro.ict` (`src/oro/ict.py`); boletín diario en `consumo.alertas` |
| Parámetros | `parametros.yaml` → `pesos`, `umbrales_criticidad`, `criterios`, `escalamiento`, `factores_estado`, `radios_influencia_m`; lo editado desde la aplicación, en `modelo_personalizado.yaml` |
| Salidas (Oro) | `paquetes_ict.geojson`, `puntos_crisis.geojson`, `zonas_intervencion.geojson`, `grid_calor.geojson`, `alertas.json` |
| Vistas | Mapa (color por ICT, escalamiento, mapa de calor, alertas), Explorar, Ajustar (pesos, AHP, umbrales, reglas) |
| Pruebas y auditoría | `tests/test_ict.py`, `tests/test_ict_territorio.py`, `tests/test_alertas.py`, `tests/test_texto.py`, `tests/test_modelo_config.py`; la auditoría comprueba que el ICT es la suma de sus aportes, que cada criterio está en su escala y que cada punto de crisis es de un paquete en escalamiento |

## 1. Formulación

```
ICT(z) = 100 × Σk wk · Ck(z)        Σ wk = 1,   0 ≤ Ck(z) ≤ 1
```

**Escala fija.** Cada criterio *Ck* vale de 0 a 1 contra un tope definido en `parametros.yaml`, no contra los demás paquetes. Así el ICT de un paquete no cambia porque se agregue otro, y dos fechas se comparan sin reescalar.

**Sin imputar.** Un componente sin dato no se cuenta como cero: el criterio se calcula con los componentes que sí tienen dato, y la falta baja el índice de confianza.

| Criterio | Peso base | Cómo se calcula (0 a 1) | Fuentes |
|---|---|---|---|
| Severidad de los riesgos | 0,28 | 0,7 × la amenaza más severa que alcanza el paquete + 0,3 × el promedio ponderado por severidad; severidad = puntaje del nivel RAM residual (N=1 … VH=5) × factor de estado (latente 1, próximo 1,3, materializado 1,6); dividido por el peor caso (VH materializado = 8) | Registro + RAM |
| Exposición del paquete | 0,20 | 0,5 × ruta crítica + 0,5 × amenazas abiertas que lo alcanzan / 20 | Cronograma + registro |
| Vulnerabilidad del territorio | 0,22 | Promedio ponderado (las fórmulas, en la tabla siguiente): territorio étnico 0,30, pobreza 0,25, áreas protegidas 0,25, acceso 0,20 | ANT, DANE, RUNAP, INVIAS + IGAC |
| Amenazas externas | 0,15 | Promedio ponderado (las fórmulas, en la tabla siguiente): lluvia reciente 0,30, lluvia anómala 0,15, emergencias 0,25, delitos 0,30 | IDEAM, CHIRPS, UNGRD, MinDefensa |
| Convergencia | 0,15 | (categorías de amenaza abiertas con nivel RAM M o más que lo alcanzan + factores externos ≥ 0,6) / 5 | Registro + territorio |

**Cómo se calcula cada componente del territorio:**

| Componente | Fórmula |
|---|---|
| Territorio étnico | máx(fracción del paquete en resguardo; 0,5 × decaimiento hasta 5 km) |
| Pobreza | IPM / 100 |
| Áreas protegidas | máx(fracción dentro; decaimiento hasta 10 km) |
| Acceso | fracción de km de vías a menos de 10 km que solo se transitan en tiempo seco |
| Lluvia reciente | mm de 14 días / 80 |
| Lluvia anómala | \|desviación de 3 meses\| / 100 % |
| Emergencias | emergencias por año / 15 |
| Delitos | delitos por 100.000 hab. / 80 |

**Alcance espacial de las amenazas.** Una amenaza asignada al paquete en el registro lo alcanza entera. La de un paquete vecino lo alcanza con un peso que decae linealmente con la distancia, hasta 0 en el radio de influencia de su categoría (`radios_influencia_m`: social 3 km, seguridad 5 km, climático 8 km…). Así la severidad, la exposición y la convergencia son cruces espaciales, no solo una suma por identificador.

**Lluvia al día.** Cuenta la estación del IDEAM más cercana que tenga al menos 10 de los últimos 14 días con dato y esté a menos de 20 km. Si ninguna cumple, el componente queda sin dato: una serie vieja o una estación lejana no representan la lluvia de hoy.

**Niveles.** Con el ICT se clasifica cada paquete:
- **Bajo:** menos de 25.
- **Medio:** de 25 a 49.
- **Alto:** de 50 a 74.
- **Crítico:** 75 o más.

Los umbrales son editables.

**Índice de confianza:**

```
confianza = Σk wk · disponibilidadk
```

La disponibilidad de un criterio es la fracción de su peso que tuvo dato al día. Un paquete sin ningún riesgo en el registro cuenta como no evaluado.

## 2. Escalamiento a crisis

Un paquete escala si se cumple al menos una de estas reglas (todas configurables):

| Regla | Dónde se ubica en el mapa |
|---|---|
| ICT de 75 o más | Centro del paquete |
| Amenaza abierta con nivel RAM residual muy alto (VH), intolerable según la RAM | La amenaza |
| Amenaza alta (H) en un paquete de ruta crítica | La amenaza |
| Amenaza H o VH cuya área de influencia alcanza un resguardo indígena (categorías social y ambiental) o un área protegida (ambiental y climático), con las capas reales | La amenaza |
| Convergen 4 o más amenazas (registro + territorio) con un ICT de 50 o más | Centro del paquete |
| 3 o más acciones de tratamiento vencidas con un ICT de 50 o más | Centro del paquete |

**Puntos de crisis y zonas de intervención.** Cada punto de crisis lleva:
- su causa;
- la decisión que exige la RAM y quién decide;
- su acción de tratamiento, con la fecha y si ya está vencida.

La **zona de intervención prioritaria** de un paquete es la unión de los círculos de influencia de sus puntos de crisis.

**Alertas.** Hay una alerta por cada paquete en escalamiento, o cuyo ICT subió 10 o más puntos en 7 días. Cada alerta incluye:
- la prioridad (crítica si hay un VH o un ICT crítico);
- las causas y los puntos de crisis;
- qué hacer: la decisión de la RAM, el relacionamiento con el resguardo que se alcanza, la coordinación ambiental y la actualización de acciones vencidas.

## 3. Mapa de calor y estadística espacial

- **Densidad kernel** (gaussiano, banda de 4 km) de las amenazas, ponderada por nivel RAM y estado, sobre una grilla de 0,02° (~2 km). Las oportunidades abiertas tienen su propia superficie: no se restan de las amenazas.
- **Puntos calientes (Getis-Ord Gi\*)** sobre las celdas del área de estudio. El valor de cada celda es la severidad de las amenazas que caen en ella, sin suavizar; se usan 8 vecinas por celda. Una celda con z ≥ 1,96 es un conglomerado significativo al 95 %. No se aplica sobre los 14 paquetes, porque con tan pocas unidades ningún conglomerado podría ser significativo.

## 4. Tendencia y alertas diarias

**Tendencia.** Es el ICT de hace 7 días calculado con la misma escala fija. El cambio viene de los riesgos (fechas de identificación y materialización) y de la lluvia, no de un reescalado.

**Tarea diaria** (`src/tarea_diaria.py`):
1. Descarga el IDEAM.
2. Recalcula el ICT y todo lo que depende de él.
3. Compara las alertas con el corte anterior (nuevas, suben, siguen, resueltas) y escribe el boletín en `exports/alertas/`.
4. Avisa por Teams o por correo si esos canales están activos.

**Cómo se ejecuta:**
- **Con la aplicación encendida:** la corre sola a las 06:00 (`alertas.hora_diaria`).
- **Sin la aplicación:** `python alertas_diarias.py` desde el Programador de tareas o cron (`--programar` muestra cómo).
- **A mano:** el botón "Actualizar ahora" del panel de alertas del mapa.

**Credenciales.** Las de los canales de aviso solo van en variables de entorno.

## 5. IA sobre el texto del registro

El registro real llega en Excel con texto libre. El paso `plata.sinteticos` usa un clasificador bayesiano ingenuo multinomial (`src/modelo/texto.py`), entrenado con los riesgos que sí traen categoría. Lo que hace:
- **Categoría faltante:** la sugiere para los riesgos que no la traen, si la confianza es 0,6 o más.
- **Categoría contradicha:** marca para revisión los riesgos cuyo texto contradice la categoría registrada con confianza de 0,8 o más. No la cambia sola.
- **Lugares:** busca municipios nombrados en el texto y marca los que quedan a más de 15 km del paquete.

**Trazabilidad:**
- Cada decisión deja su confianza y las palabras que más pesaron.
- La categoría original queda en `categoria_registrada`.
- El origen de la categoría final queda en `categoria_origen` (registro, ia o pendiente).

**Acierto.** Se mide con validación cruzada en 5 partes y, como los datos son sintéticos, también contra una clave con la categoría verdadera (`bronze/clave_categorias_sinteticas.csv`). Con el registro real se reentrena igual.

## 6. Configuración y versiones

**Qué se edita en la vista "Ajustar":**
- **Pesos:** directos o derivados con AHP (escala de Saaty y razón de consistencia, que debe ser 0,10 o menos).
- **Umbrales** de nivel.
- **Reglas** de escalamiento.
- **Componentes y topes** del territorio.
- **Factores de estado.**

**Antes de guardar.** La vista previa recalcula el ICT y el escalamiento de cada paquete sin guardar nada.

**Al guardar:**
- Los cambios van a `modelo_personalizado.yaml`; `parametros.yaml` no se toca.
- Se recalcula el ICT, la validación, la exportación y el boletín (unos 12 s).
- Queda una versión en `historial_parametros.jsonl` con quién, cuándo, por qué y los parámetros vigentes, para poder reproducir cualquier resultado con los parámetros de su fecha.

**Otras vistas.** La matriz RAM y los supuestos del riesgo de ejecución también dejan su versión en ese historial.

**Seguridad.** Desde otro equipo de la red, editar exige la clave de `RETO5_CLAVE_EDICION`; sin esa variable, solo se edita desde el equipo donde corre la aplicación.

## 7. Validación

- **Sensibilidad:** cada peso se mueve ±20 % y se mide la correlación del ranking (Spearman) y los paquetes que cambian de nivel.
- **Prueba de consistencia:** compara el ICT con los riesgos ya materializados. Es circular, porque los materializados entran al ICT: comprueba el mecanismo, no valida el modelo.
- **Validación real (Fase 4):** con el historial de Ecopetrol, se mira si las zonas señaladas coincidieron con los eventos y con cuánta anticipación, más la calibración de pesos y topes.

## 8. Limitaciones

- **Datos sintéticos:** el registro de riesgos y los paquetes son sintéticos; el territorio es real. Las cifras demuestran el mecanismo, no el riesgo real de ningún proyecto.
- **Supuestos de trabajo:** los topes, los pesos y las reglas deben fijarse con los expertos (Fase 2).
- **Lluvia:** cubre solo los paquetes con una estación del IDEAM al día a menos de 20 km; los demás quedan sin dato (y su confianza lo dice).
- **Territorio étnico:** que un paquete esté dentro de un resguardo indica dónde aplica la consulta previa y una mayor sensibilidad sociocultural, no una amenaza.
- **IA:** el clasificador aprende de textos sintéticos redactados con plantillas, así que su acierto real se sabrá con el registro de Ecopetrol.
