# Modelo de riesgo de ejecución

**Pregunta que responde:** ¿cuántos días de atraso y cuántos dólares de sobrecosto puede tener cada paquete de trabajo y cada
proyecto, con qué probabilidad y por qué?

El ICT dice **dónde mirar primero** (un ranking territorial relativo). Este modelo dice **cuánto podría costar no hacerlo**, en
unidades del negocio: días, USD y probabilidad.

**Datos de entrada:**
- **Registro de riesgos:** calificado con la matriz RAM de Ecopetrol.
- **Territorio real:** IDEAM y CHIRPS (clima); UNGRD (emergencias); Ministerio de Defensa (delitos); DANE (censo); ANT (resguardos); RUNAP (áreas protegidas); INVIAS e IGAC (vías).
- **Cronograma de los paquetes:** hoy es sintético.

| | |
|---|---|
| Motor | `src/modelo/ejecucion.py` (funciones puras, sin lectura de archivos) |
| Paso del pipeline | `oro.ejecucion` (`src/oro/ejecucion.py`) |
| Supuestos | `parametros.yaml` → `ejecucion`; los editados desde la aplicación, en `ejecucion_personalizada.yaml` |
| Salidas | `data/gold/ejecucion_paquetes.csv`, `ejecucion_proyectos.csv`, `ejecucion_riesgos.csv`, `ejecucion_resumen.json` |
| Vista | *Riesgo de ejecución* (`app/static/ejecucion.html`; API `/api/ejecucion`) |
| Pruebas | `tests/test_ejecucion.py`; la auditoría comprueba que la simulación reproduce el valor esperado analítico |

## 1. Formulación

### 1.1 Frecuencia de cada amenaza abierta

Para la amenaza *i* del paquete *p* (latente o próxima a materializarse):

```
λᵢ = λ₀(Lᵢ) · exp( γ · Σₖ βₖ,c(i) · zₖ,p ) · f(estadoᵢ)        [eventos por año]
```

- **Lᵢ:** letra RAM de probabilidad **residual** (con controles). La inherente se usa para valorar los controles y en el escenario "sin controles".
- **λ₀(L):** frecuencia por paquete de cada letra. Las letras de la RAM hablan del historial de la industria, la empresa o la unidad, no de un paquete; por eso se reparten entre las "unidades de exposición" comparables de cada nivel:

| Letra | Definición RAM | Lectura por paquete | λ₀ (por año) |
|---|---|---|---|
| E | Varias veces al año en la unidad | ~3 eventos/año entre ~6 paquetes de una unidad | 0,5 |
| D | Varias veces al año en la empresa | ~3 eventos/año entre ~60 paquetes | 0,05 |
| C | Ha ocurrido en la empresa | ~1 evento en ~15 años entre ~60 paquetes | 0,001 |
| B | Ha ocurrido en la industria | ~5 veces menos que C | 0,0002 |
| A | No ha ocurrido en la industria | teórico | 0,00002 |

- **z₍ₖ,ₚ₎:** covariables del territorio del paquete. Valen 0 en el promedio de La Guajira, así que el modelo solo corrige la diferencia frente a lo que el evaluador ya sabe:

| Covariable | Definición | Fuente |
|---|---|---|
| `tasa_delitos_rel` | ln((tasa del municipio + 1) / (tasa del departamento + 1)); extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre y ataques a la fuerza pública en 12 meses por 100.000 hab. El homicidio no entra: en su mayoría es violencia interpersonal | Ministerio de Defensa, DANE |
| `emergencias_rel` | ln((emergencias por año del municipio + 0,5) / (promedio por municipio + 0,5)) | UNGRD |
| `anomalia_lluvia` | Desviación media de la lluvia de los últimos 3 meses frente a su normal 1991-2020, menos la del departamento | CHIRPS |
| `en_resguardo` | Fracción del paquete dentro de resguardos, menos la del departamento (63 %) | ANT |
| `ipm_rel` | (IPM del municipio − IPM del departamento) / IPM del departamento | DANE, censo 2018 |
| `pdet` | 1 si el municipio es PDET, menos la fracción de municipios PDET | ART |
| `vias_tiempo_seco` | Fracción de km de vías a menos de 10 km que solo se transitan en tiempo seco, menos la del departamento | INVIAS + IGAC |

- **β₍ₖ,c₎:** cuánto pesa cada covariable en cada categoría de riesgo:

| Categoría | Covariables (β) |
|---|---|
| Seguridad física | delitos 0,6 |
| Climático | emergencias 0,4 · anomalía de lluvia 1,0 |
| Social / comunidad | resguardo 0,8 · IPM 0,8 · PDET 0,3 |
| Logístico / acceso | vías solo tiempo seco 1,5 · anomalía de lluvia 0,5 |
| Ambiental | ninguna sobre la frecuencia; el área protegida cercana sube la consecuencia (1.3) |
| Contractual | ninguna |

- **γ = 0,5:** reparte el peso entre la letra del evaluador y el territorio. Con γ = 0 solo cuenta la letra; con γ = 1, el territorio con todo su peso. Evita contar dos veces el historial que el evaluador ya puso en la letra.
- **Límite del multiplicador:** el territorio multiplica la frecuencia entre 1/3 y 3.
- **f(estado):** 1 si el riesgo está latente; 2 si está próximo a materializarse.

### 1.2 Probabilidad en lo que falta

```
Pᵢ = 1 − exp(−λᵢ · Tᵢ)
```

Tᵢ es el tiempo durante el que la amenaza puede pegarle a **la actividad del cronograma a la que apunta** (ver
[CRONOGRAMA.md](CRONOGRAMA.md#6-riesgos-y-actividades)): de la fecha de corte (o de su inicio proyectado, si la actividad
aún no empieza) a su **fin proyectado**; 0 si la actividad ya terminó. Un riesgo de las pruebas solo puede ocurrir mientras
duren las pruebas, no durante todo lo que le falta al paquete. Si no se sabe la actividad, Tᵢ es lo que le falta al paquete.
Como las actividades de un paquete van en secuencia, un evento en cualquiera de ellas corre el fin del paquete.

`ejecucion_riesgos.csv` dice de dónde salió cada horizonte (`horizonte_origen`: actividad o paquete) y la actividad.

### 1.3 Impacto por evento: de la RAM a días y dólares

- **Días.** Cada nivel de consecuencia RAM (0-5) de cada dimensión se traduce a días de atraso del paquete (valor más probable *D*). **Manda la peor dimensión**, como en la RAM. Cada evento dura `Triangular(½·D, D, 2·D)`, con media 7/6·D:

| Nivel | Personas | Económica | Ambiental | Clientes | Imagen / social |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 0 | 0 |
| 2 | 0,5 | 1 | 1 | 1 | 2 |
| 3 | 2 | 5 | 5 | 5 | 7 |
| 4 | 10 | 20 | 20 | 15 | 30 |
| 5 | 30 | 60 | 60 | 30 | 60 |

- **Costo:**

```
costoᵢ = LogUniforme(banda USD de la consecuencia económica) + costo diario de parada_p · díasᵢ
```

  - Las bandas son las del instructivo: 1, menos de USD 10 mil; 2, de 10 mil a 100 mil; 3, de 100 mil a 1 M; 4, de 1 M a 10 M; 5, más de 10 M (se toma hasta 30 M).
- **Ya materializado.** Una amenaza materializada no tiene probabilidad. Su atraso y su costo cuentan como **ya consumidos**, con una fracción (35 %) de los de la consecuencia potencial, porque la RAM registra la peor consecuencia creíble.

### 1.4 Simulación y dependencia

En cada uno de *S* escenarios (10.000):

```
Nᵢˢ   ~ Poisson( λᵢ · T_p · W_g(i)ˢ )                número de eventos
díasᵢˢ = suma de Nᵢˢ eventos Triangular             (se aproxima con una normal de media y varianza exactas, cortada en 0)
W_gˢ  ~ Gamma(k = 1/σ², θ = σ²)                     choque común: media 1, desviación σ
```

**Grupos del choque común:**
- **Clima (σ = 0,5):** los riesgos climáticos y logísticos de un mismo municipio. Captura una temporada de lluvias o una sequía.
- **Social (σ = 0,6):** los riesgos sociales de un mismo proyecto. Captura un paro, un bloqueo o una consulta.

El choque no cambia el valor esperado; ensancha la cola: hay años en que todo falla junto, y eso es lo que mueve el P90.

### 1.5 Paquete y proyecto

```
D_p = máxⱼ dⱼ + α · (Σⱼ dⱼ − máxⱼ dⱼ)        j = todos los eventos del paquete: los ya ocurridos (consumido) y los simulados
D_proyecto = Σ_p máx(0, D_p − holgura_p)
C_p = Σᵢ costo directoᵢ + costo diario de parada_p · (días de parada de los eventos simulados, con el mismo solapamiento) + costo consumido_p
C_proyecto = Σ_p C_p
```

**Solapamiento (α = 0,5).** En un paquete, los atrasos de varios eventos no siempre van uno detrás de otro: el paquete se
atrasa lo del mayor evento más una fracción α de lo de los demás (α = 1, en fila; α = 0, todos a la vez). El costo de tener
el paquete parado se cobra sobre esos días una sola vez; el costo directo de cada evento sí se suma. α es un supuesto
editable desde la vista; `atraso_sin_solapamiento_media` guarda la suma sin solapar, que es la que la auditoría compara con
el valor esperado analítico.

Los paquetes de **ruta crítica** tienen holgura 0: todo su atraso pasa al proyecto.

### 1.6 Salidas

| Salida | Uso |
|---|---|
| Atraso esperado y P50/P80/P90 (días), por paquete, proyecto y portafolio | Contingencia de cronograma |
| Sobrecosto esperado y P50/P80/P90 (USD) | Reserva de contingencia |
| **IRE** = 100 · P(D > holgura + tolerancia); tolerancia de 15 días por paquete y 30 por proyecto | Índice de riesgo de ejecución (0-100), con los mismos niveles que el ICT |
| Aporte de cada amenaza = λ·T·días medios (y su % del paquete) | Qué atacar primero |
| Valor de los controles = (λ inherente − λ residual)·T·días medios | Si los controles valen lo que cuestan |
| Escenarios: factor por categoría, con o sin controles, otras tolerancias | Preguntas del tipo "¿y si llueve el doble?" |

## 2. Relación con el resto del piloto

- **Matriz RAM:** la RAM da a cada amenaza su letra y sus consecuencias; este modelo las convierte en frecuencias, días y dólares. Si se edita la matriz o se recalcula el registro, el modelo se recalcula después (depende de `plata.sinteticos`).
- **ICT:** no se reemplaza. El ICT prioriza el territorio; el IRE mide la ejecución. Un paquete puede tener ICT alto e IRE bajo (zona difícil, pero con holgura y pocos riesgos frecuentes), y al revés.
- **Escalamiento RAM:** sigue aparte. Una amenaza VH es intolerable aunque su efecto esperado en días sea pequeño.

## 3. Calibración y validación

**Hoy, sin historial:**
- **Origen de los supuestos:** λ₀, la tabla de días, γ y los β son supuestos de trabajo, editables desde la aplicación. Deben fijarse en un taller de expertos; la derivación de pesos por AHP ya está en `src/modelo/ahp.py`.
- **Comprobación de la simulación:** la auditoría verifica que la simulación reproduce el valor esperado analítico (±5 %). Las pruebas verifican cada pieza: la holgura, la tolerancia, el choque común y el escenario sin controles.

**Con el historial de Ecopetrol:**

1. **Frecuencias.** Se actualiza cada categoría con Bayes conjugado Poisson-Gamma: la letra RAM es la creencia inicial (Gamma con media λ₀ y forma *k*) y los eventos reales la corrigen.

   ```
   λ_posterior = (k + n) / (k/λ₀ + t)
   ```

   Aquí *n* son los eventos observados y *t* los años-paquete de exposición.
2. **Pesos del territorio.** Los β se estiman con una regresión de Poisson de los incidentes reales contra las covariables del territorio (con γ = 1 una vez estimados).
3. **Días por evento.** La tabla se calibra con los atrasos reales de los incidentes registrados.
4. **Validación fuera de muestra.** Con proyectos ya terminados se calculan el *Brier score* de P(atraso > tolerancia), la curva de calibración y la cobertura del P90 (que el atraso real no pase el P90 más del 10 % de las veces).

## 4. Limitaciones

- **Datos sintéticos.** El cronograma, el costo de parada y el registro de riesgos son sintéticos: las cifras demuestran el mecanismo, no el riesgo real de ningún proyecto.
- **Solapamiento uniforme.** Un solo α para todo par de eventos: en la realidad depende de si atacan la misma actividad del cronograma (lo resolvería una red de precedencias, que el piloto no tiene).
- **Controles.** Solo bajan la probabilidad; no reducen la consecuencia.
- **Oportunidades.** No restan atraso.
- **Cronograma simplificado.** El proyecto se modela como la suma de lo que cada paquete no absorbe con su holgura, no como una red de precedencias (no hay CPM).
- **Datos del territorio.** Usan la población del censo 2018 y el último año disponible de cada fuente.
