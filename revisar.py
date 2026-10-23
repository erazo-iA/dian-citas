import os, urllib.request
from playwright.sync_api import sync_playwright

TOPIC = os.environ["NTFY_TOPIC"]
URL = "https://agendamiento.dian.gov.co/"
PASOS = [r"Agendar cita", r"Persona natural", r"Video\s*Atenci", r"Devoluciones"]

def avisar(msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=msg.encode("utf-8"),
        headers={"Title": "Citas DIAN", "Priority": "high", "Click": URL})
    urllib.request.urlopen(req)

def clic(pag, patron):
    loc = pag.locator(f"text=/{patron}/i >> visible=true").first
    loc.wait_for(timeout=20000)
    try:
        loc.click(timeout=10000)
    except Exception:
        loc.click(force=True, timeout=10000)

os.makedirs("capturas", exist_ok=True)
llegue, error = "inicio", ""
with sync_playwright() as p:
    nav = p.chromium.launch()
    pag = nav.new_page(locale="es-CO", viewport={"width": 1280, "height": 900})
    pag.goto(URL, wait_until="load", timeout=60000)
    pag.wait_for_timeout(6000)
    pag.screenshot(path="capturas/0.png", full_page=True)
    for i, paso in enumerate(PASOS, 1):
        try:
            clic(pag, paso)
            pag.wait_for_timeout(4000)
            pag.screenshot(path=f"capturas/{i}.png", full_page=True)
            llegue = paso
        except Exception as e:
            error = f" | Falló en: {paso} ({str(e).splitlines()[0][:150]})"
            pag.screenshot(path="capturas/error.png", full_page=True)
            break
    texto = pag.inner_text("body")
    with open("capturas/texto_final.txt", "w") as f:
        f.write(texto)
    nav.close()

avisar(f"Prueba ✅ Llegó hasta: {llegue}{error}\n\n{texto[:500]}")
