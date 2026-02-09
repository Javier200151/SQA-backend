from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import unicodedata
import os
import csv
import io

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTuQORinglzn8kO3ywB2K6YYDZJCgaEWwBUlhNhBbg7uEyyku8tC7sCN1Um1BgFyT_oqqvqL-4IKROB/pub?gid=259895026&single=true&output=csv"

app = Flask(__name__)
CORS(app)

COLOR_OPERATIVO = 'style="color:#80BFFF"'
COLOR_INSTRUCCION = 'style="color:#40BFFF"'

INSTRUCCIONES_VALIDAS = {
    "CEOD", "CFAC", "CIAC", "CIAE", "CIAM", "CIBC", "CIBI", "CICO", "CICU", "CIET", "CIEX",
    "CIGR", "CILA", "CIMC", "CIMG", "CIMM", "CIOE", "CIOF", "CIOR", "CIOS", "CIPC", "CIPT",
    "CREC", "CUAV"
}


# ===================== UTILIDADES =====================

def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def inferir_tipo_por_titulo(titulo: str):
    t = normalizar_texto(titulo)

    if any(dia in t for dia in ("martes", "viernes", "sabado")):
        return "Operativo"
    if any(dia in t for dia in ("lunes", "miercoles", "jueves")):
        return "Instruccion"
    return None


def extraer_lineas_orbat(cuerpo_html: str):
    html = re.sub(r'<br\s*/?>', '[[BR]]', cuerpo_html, flags=re.IGNORECASE)
    raw_lines = html.split('[[BR]]')

    orbat = []
    tipo = None

    for raw in raw_lines:
        if COLOR_OPERATIVO in raw:
            tipo = "Operativo"
        elif COLOR_INSTRUCCION in raw:
            tipo = "Instruccion"
        else:
            continue

        limpio = BeautifulSoup(raw, "html.parser").get_text().strip()
        limpio = re.sub(r'^[/>\s]+|[/>\s]+$', '', limpio)

        if limpio:
            orbat.append(limpio)

    return "\n".join(orbat).strip(), tipo


def extraer_instruccion_desde_pasador(cuerpo_html: str):
    soup = BeautifulSoup(cuerpo_html, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/pasadores/" in src and "_pasador" in src:
            try:
                fragmento = src.split("/pasadores/")[1]
                nombre_raw = fragmento.split("_pasador")[0]
                codigo = nombre_raw.split("_")[0].upper()
                if codigo in INSTRUCCIONES_VALIDAS:
                    return codigo
            except Exception:
                continue
    return None


# ===================== CORE =====================

def extraer_misiones_de_una_pagina(pagina: int):
    if pagina < 1:
        pagina = 1

    base_url = "https://foro.squadalpha.es/"
    start = (pagina - 1) * 25

    foro_url = (
        f"{base_url}viewforum.php?f=18&start={start}"
        if pagina > 1
        else f"{base_url}viewforum.php?f=18"
    )

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
        contenido_completo = cuerpo.get_text("\n").strip()

        orbat, tipo = extraer_lineas_orbat(cuerpo_html)

        tipo_titulo = inferir_tipo_por_titulo(titulo)
        if tipo_titulo:
            tipo = tipo_titulo

        instruccion = None
        if tipo == "Instruccion":
            instruccion = extraer_instruccion_desde_pasador(cuerpo_html)

        misiones.append({
            "titulo": titulo,
            "url": enlace,
            "contenido_completo": contenido_completo,
            "orbat": orbat,
            "tipo": tipo,
            "instruccion": instruccion
        })

    return misiones


# ===================== ENDPOINTS =====================

@app.route("/api/misiones")
@app.route("/api/misiones/<int:paginas>")
def obtener_misiones(paginas=1):
    try:
        if paginas < 1:
            paginas = 1

        todas = []
        for p in range(1, paginas + 1):
            todas.extend(extraer_misiones_de_una_pagina(p))

        return jsonify(todas)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mision/<int:pagina>")
def obtener_mision(pagina):
    try:
        return jsonify(extraer_misiones_de_una_pagina(pagina))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route("/api/miembros")
def api_miembros():
    try:
        r = requests.get(SHEET_CSV_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()

        # Parse CSV -> dict {nombre_normalizado: fecha_string}
        text = r.text
        f = io.StringIO(text)
        reader = csv.reader(f)

        rows = list(reader)
        if not rows:
            return jsonify({"error": "CSV vacío"}), 500

        miembros = {}
        # Saltamos cabecera (fila 0)
        for row in rows[1:]:
            if len(row) < 2:
                continue
            nombre = (row[0] or "").strip()
            fecha = (row[1] or "").strip()
            if nombre and fecha:
                miembros[normalizar_texto(nombre)] = fecha

        return jsonify(miembros)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "uso": {
            "/api/misiones": "Primera página",
            "/api/misiones/n": "Páginas acumuladas",
            "/api/mision/n": "Solo la página n"
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
