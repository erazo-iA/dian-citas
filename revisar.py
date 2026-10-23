import os, re, urllib.request
from playwright.sync_api import sync_playwright

TOPIC = os.environ["NTFY_TOPIC"]
URL = "https://agendamiento.dian.gov.co/"
PASOS = [r"Agendar cita", r"Persona natural", r"Video\s*Atenci", r"Devoluciones"]

def avisar(msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=msg.encode("utf-8"),
        headers={"Title": "Citas DIAN", "Priority": "high", "Click": URL})
    urllib.request.urlopen(req)

os.makedirs("capturas", exist_ok=True)
llegue, error = "inicio", ""
with sync_playwright() as p:
    nav = p.chromium.launch()
    pag = nav.new_page(locale="es-CO", viewport={"width": 1280, "height": 900})
    pag.goto(URL, wait_until="networkidle")
    pag.wait_for_timeout(4000)
    pag.screenshot(path="capturas/0.png", full_page=True)
    try:
        for i, paso in enumerate(PASOS, 1):
            pag.get_by_text(re.compile(paso, re.I)).first.click(timeout=15000)
            pag.wait_for_timeout(3000)
            pag.screenshot(path=f"capturas/{i}.png", full_page=True)
            llegue = paso
    except Exception:
        error = f" | Falló en: {paso}"
    texto = pag.inner_text("body")
    with open("capturas/texto_final.txt", "w") as f:
        f.write(texto)
    nav.close()

avisar(f"Prueba ✅ Llegó hasta: {llegue}{error}\n\n{texto[:600]}")
