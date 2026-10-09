"""
Inteligencia artificial sobre el texto del registro de riesgos (procesamiento de lenguaje natural).

Los registros de riesgos llegan de varios Excel y reportes de campo con texto libre: la categoria a veces falta, a veces
no coincide con lo que dice la descripcion, y los lugares se mencionan solo en el texto. Este modulo:

  * ClasificadorTexto: aprende la taxonomia de riesgos (6 categorias) del propio registro (los riesgos que SI traen
    categoria) con un modelo bayesiano ingenuo multinomial sobre palabras y pares de palabras, y la sugiere para los
    que no la traen. Da la probabilidad de cada categoria y las palabras que mas pesaron (explicable).
  * validacion_cruzada: mide el acierto con datos que el modelo no vio (k particiones).
  * lugares_mencionados: encuentra municipios nombrados en el texto (diccionario geografico del DANE).

Sin dependencias fuera de numpy: el modelo es pequeno, rapido y auditable. Con el registro real de Ecopetrol se
reentrena igual; si se quiere un modelo de lenguaje mas grande, se cambia esta clase sin tocar el resto del pipeline.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np

# palabras vacias del espanol que no ayudan a distinguir categorias
VACIAS = set("""
a al ante bajo con contra de del desde durante e el en entre es esta este esto ha hacia hasta la las le lo los mas
muy no o para pero por que se sin sobre su sus tras un una uno unos y ya lo cual como cuando donde otra otro otros
varios varias tiene tienen hay fue son ser sera puede pueden dias dia
""".split())


def normalizar(texto: str) -> str:
    """minusculas, sin tildes ni signos."""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9 ]+", " ", t)


def rasgos(texto: str) -> list[str]:
    """Palabras (sin vacias) y pares de palabras seguidas: 'bloqueo via', 'consulta previa'."""
    palabras = [p for p in normalizar(texto).split() if p not in VACIAS and len(p) > 2 and not p.isdigit()]
    return palabras + [f"{a} {b}" for a, b in zip(palabras, palabras[1:])]


class ClasificadorTexto:
    """Bayesiano ingenuo multinomial con suavizado de Laplace."""

    def __init__(self, alfa: float = 0.5):
        self.alfa = alfa

    def entrenar(self, textos: list[str], etiquetas: list[str]) -> "ClasificadorTexto":
        self.clases = sorted(set(etiquetas))
        conteos = {c: Counter() for c in self.clases}
        for t, c in zip(textos, etiquetas):
            conteos[c].update(rasgos(t))
        self.vocab = sorted({r for cnt in conteos.values() for r in cnt})
        pos = {r: i for i, r in enumerate(self.vocab)}
        m = np.zeros((len(self.clases), len(self.vocab)))
        for k, c in enumerate(self.clases):
            for r, n in conteos[c].items():
                m[k, pos[r]] = n
        self._pos = pos
        n_por_clase = np.array([sum(1 for e in etiquetas if e == c) for c in self.clases], dtype=float)
        self.log_prior = np.log(n_por_clase / n_por_clase.sum())
        suavizado = m + self.alfa
        self.log_verosimilitud = np.log(suavizado / suavizado.sum(axis=1, keepdims=True))
        return self

    def _puntajes(self, texto: str) -> np.ndarray:
        idx = [self._pos[r] for r in rasgos(texto) if r in self._pos]
        return self.log_prior + (self.log_verosimilitud[:, idx].sum(axis=1) if idx else 0.0)

    def probabilidades(self, texto: str) -> dict[str, float]:
        s = self._puntajes(texto)
        p = np.exp(s - s.max())
        p /= p.sum()
        return dict(zip(self.clases, p.round(4)))

    def predecir(self, texto: str) -> tuple[str, float]:
        p = self.probabilidades(texto)
        clase = max(p, key=p.get)
        return clase, float(p[clase])

    def explicar(self, texto: str, clase: str, n: int = 3) -> list[str]:
        """Rasgos del texto que mas empujan hacia `clase` frente al promedio de las otras categorias."""
        k = self.clases.index(clase)
        otras = np.delete(self.log_verosimilitud, k, axis=0).mean(axis=0)
        vistos = {r for r in rasgos(texto) if r in self._pos}
        peso = {r: self.log_verosimilitud[k, self._pos[r]] - otras[self._pos[r]] for r in vistos}
        return [r for r, v in sorted(peso.items(), key=lambda x: -x[1]) if v > 0][:n]


def validacion_cruzada(textos: list[str], etiquetas: list[str], k: int = 5, semilla: int = 42) -> dict:
    """Acierto con datos que el modelo no vio: k particiones; tambien el acierto de cada categoria."""
    n = len(textos)
    orden = np.random.default_rng(semilla).permutation(n)
    aciertos, total = 0, 0
    por_clase: dict[str, list[int]] = {}
    for f in range(k):
        prueba = set(orden[f::k].tolist())
        entrenamiento = [i for i in range(n) if i not in prueba]
        modelo = ClasificadorTexto().entrenar([textos[i] for i in entrenamiento], [etiquetas[i] for i in entrenamiento])
        for i in prueba:
            ok = modelo.predecir(textos[i])[0] == etiquetas[i]
            aciertos += ok
            total += 1
            por_clase.setdefault(etiquetas[i], []).append(int(ok))
    return {"exactitud": round(aciertos / total, 3) if total else None, "evaluados": total,
            "por_categoria": {c: round(float(np.mean(v)), 3) for c, v in sorted(por_clase.items())}}


def lugares_mencionados(texto: str, nombres: dict[str, str]) -> list[str]:
    """Codigos de los lugares (p. ej. municipios) cuyo nombre aparece en el texto. `nombres`: codigo -> nombre."""
    t = f" {normalizar(texto)} "
    return [codigo for codigo, nombre in nombres.items() if f" {normalizar(nombre).strip()} " in t]
