from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import unicodedata
import os

app = Flask(__name__)
CORS(app)

COLOR_OPERATIVO = 'style="color:#80BFFF"'
COLOR_INSTRUCCION = 'style="color:#40BFFF"'

INSTRUCCIONES_VALIDAS = {
    "CEOD", "CFAC", "CIAC", "CIAE", "CIAM", "CIBC", "CIBI", "CICO", "CICU", "CIET", "CIEX",
    "CIGR", "CILA", "CIMC", "CIMG", "CIMM", "CIOE", "CIOF", "CIOR", "CIOS", "CIPC", "CIPT",
    "CREC", "CUAV"
}


def normalizar_texto(texto: str) -> str:
    #Pasa el texto a minúsculas y le quita acentos para comparar más fácil.
    if not texto:
        return ""
    texto = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def inferir_tipo_por_titulo(titulo: str):

#    Usa el día de la semana en el título para decidir el tipo:
#    - martes, viernes, sábado -> Operativo
#    - lunes, miércoles, jueves -> Instruccion
#    Si no encuentra nada, devuelve None.

    t = normalizar_texto(titulo)

    # Operativos: martes, viernes, sábado
    if any(dia in t for dia in ("martes", "viernes", "sabado")):
        return "Operativo"

    # Instrucciones: lunes, miércoles, jueves
    if any(dia in t for dia in ("lunes", "miercoles", "jueves")):
        return "Instruccion"

    return None


def extraer_lineas_orbat(cuerpo_html: str):
    #Extrae líneas completas que contienen colores de ORBAT (Operativo o Instrucción).

    html = re.sub(r'<br\s*/?>', '[[BR]]', cuerpo_html, flags=re.IGNORECASE)
    raw_lines = html.split('[[BR]]')

    orbat = []
    tipo = None

    for raw in raw_lines:
        # Detecta si la línea contiene alguno de los dos colores
        if COLOR_OPERATIVO in raw:
            tipo = "Operativo"
        elif COLOR_INSTRUCCION in raw:
            tipo = "Instruccion"
        else:
            continue

        # Limpieza visual
        limpio = BeautifulSoup(raw, "html.parser").get_text().strip()
        limpio = re.sub(r'^[/>\s]+|[/>\s]+$', '', limpio)

        if limpio:
            orbat.append(limpio)

    return "\n".join(orbat).strip(), tipo


def extraer_instruccion_desde_pasador(cuerpo_html: str):
    #Extrae el código de instrucción a partir de la imagen del pasador en el HTML.
    soup = BeautifulSoup(cuerpo_html, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "/pasadores/" in src and "_pasador" in src:
            try:
                fragmento = src.split("/pasadores/")[1]
                nombre_raw = fragmento.split("_pasador")[0]
            except (IndexError, ValueError):
                continue

            base = nombre_raw.split("_")[0]
            codigo = base.strip().upper()

            if codigo in INSTRUCCIONES_VALIDAS:
                return codigo

    return None



@app.route("/api/misiones")
@app.route("/api/misiones/<int:paginas>")
def obtener_misiones(paginas=1):
    try:
        if paginas is None or paginas < 1:
            paginas = 1

        base_url = "https://foro.squadalpha.es/"
        misiones = []

        # Recorrer desde página 1 hasta <paginas>
        for pagina in range(1, paginas + 1):
            start = (pagina - 1) * 25
            if pagina > 1:
                foro_url = f"{base_url}viewforum.php?f=18&start={start}"
            else:
                foro_url = f"{base_url}viewforum.php?f=18"

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
                orbat, tipo = extraer_lineas_orbat(cuerpo_html)

                # Ajustar tipo según día de la semana
                tipo_titulo = inferir_tipo_por_titulo(titulo)
                if tipo_titulo:
                    tipo = tipo_titulo

                # Extraer instrucción si es de tipo Instruccion
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

        return jsonify(misiones)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "mensaje": "Backend Squad Alpha activo con extracción de ORBAT",
        "uso": "/api/misiones o /api/misiones/n donde n es el número de paginas en OSCAR - Operation Center"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)