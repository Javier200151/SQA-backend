from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde tu frontend (GitHub Pages)

@app.route("/api/misiones")
def obtener_misiones():
    base_url = "https://foro.squadalpha.es/"
    foro_url = base_url + "viewforum.php?f=18"

    try:
        res = requests.get(foro_url, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"No se pudo acceder al foro: {e}"}), 500

    soup = BeautifulSoup(res.text, "html.parser")
    misiones = []

    # Cada tema del foro está en un enlace con clase 'topictitle'
    for tema in soup.select("a.topictitle"):
        titulo = tema.text.strip()
        href = tema.get("href")

        if not href:
            continue

        enlace = base_url + href.lstrip("./")

        # Obtener el contenido del primer mensaje de cada publicación
        try:
            post_res = requests.get(enlace, headers={"User-Agent": "Mozilla/5.0"})
            post_res.raise_for_status()
            post_soup = BeautifulSoup(post_res.text, "html.parser")
            cuerpo = post_soup.select_one(".postbody")
            contenido = cuerpo.get_text("\n", strip=True) if cuerpo else ""
        except Exception:
            contenido = ""

        misiones.append({
            "titulo": titulo,
            "url": enlace,
            "contenido": contenido
        })

    return jsonify(misiones)


@app.route("/")
def home():
    return jsonify({"status": "OK", "mensaje": "Backend Squad Alpha activo"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
