from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

COLOR_AZUL = 'style="color:#80BFFF"'


def extraer_lineas_orbat(cuerpo_html: str):
    """Extrae líneas completas que contienen color azul (#80BFFF) sin modificar su contenido."""

    # Normalizar <br> como separador de línea
    html = re.sub(r'<br\s*/?>', '[[BR]]', cuerpo_html, flags=re.IGNORECASE)

    # Separar por saltos de línea reales
    raw_lines = html.split('[[BR]]')

    orbat = []

    for raw in raw_lines:
        # Mantener solo líneas con el color azul
        if COLOR_AZUL not in raw:
            continue

        # Limpiar HTML de esa línea sin alterar el contenido visual
        limpio = BeautifulSoup(raw, "html.parser").get_text().strip()

        # Quitar posibles restos como "/>" o ">" al inicio/fin
        limpio = re.sub(r'^[/>\s]+|[/>\s]+$', '', limpio)

        if limpio:
            orbat.append(limpio)

    return "\n".join(orbat).strip()


@app.route("/api/misiones")
@app.route("/api/misiones/<int:paginas>")
def obtener_misiones(paginas=1):
    try:
        # Si no viene número, actuar como página 1
        if paginas is None or paginas < 1:
            paginas = 1

        base_url = "https://foro.squadalpha.es/"
        misiones = []

        # Recorrer desde página 1 hasta <paginas>
        for pagina in range(1, paginas + 1):
            start = (pagina - 1) * 25
            foro_url = f"{base_url}viewforum.php?f=18&start={start}" if pagina > 1 else f"{base_url}viewforum.php?f=18"

            res = requests.get(foro_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")

            for tema in soup.select("a.topictitle"):
                titulo = tema.text.strip()
                href = tema.get("href")
                if not href:
                    continue

                enlace = base_url + href.lstrip("./")

                post_res = requests.get(enlace, headers={"User-Agent": "Mozilla/5.0"})
                post_soup = BeautifulSoup(post_res.text, "html.parser")

                cuerpo = post_soup.select_one(".postbody")
                if not cuerpo:
                    continue

                cuerpo_html = str(cuerpo)

                # Contenido completo plano
                contenido_completo = cuerpo.get_text("\n").strip()

                # Extraer ORBAT por color
                orbat = extraer_lineas_orbat(cuerpo_html)

                misiones.append({
                    "titulo": titulo,
                    "url": enlace,
                    "contenido_completo": contenido_completo,
                    "orbat": orbat
                })

        return jsonify(misiones)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "mensaje": "Backend Squad Alpha activo con extracción de ORBAT por color",
        "uso": "/api/misiones o /api/misiones/<n>"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
