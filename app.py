from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

COLOR_AZUL = "color:#80BFFF"

def extraer_lineas_orbat(cuerpo_html: str):
    """Extrae líneas completas del ORBAT basadas en color azul #80BFFF sin arrastrar restos de etiquetas."""

    html = re.sub(r'<br\s*/?>', '[[BR]]', cuerpo_html, flags=re.IGNORECASE)

    raw_lines = html.split('[[BR]]')

    orbat = []

    for raw in raw_lines:
        # Solo procesar líneas que contienen el color azul
        if COLOR_AZUL not in raw:
            continue

        limpio = BeautifulSoup(raw, "html.parser").get_text().strip()

        limpio = re.sub(r'^[/>\s]+|[/>\s]+$', '', limpio)

        if limpio:
            orbat.append(limpio)

    return "\n".join(orbat).strip()

@app.route("/api/misiones")
def obtener_misiones():
    base_url = "https://foro.squadalpha.es/"
    foro_url = base_url + "viewforum.php?f=18"

    res = requests.get(foro_url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    misiones = []

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

        # Extraer contenido completo del post (solo texto plano)
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


@app.route("/")
def home():
    return jsonify({"status": "OK", "mensaje": "Backend Squad Alpha extractor de ORBAT"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
