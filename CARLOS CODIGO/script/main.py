### Punto de entrada de la Ficha Presidencial
### Uso:
###   python main.py            genera las 32 fichas
###   python main.py 15         genera solo la ficha de la clave indicada
###   python main.py 15 09 30   genera las fichas de varias claves

import sys

from engine import GeneradorFichas


def main():
    """Lee las claves de entidad de la linea de comandos y genera las fichas."""
    claves = sys.argv[1:]

    generador = GeneradorFichas()

    if not claves:
        rutas = generador.generar_lote()
        print(f"\nFichas generadas: {len(rutas)}")
        return

    for clave in claves:
        ruta = generador.generar(clave)
        print(f"Generada: {ruta}")


if __name__ == "__main__":
    main()