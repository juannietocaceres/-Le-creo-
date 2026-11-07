// Página de "Compartir con ¿Le creo?". Todo el texto se pinta con textContent:
// lo que viene del mensaje o del modelo nunca se interpreta como HTML.
"use strict";

const $ = (id) => document.getElementById(id);
const secciones = { entrada: $("entrada"), espera: $("espera"), resultado: $("resultado") };

// Lo que va diciendo mientras revisa: los pasos reales del agente, en palabras de todos los días.
const PASOS_ESPERA = [
  "Leyendo el mensaje…",
  "Buscando el número en los reportes…",
  "Mirando el enlace, sin abrirlo…",
  "Revisando cómo contacta de verdad la entidad…",
  "Decidiendo el color del semáforo…",
];
let relojEspera = null;

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
  if (nombre !== "resultado") callar();
}

// El semáforo ya muestra el color: el emoji del inicio sobra en pantalla (y se lee raro en voz alta).
const sinEmoji = (t) => (t || "").replace(/^(?:🔴|🟡|🟢|👉|⚠️)\s*/u, "");

function parrafo(texto) {
  const p = document.createElement("p");
  p.textContent = texto;
  return p;
}

function titulo(texto) {
  const h = document.createElement("h3");
  h.textContent = texto;
  return h;
}

function lista(items, clase) {
  const ul = document.createElement("ul");
  ul.className = clase;
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.append(li);
  }
  return ul;
}

function trucos(items) {   // cada truco con la frase del mensaje que lo prueba
  const ul = document.createElement("ul");
  ul.className = "trucos";
  for (const t of items) {
    const li = document.createElement("li");
    const b = document.createElement("b");
    b.textContent = t.nombre;
    const q = document.createElement("q");
    q.textContent = t.evidencia;
    li.append(b, q);
    ul.append(li);
  }
  return ul;
}

function pintar(datos) {
  const [orden = "", ...resto] = datos.lineas || [];
  const accion = resto.length > 1 ? resto[resto.length - 1] : (resto[0] || "");
  const porque = resto.length > 1 ? resto.slice(0, -1).join(" ") : "";

  $("tarjeta").className = `tarjeta ${datos.semaforo}`;
  $("orden").textContent = sinEmoji(orden);
  $("porque").textContent = porque;
  $("porque").hidden = !porque;
  $("accion").textContent = sinEmoji(accion);
  $("accion").hidden = !accion;
  pintarAyudas(datos);

  const cuerpo = $("detalle-cuerpo");
  cuerpo.replaceChildren();
  if (datos.trucos && datos.trucos.length) cuerpo.append(titulo("El truco que usan"), trucos(datos.trucos));
  if (datos.ademas) cuerpo.append(titulo("Además"), parrafo(datos.ademas));
  if (datos.revise && datos.revise.length) cuerpo.append(titulo("Qué revisé"), lista(datos.revise, "revise"));
  if (datos.truncado) cuerpo.append(parrafo("El mensaje era muy largo: revisé solo el comienzo."));
  if (datos.leido) {
    const p = parrafo(datos.leido);
    p.className = "leido";
    cuerpo.append(titulo(datos.tipo === "audio" ? "Lo que escuché en el audio" : "Lo que leí en la foto"), p);
  }
  if (datos.analizado_con) {
    const p = parrafo(`Analizado con ${datos.analizado_con}`);
    p.className = "analizado-con";
    cuerpo.append(p);
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

// ── B3: llamar a la línea oficial · B2: escuchar la respuesta ───────────────
// El número del botón llega aparte desde el servidor y sale de la tabla verificada, nunca del modelo.

function pintarAyudas(datos) {
  const llamar = $("llamar");
  if (datos.llamar && /^\d{3,15}$/.test(datos.llamar.marcar)) {
    llamar.href = `tel:${datos.llamar.marcar}`;
    const linea = document.createElement("span");
    linea.textContent = `📞 Llamar a ${datos.llamar.entidad}`;
    const numero = document.createElement("small");
    numero.textContent = datos.llamar.numero;
    llamar.replaceChildren(linea, numero);
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
