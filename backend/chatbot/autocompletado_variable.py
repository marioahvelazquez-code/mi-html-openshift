"""Política del desplegable; no participa en la interpretación conversacional."""
import re


def sugerir_variables(buscador, texto):
    """Busca en el catálogo completo; exactas primero, máximo diez, sin páginas.

    total cuenta la unión sin duplicados antes del límite; total_exactas permite
    distinguir coincidencias estrictas de las sugerencias complementarias.
    """
    q = str(texto or "").strip()
    variables = []
    vistos = set()

    def agregar(variable, mecanismo):
        clave = str(variable["id"])
        if clave not in vistos:
            vistos.add(clave)
            variables.append({
                "id": variable["id"],
                "descripcion": variable.get("descripcion") or variable["desc_original"],
                "mecanismo": mecanismo,
            })

    if re.fullmatch(r"[0-9]+", q):
        for variable in buscador.buscar_por_clave(q):
            agregar(variable, "clave")
        total_exactas = len(variables)
    elif len(q) >= 3:
        for variable in buscador.buscar_por_tokens(q):
            agregar(variable, "tokens")
        total_exactas = len(variables)
        # Misma preparación, canónica y ranking que usaba la vista original.
        canonica = buscador.buscar_variable_canonica(buscador._preparar_texto(q))
        resultado = buscador.buscar(q, aplicar_canonica=False)
        if canonica:
            agregar(canonica, "canonica")
        if resultado["status"] == "ganador_claro":
            agregar(resultado["variable"], "similitud")
        else:
            for candidato in resultado.get("candidatos", []):
                agregar(candidato, "similitud")
    else:
        total_exactas = 0

    return {"items": variables[:10], "total": len(variables), "total_exactas": total_exactas}
