// Página de "Compartir con ¿Le creo?". Todo el texto se pinta con textContent:
// lo que viene del mensaje o del modelo nunca se interpreta como HTML.
"use strict";

const $ = (id) => document.getElementById(id);
const secciones = { entrada: $("entrada"), espera: $("espera"), resultado: $("resultado") };

function mostrar(nombre) {
  for (const [clave, el] of Object.entries(secciones)) el.hidden = clave !== nombre;
}

function parrafo(texto) {
  const p = document.createElement("p");
  p.textContent = texto;
  return p;
}

function lista(titulo, items) {
  const frag = document.createDocumentFragment();
  const h = document.createElement("h2");
  h.textContent = titulo;
  const ul = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.append(li);
  }
  frag.append(h, ul);
  return frag;
}

function pintar(datos) {
  const [orden = "", ...resto] = datos.lineas || [];
  const accion = resto.length > 1 ? resto[resto.length - 1] : (resto[0] || "");
  const porque = resto.length > 1 ? resto.slice(0, -1).join(" ") : "";

  $("tarjeta").className = `tarjeta ${datos.semaforo}`;
  $("orden").textContent = orden;
  $("porque").textContent = porque;
  $("porque").hidden = !porque;
  $("accion").textContent = accion;

  const cuerpo = $("detalle-cuerpo");
  cuerpo.replaceChildren();
  if (datos.ademas) cuerpo.append(parrafo(`Además: ${datos.ademas}`));
  if (datos.trucos && datos.trucos.length)
    cuerpo.append(lista("El truco que usan", datos.trucos.map((t) => `${t.nombre}: «${t.evidencia}»`)));
  if (datos.revise && datos.revise.length) cuerpo.append(lista("Qué revisé", datos.revise));
  if (datos.truncado) cuerpo.append(parrafo("El mensaje era muy largo: revisé solo el comienzo."));
  if (datos.leido) {
    const h = document.createElement("h2");
    h.textContent = datos.tipo === "audio" ? "Esto es lo que escuché en el audio" : "Esto es lo que leí en la captura";
    const p = parrafo(datos.leido);
    p.className = "leido";
    cuerpo.append(h, p);
  }
  $("detalle").hidden = !cuerpo.childElementCount;
  $("detalle").open = false;

  const avisos = $("avisos");
  avisos.replaceChildren(...(datos.avisos || []).map((a) => {
    const li = document.createElement("li");
    li.textContent = a;
    return li;
  }));
  avisos.hidden = !avisos.childElementCount;
  $("reintentar").hidden = !(datos.reintentar && ultimo);

  mostrar("resultado");
  $("tarjeta").scrollIntoView({ behavior: "smooth", block: "start" });
}

let ultimo = null;   // lo último que se revisó, para el botón Reintentar tras un timeout

async function revisar(texto) {
  texto = (texto || "").trim();
  if (!texto) {
    $("texto").focus();
    return;
  }
  ultimo = { texto };
  mostrar("espera");
  try {
    const resp = await fetch("/api/analizar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
    });
    pintar(await resp.json());
  } catch {
    pintar({ semaforo: "error", lineas: ["⚠️ No pude conectarme. Revisa tu internet e inténtalo de nuevo."] });
  }
}

async function revisarCaptura(archivo) {
  if (!archivo) return;
  ultimo = { archivo };
  mostrar("espera");
  const datos = new FormData();
  datos.append("archivo", archivo);
  try {
    const resp = await fetch("/api/analizar_archivo", { method: "POST", body: datos });
    pintar(await resp.json());
  } catch {
    pintar({ semaforo: "error", lineas: ["⚠️ No pude conectarme. Revisa tu internet e inténtalo de nuevo."] });
  }
}

function marcarOrigen(texto) {
  $("origen").textContent = texto;
  $("origen").hidden = false;
}

$("revisar").addEventListener("click", () => revisar($("texto").value));

$("reintentar").addEventListener("click", () => {
  if (ultimo && ultimo.texto) revisar(ultimo.texto);
  else if (ultimo && ultimo.archivo) revisarCaptura(ultimo.archivo);
});

$("captura").addEventListener("change", (e) => {
  revisarCaptura(e.target.files[0]);
  e.target.value = "";   // permite elegir la misma imagen otra vez
});

$("pegar").addEventListener("click", async () => {
  try {
    const texto = await navigator.clipboard.readText();
    $("texto").value = texto;
    revisar(texto);
  } catch {
    // Sin permiso para leer el portapapeles: se deja el cursor listo para pegar a mano.
    $("texto").focus();
  }
});

$("otro").addEventListener("click", () => {
  $("origen").hidden = true;
  $("texto").value = "";
  mostrar("entrada");
  $("texto").focus();
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

// Si llegamos desde el menú Compartir, el servidor dejó lo compartido incrustado como JSON:
// un texto por analizar, o el resultado ya listo de una captura.
const compartido = JSON.parse($("compartido").textContent);
if (compartido !== null) {
  history.replaceState(null, "", "/");   // recargar no vuelve a enviar el formulario
  if (compartido.resultado) {
    marcarOrigen(compartido.origen === "audio" ? "📤 Nota de voz recibida desde WhatsApp" : "📤 Captura recibida desde WhatsApp");
    pintar(compartido.resultado);
  } else {
    marcarOrigen("📤 Recibido desde WhatsApp");
    $("texto").value = compartido.texto || "";
    revisar(compartido.texto);
  }
}
