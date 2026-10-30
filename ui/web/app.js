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
  pintarAcciones(datos);

  mostrar("resultado");
  $("tarjeta").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Acciones que la persona aprueba con un clic (D14) ───────────────────────
// El servidor solo escribe en la base si recibe el permiso de un solo uso que vino con el resultado.

function boton(texto, clase, alHacerClic) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `boton-chico ${clase || ""}`;
  b.textContent = texto;
  b.addEventListener("click", alHacerClic);
  return b;
}

function legible(numero) {   // +573000000007 → +57 300 000 0007
  return numero.replace(/^\+57(\d{3})(\d{3})(\d{4})$/, "+57 $1 $2 $3");
}

async function enviarAccion(ruta, cuerpo, bloque) {
  bloque.querySelectorAll("button").forEach((b) => (b.disabled = true));
  let mensaje;
  try {
    const resp = await fetch(ruta, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
    });
    mensaje = (await resp.json()).mensaje;
  } catch {
    mensaje = "No pude conectarme. Inténtalo de nuevo.";
  }
  bloque.replaceChildren(parrafo(mensaje));
}

function bloqueReporte(analisisId, { numero, permiso }) {
  const bloque = document.createElement("div");
  bloque.className = "bloque";
  const inicio = () => {
    bloque.replaceChildren(
      parrafo(`¿Te escribieron desde el ${legible(numero)}?`),
      boton(`🚩 Reportar este número`, "", confirmar),
    );
  };
  const confirmar = () => {
    bloque.replaceChildren(
      parrafo(`Vas a sumar un reporte al ${legible(numero)}. Con 3 reportes queda en alerta para todos. ¿Seguro?`),
      Object.assign(document.createElement("div"), { className: "fila-botones" }),
    );
    bloque.lastChild.append(
      boton("Sí, reportar", "fuerte", () => enviarAccion("/api/reportar", { analisis_id: analisisId, numero, permiso }, bloque)),
      boton("Cancelar", "", inicio),
    );
  };
  inicio();
  return bloque;
}

function bloqueFeedback(analisisId, permiso) {
  const bloque = document.createElement("div");
  bloque.className = "bloque";
  const fila = Object.assign(document.createElement("div"), { className: "fila-botones" });
  const enviar = (usuario_dice) => enviarAccion("/api/feedback", { analisis_id: analisisId, usuario_dice, permiso }, bloque);
  fila.append(boton("Sí era estafa", "", () => enviar("era_estafa")), boton("No era estafa", "", () => enviar("no_era_estafa")));
  bloque.append(parrafo("¿Me equivoqué? Cuéntame qué era en realidad:"), fila);
  return bloque;
}

function pintarAcciones(datos) {
  const acciones = $("acciones");
  acciones.replaceChildren();
  if (datos.analisis_id) {
    for (const r of datos.reportables || []) acciones.append(bloqueReporte(datos.analisis_id, r));
    if (datos.permiso_feedback) acciones.append(bloqueFeedback(datos.analisis_id, datos.permiso_feedback));
  }
  acciones.hidden = !acciones.childElementCount;
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
