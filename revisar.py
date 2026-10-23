import os, time, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

TOPIC = os.environ["NTFY_TOPIC"]
URL = "https://agendamiento.dian.gov.co/"
TZ = ZoneInfo("America/Bogota")
MANUAL = os.environ.get("GITHUB_EVENT_NAME") != "schedule"
PASOS = [r"Agendar cita", r"Persona\s+Natural", r"Videoatenci", r"Devoluciones"]
ESPERA = 60  # segundos entre revisiones

def avisar(msg, titulo="Citas DIAN", prioridad="default", tags=""):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=msg.encode("utf-8"),
        headers={"Title": titulo, "Priority": prioridad, "Tags": tags, "Click": URL})
    urllib.request.urlopen(req, timeout=20)

def esperar_carga(pag):
    pag.wait_for_timeout(1000)
    for _ in range(60):
        if pag.locator("text=Cargando >> visible=true").count() == 0:
            break
        pag.wait_for_timeout(500)
    pag.wait_for_timeout(1000)

def clic(pag, patron):
    loc = pag.locator(f"text=/{patron}/i >> visible=true").first
    loc.wait_for(timeout=30000)
    try:
        loc.click(timeout=10000)
    except Exception:
        loc.click(force=True, timeout=10000)
    esperar_carga(pag)

def revisar(nav):
    pag = nav.new_page(locale="es-CO", viewport={"width": 1280, "height": 900})
    try:
        pag.goto(URL, wait_until="load", timeout=60000)
        esperar_carga(pag)
        for paso in PASOS:
            clic(pag, paso)
        pag.wait_for_timeout(3000)
        esperar_carga(pag)
        texto = pag.inner_text("body").lower()
        pag.screenshot(path="capturas/ultima.png", full_page=True)
        if "no se encontraron especialidades" in texto:
            return "no_hay"
        if "medell" in texto:
            pag.screenshot(path="capturas/alerta.png", full_page=True)
            return "hay"
        return "raro"
    finally:
        pag.close()

os.makedirs("capturas", exist_ok=True)
ahora = datetime.now(TZ)
if ahora.hour * 60 + ahora.minute < 13 * 60 + 30:
    inicio = ahora.replace(hour=11, minute=0, second=0)
else:
    inicio = ahora.replace(hour=14, minute=0, second=0)
fin = inicio + timedelta(hours=3)
if not MANUAL:
    while datetime.now(TZ) < inicio:
        time.sleep(20)

ultimo, fallos, ult_error = {}, 0, ""
with sync_playwright() as p:
    nav = p.chromium.launch()
    while True:
        try:
            estado = revisar(nav)
            fallos = 0
        except Exception as e:
            estado, ult_error = "error", str(e).splitlines()[0][:150]
            fallos += 1
        hora = datetime.now(TZ).strftime("%I:%M %p")
        print(hora, estado, flush=True)
        t = time.time()
        if estado == "hay" and t - ultimo.get("hay", 0) > 300:
            avisar(f"HAY CITAS EN MEDELLIN ({hora}). Entra YA: Agendar cita > Persona Natural > Videoatencion > Devoluciones > Medellin",
                   "CITA DIAN DISPONIBLE", "urgent", "rotating_light")
            ultimo["hay"] = t
        elif estado == "raro" and t - ultimo.get("raro", 0) > 1800:
            avisar(f"La pagina mostro algo distinto al mensaje de 'no hay citas' ({hora}). Puede haber citas en otra ciudad; revisa.",
                   "Citas DIAN: revisar", "high", "eyes")
            ultimo["raro"] = t
        elif estado == "error" and fallos == 5:
            avisar(f"5 intentos fallidos seguidos ({hora}). La pagina de la DIAN puede estar caida. {ult_error}",
                   "Citas DIAN: problema", "default", "warning")
        if MANUAL:
            if estado == "no_hay":
                avisar(f"Revision manual ({hora}): no hay citas por ahora. Todo funciona ✅")
            elif estado == "error":
                avisar(f"Revision manual ({hora}): fallo ❌ {ult_error}")
            break
        if datetime.now(TZ) >= fin:
            break
        time.sleep(ESPERA)
    nav.close()
