# Cronograma por actividades: avance y fechas

> **Datos sintéticos.** Proyectos, paquetes y actividades son inventados (`src/bronce/cronograma_sintetico.py`). Lo que se demuestra
> es el mecanismo: cómo un export de planeación (Primavera, MS Project, un Excel con WBS) se vuelve avance y fechas confiables.

## 1. Idea central

**La actividad es la única fuente.** Cada paquete de trabajo tiene entre 5 y 7 actividades en secuencia. De ellas se calcula hacia
arriba todo lo demás, así el avance de un proyecto nunca contradice sus actividades.

```
proyecto  ──  paquetes (peso = presupuesto del paquete / presupuesto del proyecto)
paquete   ──  actividades (peso_en_paquete, suman 1 por paquete)
actividad ──  peso_en_proyecto = peso_en_paquete × peso del paquete   (suman 1 por proyecto)
```

| Cálculo | Fórmula |
|---|---|
| Avance del paquete | Σ `peso_en_paquete` × `avance` de sus actividades |
| Avance del proyecto | Σ `peso_en_proyecto` × `avance` de todas sus actividades |
| Aporte de una actividad | `peso_en_proyecto` × `avance` (en puntos de 100: `aporte_avance_pp`; lo que aportará al terminar: `aporte_total_pp`) |
| Avance planeado | Σ peso × fracción que el calendario dice que ya debería estar hecha a la fecha de corte: `clip((corte − inicio_plan) / (fin_plan − inicio_plan), 0, 1)` |
| Índice de cumplimiento | avance real / avance planeado (como el SPI del valor ganado): 1 va al día, menos de 1 va atrasado |

## 2. Las tres clases de fecha

| Fecha | Qué es |
|---|---|
| **Planeada** (`fecha_inicio_plan`, `fecha_fin_plan`) | La línea base. En paquetes y proyectos: el inicio de la primera actividad y el fin de la última. |
| **Real** (`fecha_inicio_real`, `fecha_fin_real`) | Solo existe si la actividad ya empezó o terminó. |
| **Proyectada** (`fecha_inicio_proyectada`, `fecha_fin_proyectada`) | La real si ya ocurrió; si falta, un pronóstico al **ritmo real del paquete** (días de calendario por unidad de avance, acotado entre 0,9 y 1,35 veces lo planeado). |

`atraso_proyectado_dias` = fin proyectado − fin planeado. En un paquete se compara con su **holgura**: lo que pasa de ella
(`atraso_sobre_holgura_dias`) es lo que ya empuja el fin del proyecto. El proyecto termina cuando termina su último paquete
(`paquete_que_define_el_fin`) y `paquetes_sobre_su_holgura` cuenta los que ya la pasaron.

Los **meses que faltan** de un paquete (el horizonte T del modelo de riesgo de ejecución) salen ahora de su fecha de fin proyectada
menos la fecha de corte, no de un número sorteado.

## 3. Cómo se generan los datos sintéticos

- Cada proyecto termina entre 0,40 y 0,62 veces la duración de su paquete más corto, contada desde el día de la corrida: el paquete
  más corto lleva entre 40 y 60 % hecho.
- Cada paquete termina `holgura_dias` antes que su proyecto (los de **ruta crítica, el mismo día**): holgura y fechas cuentan la misma historia.
  La duración sale hacia atrás desde su fin.
- Las actividades son 8 plantillas (ingeniería, gestión social, licencias, compras, obra civil, montaje, pruebas, cierre) con un peso
  base; compras, montaje y pruebas siempre están, las demás se sortean hasta tener 5 a 7. Los pesos se normalizan a 1.
- El avance real va un poco por detrás del planeado (lo normal en obra) y se reparte en orden: las primeras actividades completadas, una
  en curso y las demás por iniciar.
- Generador propio (semilla + 13) para lo nuevo, y la misma secuencia (semilla + 7) para duración, holgura, costo de parada y
  presupuesto, de modo que esas cifras no cambian.
- **Las fechas se cuentan desde el día en que se genera el dato** (`fecha_corte`): el mismo código con la misma semilla produce
  las mismas cifras relativas, no las mismas fechas de calendario.

## 4. Sucio a propósito, limpio en Plata

El export llega como uno real: estados escritos de varias formas (`Completada`, ` EN_CURSO `, `Por Iniciar`), ~6 % de avances en
porcentaje (0 a 100) y ~3 % de filas repetidas. `plata.sinteticos` (`limpiar_actividades`, `limpiar_cronograma`):

1. Quita repetidas por `id_actividad` y las que apuntan a un paquete inexistente.
2. Convierte fechas y **invierte** las que quedaron con el fin antes del inicio.
3. Pasa a fracción lo que viene en porcentaje (lo que pasa de 1 se divide por 100).
4. **Deriva el estado del avance** (0 por iniciar, 1 completada) en vez de confiar en el texto.
5. Renormaliza los pesos de cada paquete a 1 y calcula `peso_en_proyecto`.
6. En el cronograma de paquetes, **manda la suma de las actividades**: avance, fechas, duración y meses restantes se calculan de ellas
   (se reporta cuántas fechas declaradas no coincidían). La holgura sigue siendo la declarada, salvo que un paquete de ruta crítica
   no puede tener holgura.

El reporte `reporte_calidad_bronce_a_plata.csv` cuenta cada corrección (`actividades_*`, `cronograma_*`).

## 5. Capas y archivos

| Capa | Archivo | Qué trae |
|---|---|---|
| Bronce | `actividades_cronograma.csv` | Export sucio: una fila por actividad |
| Bronce | `cronograma_paquetes.csv` | Fechas planeadas, holgura, costo de parada y presupuesto por paquete |
| Bronce | `proyectos.geojson` | Ahora con `fecha_inicio_plan` y `fecha_fin_plan` |
| Plata | `actividades.parquet`, `cronograma.parquet` | Limpios y con los pesos y el roll-up calculados |
| Oro | `cronograma_actividades.csv` | Por actividad: pesos, aporte al proyecto, fechas, atraso, si queda por ejecutar |
| Oro | `cronograma_paquetes.csv` | Por paquete: avance real y planeado, índice, fechas, atraso vs holgura, actividad en curso y siguiente |
| Oro | `cronograma_proyectos.csv` | Por proyecto: lo mismo, más el paquete que define el fin |

Paso del pipeline: `oro.cronograma` (lee Plata). Se exporta al GeoPackage como `cronograma_paquetes` (con geometría) y las tablas
`cronograma_proyectos` y `cronograma_actividades`. API: `GET /api/cronograma`. Vista: tarjeta *Cronograma y avance* en **Ejecución**.

## 6. Riesgos y actividades

Cada riesgo del registro apunta a **la actividad de su paquete a la que pega** (`id_actividad`). Con eso el registro y el
cronograma se cruzan: cada actividad sabe cuántas amenazas abiertas tiene (y cuántas de RAM alta o muy alta) y cuántos
riesgos ya se materializaron en ella, y el modelo de riesgo de ejecución usa **lo que le falta a esa actividad** como
horizonte de cada amenaza.

**En el dato sintético** (`bronce/riesgo_actividad_sintetico.py`) primero se decide la actividad y después el texto:
- un riesgo latente pega en algo que falta por hacer (una actividad en curso o por iniciar), con más probabilidad cuanto más
  trabajo le falta; uno próximo a materializarse, en algo que se ejecuta o arranca en los próximos 45 días; uno materializado,
  en algo que ya se ejecutó o se está ejecutando, con más probabilidad cuanto más tiempo se ejecutó en los últimos seis meses;
- pesan más las actividades que su categoría puede afectar: cada plantilla de texto dice qué actividades nombra
  (`textos_sinteticos.ACTIVIDADES_DE`) y el texto se elige entre las que hablan de esa actividad. En ~6 % de los riesgos no
  hay una actividad posible de las que nombra su texto (por ejemplo, un riesgo de obra civil cuando la obra civil ya
  terminó): queda el texto y la actividad no coincide.
- **Las fechas salen de la actividad** (ver la sección 7).
- El Excel trae la columna `actividad_afectada` como la escribe cada quien: el código (~55 %), el nombre o la disciplina con
  otra ortografía (~25 %), vacía (~12 %), el código de otra actividad de otro paquete (~4 %) o, en lo abierto, el de una
  actividad que ya terminó (~4 %). La clave sintética guarda la verdadera (`actividad_real`).

**En Plata** (`modelo/actividad_riesgo.py`):

| Lo que trae el registro | Qué se hace | `actividad_origen` |
|---|---|---|
| Código de una actividad del mismo paquete | Se usa | registro |
| Nombre o disciplina, con cualquier ortografía | Se reconoce | nombre |
| Vacío o irreconocible | Se infiere | inferida |
| Código de otro paquete, o una actividad que no cuadra con el momento del riesgo (abierto en una actividad terminada, materializado en una que no había empezado) | Se infiere otra y se marca `revisar_actividad` | corregida |

La inferencia solo mira actividades posibles para el momento del riesgo (lo que falta, si sigue abierto; lo que ya había
empezado, si se materializó) y entre ellas elige la que más palabras de la descripción y la causa apuntan a su disciplina,
con un empujón por la categoría del riesgo y otro por estar en ejecución. Las palabras son reglas escritas a mano. Acierto
contra la clave: **81 %** si se infiriera para todos los riesgos y **77 %** en los que hubo que inferir o corregir; el
resto se puede revisar en la ficha de cada riesgo (Explorar → Riesgos).

**En Oro:** `cronograma_actividades.csv` suma `riesgos`, `amenazas_abiertas`, `amenazas_altas` y `riesgos_materializados`
por actividad; el registro (`riesgos.geojson`) lleva `id_actividad`, `actividad`, `actividad_origen` y `revisar_actividad`.

## 7. Fechas de los riesgos

Las tres fechas de un riesgo (identificación, materialización y acción de tratamiento) cuentan una sola historia con su
estado, su nivel RAM y su actividad (`bronce/fechas_riesgo_sintetico.py`):

| Estado | Identificación | Materialización | Acción |
|---|---|---|---|
| Materializado | 3 a 60 días antes de materializarse | Mientras se ejecutaba su actividad, de preferencia en los últimos seis meses; nunca después del corte | 1 a 20 días después de materializarse (la respuesta) |
| Latente o próximo | En los últimos seis meses (no antes de que arrancara su paquete, menos un mes de planeación) | — | Plazo según el nivel RAM residual: VH 5–15 días, H 10–30, M 20–60, L 45–90, N 60–120 (la mitad si está próximo). Si ya pasó, se reprogramó o quedó **vencida** (25 % de las latentes, 45 % de las próximas) |

Resultado: una acción abierta de nivel VH vence, en la mediana, en 4 días; una de nivel N, en 48. Cerca del 40 % de las de
nivel H o VH están vencidas: es lo que la regla de escalamiento por acciones vencidas debe detectar.

**Sucias a propósito, revisadas en Plata** (`modelo/fechas_riesgo.py`): ~6 % de las fechas llegan escritas día/mes/año (se
leen igual); en los materializados, algunas fechas cruzadas (la materialización antes que la identificación: se
intercambian), un año de más (materialización en el futuro: se le quita un año si así cuadra; si no, queda sin fecha) o sin
fecha de materialización. Todo lo corregido o imposible queda con `revisar_fechas` y su explicación en `problema_fechas`.
La auditoría comprueba que ningún riesgo se materialice después del corte ni antes de identificarse, que ningún abierto
tenga fecha de materialización y que cada materializado haya ocurrido mientras se ejecutaba su actividad.

## 8. Auditoría

`conciliacion_cronograma` (en `src/auditoria.py`) comprueba: actividades de Bronce − repetidas − sin paquete = Plata = Oro; pesos que suman 1
por paquete y por proyecto; avances entre 0 y 1; estado coherente con el avance; fechas en orden (plan y proyectado); lo pendiente se
proyecta desde la fecha de corte; el avance de cada paquete y de cada proyecto es la suma de peso × avance; y un paquete de ruta crítica
termina el mismo día que su proyecto.

`conciliacion_riesgo_actividad` comprueba que todo riesgo tenga una actividad de su mismo paquete, que ningún riesgo abierto
apunte a una actividad terminada, que todo materializado apunte a una que ya había empezado ese día, que los riesgos y las
amenazas abiertas contados por actividad sean los del registro y que el horizonte de una amenaza no pase lo que le falta a su
paquete.

## 9. Limitaciones y siguientes pasos

- **Sin red de precedencias.** Las actividades de un paquete van en secuencia y los paquetes son independientes entre sí; un
  paquete atrasa al proyecto solo si pasa su holgura. Una red (CPM) con predecesores resolvería la ruta crítica desde las fechas.
- **La ruta crítica y la holgura se declaran**, no se derivan de las fechas (sí se verifica que sean coherentes entre sí).
- **El pronóstico es lineal**: extrapola el ritmo actual del paquete; no hay curva S ni reprogramación.
- **El peso del paquete en el proyecto es su presupuesto**, un supuesto común; podría ser horas-hombre o valor ganado.
- **El modelo de riesgo de ejecución** usa lo que le falta a la actividad de cada riesgo como horizonte, pero aún no suma el
  atraso proyectado determinista al atraso que simula por riesgos: son dos fuentes distintas de atraso que conviene integrar.
- **Un riesgo pega en una sola actividad.** Un bloqueo de la vía puede parar varias a la vez; el registro real podría traer
  varias, con un peso para cada una.
- **Las fechas se cuentan desde el día de la corrida.** Regenerar en otro día mueve todo el calendario (y qué acciones
  están vencidas); un corte fijo daría resultados repetibles.
- **Los plazos de la acción por nivel RAM son un supuesto del dato sintético**, no una regla del instructivo de Ecopetrol.
