"""
AHP (Analytic Hierarchy Process) para derivar las ponderaciones del ICT.

En el piloto los pesos en parametros.yaml son un supuesto de partida. Este
modulo muestra el mecanismo que se usaria en la Fase 2 con los expertos de
riesgos de Ecopetrol: comparaciones por pares -> pesos + razon de
consistencia (CR). Si CR > 0.10, los juicios son inconsistentes y deben
revisarse antes de usar los pesos resultantes.

Uso:
    python -m modelo.ahp
"""
from __future__ import annotations

import numpy as np

# Indice aleatorio (Saaty) por tamano de matriz (n = 1..10)
RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def calcular_pesos_ahp(matriz: np.ndarray) -> tuple[np.ndarray, float]:
    """Devuelve (pesos, razon_de_consistencia) a partir de una matriz de
    comparacion por pares (n x n, reciproca, diagonal = 1).
    """
    n = matriz.shape[0]
    # Vector propio principal via el metodo de la media geometrica (aproximacion
    # numericamente estable y estandar para matrices pequenas de AHP)
    productos = np.prod(matriz, axis=1)
    pesos_crudos = productos ** (1.0 / n)
    pesos = pesos_crudos / pesos_crudos.sum()

    # lambda_max para el Consistency Index
    vector_ponderado = matriz @ pesos
    lambda_max = np.mean(vector_ponderado / pesos)
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RI.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0
    return pesos, cr


def ejemplo_matriz_criterios() -> tuple[list[str], np.ndarray]:
    """Matriz de ejemplo, calibrada para reproducir aproximadamente los pesos
    por defecto de parametros.yaml. Escala de Saaty 1-9.

    Orden: severidad_riesgo, vulnerabilidad_territorial, amenazas_externas,
           exposicion_proyecto, convergencia
    """
    criterios = [
        "severidad_riesgo", "vulnerabilidad_territorial", "amenazas_externas",
        "exposicion_proyecto", "convergencia",
    ]
    # fila i vs columna j: cuanto mas importante es i que j
    matriz = np.array([
        [1,   1.5, 2,   1.5, 2],
        [2/3, 1,   1.5, 1,   1.5],
        [0.5, 2/3, 1,   0.5, 1],
        [2/3, 1,   2,   1,   1.5],
        [0.5, 2/3, 1,   2/3, 1],
    ])
    return criterios, matriz


def main():
    criterios, matriz = ejemplo_matriz_criterios()
    pesos, cr = calcular_pesos_ahp(matriz)

    print("Pesos derivados por AHP (ejemplo de calibracion):")
    for c, w in zip(criterios, pesos):
        print(f"  {c:28s} {w:.3f}")
    print(f"\nRazon de consistencia (CR): {cr:.3f}", "-> ACEPTABLE (<=0.10)" if cr <= 0.10 else "-> REVISAR JUICIOS (>0.10)")


if __name__ == "__main__":
    main()
