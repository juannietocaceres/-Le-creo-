// Página de "Compartir con ¿Le creo?". Todo el texto se pinta con textContent:
// lo que viene del mensaje o del modelo nunca se interpreta como HTML.
"use strict";

const $ = (id) => document.getElementById(id);
const secciones = { entrada: $("entrada"), espera: $("espera"), resultado: $("resultado") };
const SVG = "http://www.w3.org/2000/svg";

// Lo que va diciendo mientras revisa: los pasos reales del agente, en palabras de todos los días.
const PASOS_ESPERA = [
  "Leyendo el mensaje…",
  "Buscando el número en los reportes…",
  "Mirando el enlace, sin abrirlo…",
  "Revisando cómo contacta de verdad la entidad…",
  "Decidiendo el color del semáforo…",
];
let relojEspera = null;

// Pantalla completa: cada estado pinta el fondo, la etiqueta de arriba y el título del porqué.
const ESTADOS = {
  rojo:     { etiqueta: "Parece estafa",           titulo: "Por qué es roja",     barra: "#d21f3c" },
  amarillo: { etiqueta: "Ten cuidado",             titulo: "Por qué es amarilla", barra: "#f5b700" },
  verde:    { etiqueta: "Sin señales",             titulo: "Por qué es verde",    barra: "#0e8a57" },
  rechazo:  { etiqueta: "Fuera de lo que reviso",  titulo: "Detalle",             barra: "#3b3552" },
  error:    { etiqueta: "No pude revisar",         titulo: "Detalle",             barra: "#3b3552" },
  vacio:    { etiqueta: "Falta el mensaje",        titulo: "Detalle",             barra: "#3b3552" },
};
const COLOR_BARRA_INICIO = "#f4f2f8";

function pintarFondo(semaforo) {
  if (semaforo) document.body.dataset.estado = ["rojo", "amarillo", "verde"].includes(semaforo) ? semaforo : "neutro";
  else delete document.body.dataset.estado;
  $("color-barra").content = semaforo ? (ESTADOS[semaforo] || ESTADOS.error).barra : COLOR_BARRA_INICIO;
}

function mostrar(nombre) {
  for (const [clave, el] of Object.entries(secciones)) el.hidden = clave !== nombre;
  clearInterval(relojEspera);
  if (nombre === "espera") {
    let i = 0;
    $("paso-espera").textContent = PASOS_ESPERA[0];
    relojEspera = setInterval(() => {
      i = Math.min(i + 1, PASOS_ESPERA.length - 1);
      $("paso-espera").textContent = PASOS_ESPERA[i];
    }, 1600);
  }
  if (nombre !== "resultado") {
    callar();
    pintarFondo(null);
  }
  window.scrollTo(0, 0);
}

// El fondo y las luces ya dicen el color: el emoji del inicio sobra en pantalla (y se lee raro en voz alta).
const sinEmoji = (t) => (t || "").replace(/^(?:🔴|🟡|🟢|👉|⚠️)\s*/u, "");
const mayuscula = (t) => t.charAt(0).toUpperCase() + t.slice(1);

function parrafo(texto, clase) {
  const p = document.createElement("p");
  p.textContent = texto;
  if (clase) p.className = clase;
  return p;
}

// ── Por qué: una línea por hallazgo, con su ícono ─────────────────────────

function icono(nombre) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", "ico");
  svg.setAttribute("aria-hidden", "true");
  const uso = document.createElementNS(SVG, "use");
  uso.setAttribute("href", `#i-${nombre}`);
  svg.append(uso);
  return svg;
}

function iconoDeRevision(texto) {
  if (/enlace/i.test(texto)) return "enlace";
  if (/número/i.test(texto)) return "telefono";
  if (/contacta|canal/i.test(texto)) return "banco";
  return "lupa";
}

function iconoDeTruco(nombre) {
  if (/urgencia|presión|tiempo/i.test(nombre)) return "reloj";
  if (/familiar|amigo/i.test(nombre)) return "persona";
  if (/autoridad|entidad|banco/i.test(nombre)) return "banco";
  if (/enlace/i.test(nombre)) return "enlace";
  return "alerta";
}

function hallazgo(nombreIcono, titulo, detalle) {
  const li = document.createElement("li");
  const texto = document.createElement("div");
  const b = document.createElement("b");
  b.textContent = titulo;
  texto.append(b);
  if (detalle) {
    const span = document.createElement("span");
    span.textContent = detalle;
    texto.append(span);
  }
  li.append(icono(nombreIcono), texto);
  return li;
}

function pintarDetalle(datos) {
  const cuerpo = $("detalle-cuerpo");
  cuerpo.replaceChildren();
  const lista = document.createElement("ul");
  lista.className = "hallazgos";
  for (const r of datos.revise || []) {
    const titulo = /^cómo contacta/i.test(r) ? `Revisé ${r}` : mayuscula(r);   // que se lea como hallazgo
    lista.append(hallazgo(iconoDeRevision(r), titulo));
  }
  for (const t of datos.trucos || []) lista.append(hallazgo(iconoDeTruco(t.nombre), t.nombre, `«${t.evidencia}»`));
  if (datos.ademas) lista.append(hallazgo("idea", "Además", datos.ademas));
  if (datos.truncado) lista.append(hallazgo("alerta", "El mensaje era muy largo", "Revisé solo el comienzo."));
  if (lista.childElementCount) cuerpo.append(lista);
  if (datos.leido) {
    cuerpo.append(parrafo(datos.tipo === "audio" ? "Lo que escuché en el audio:" : "Lo que leí en la foto:", "analizado-con"));
    cuerpo.append(parrafo(datos.leido, "leido"));
  }
  if (datos.analizado_con) cuerpo.append(parrafo(`Analizado con ${datos.analizado_con}`, "analizado-con"));
  $("detalle-titulo").textContent = (ESTADOS[datos.semaforo] || ESTADOS.error).titulo;
  $("detalle").hidden = true;
  $("ver-porque").hidden = !cuerpo.childElementCount;
}

function pintar(datos) {
  const [orden = "", ...resto] = datos.lineas || [];
  const accion = resto.length > 1 ? resto[resto.length - 1] : (resto[0] || "");
  const porque = resto.length > 1 ? resto.slice(0, -1).join(" ") : "";

  pintarFondo(datos.semaforo);
  $("estado").textContent = (ESTADOS[datos.semaforo] || ESTADOS.error).etiqueta;
  $("orden").textContent = sinEmoji(orden);
  $("porque").textContent = porque;
  $("porque").hidden = !porque;
  $("accion").textContent = sinEmoji(accion);
  $("accion").hidden = !accion;
  pintarAyudas(datos);
  pintarDetalle(datos);

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
}

$("ver-porque").addEventListener("click", () => {
  $("detalle").hidden = false;
  $("detalle").scrollIntoView({ behavior: "smooth", block: "start" });
});

// ── B3: llamar a la línea oficial · B2: escuchar la respuesta ───────────────
// El número del botón llega aparte desde el servidor y sale de la tabla verificada, nunca del modelo.

function pintarAyudas(datos) {
  const llamar = $("llamar");
  if (datos.llamar && /^\d{3,15}$/.test(datos.llamar.marcar)) {
    llamar.href = `tel:${datos.llamar.marcar}`;
    const numero = document.createElement("small");
    numero.textContent = datos.llamar.numero;
    llamar.replaceChildren(document.createTextNode(`Llamar a ${datos.llamar.entidad}`), numero);
    llamar.hidden = false;
  } else {
    llamar.hidden = true;
  }
  $("escuchar").hidden = !("speechSynthesis" in window) || !["rojo", "amarillo", "verde"].includes(datos.semaforo);
}

function callar() {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  $("escuchar-texto").textContent = "Escuchar";
}

function escuchar() {
  if (speechSynthesis.speaking) return callar();
  const texto = [$("orden"), $("porque"), $("accion")]
    .filter((el) => !el.hidden && el.textContent).map((el) => el.textContent).join(". ");
  const voz = new SpeechSynthesisUtterance(texto);
  const voces = speechSynthesis.getVoices();
  voz.voice = voces.find((v) => v.lang === "es-CO") || voces.find((v) => v.lang.startsWith("es")) || null;
  voz.lang = voz.voice ? voz.voice.lang : "es-CO";
  voz.rate = 0.9;   // un poco más despacio que lo normal
  voz.onend = voz.onerror = () => ($("escuchar-texto").textContent = "Escuchar");
  $("escuchar-texto").textContent = "Parar";
  speechSynthesis.speak(voz);
}

$("escuchar").addEventListener("click", escuchar);

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
      boton("Reportar este número", "", confirmar),
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

// ── Revisar ────────────────────────────────────────────────────────────────

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
    pintar({ semaforo: "error", lineas: ["No pude conectarme. Revisa tu internet e inténtalo de nuevo."] });
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
    pintar({ semaforo: "error", lineas: ["No pude conectarme. Revisa tu internet e inténtalo de nuevo."] });
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
    marcarOrigen(compartido.origen === "audio" ? "Nota de voz recibida desde WhatsApp" : "Foto recibida desde WhatsApp");
    pintar(compartido.resultado);
  } else {
    marcarOrigen("Recibido desde WhatsApp");
    $("texto").value = compartido.texto || "";
    revisar(compartido.texto);
  }
}
