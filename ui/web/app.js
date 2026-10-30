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
  $("detalle").hidden = !cuerpo.childElementCount;
  $("detalle").open = false;

  mostrar("resultado");
  $("tarjeta").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function revisar(texto) {
  texto = (texto || "").trim();
  if (!texto) {
    $("texto").focus();
    return;
  }
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

$("revisar").addEventListener("click", () => revisar($("texto").value));

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

// Si llegamos desde el menú Compartir, el servidor dejó el texto incrustado como JSON.
const compartido = JSON.parse($("compartido").textContent);
if (compartido !== null) {
  history.replaceState(null, "", "/");   // recargar no vuelve a enviar el formulario
  $("origen").hidden = false;
  $("texto").value = compartido;
  revisar(compartido);
}
