from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/api/misiones")
def obtener_misiones():
    base_url = "https://foro.squadalpha.es/"
    foro_url = base_url + "viewforum.php?f=18"

    # Obtener la lista de temas
    res = requests.get(foro_url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    misiones = []

    # Cada publicación tiene el enlace con clase 'topictitle'
    for tema in soup.select("a.topictitle"):
        titulo = tema.text.strip()
        enlace_relativo = tema.get("href")
        if not enlace_relativo:
            continue

        enlace_completo = base_url + enlace_relativo.lstrip("./")

        # Obtener contenido de la primera publicación
        res_post = requests.get(enlace_completo, headers={"User-Agent": "Mozilla/5.0"})
        post_soup = BeautifulSoup(res_post.text, "html.parser")
        cuerpo = post_soup.select_one(".postbody")

        # Extraer texto limpio o dejar vacío si no existe
        contenido = cuerpo.get_text("\n", strip=True) if cuerpo else ""

        misiones.append({
            "titulo": titulo,
            "url": enlace_completo,
            "contenido": contenido
        })

    return jsonify(misiones)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
