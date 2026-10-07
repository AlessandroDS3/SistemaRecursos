"use strict";
const $ = (selector) => document.querySelector(selector);
let catalog = { recursos: [], categorias: [], tipos: [] };
let activeResource = null;
let addingTo = null;
let toastTimer;
const labels = { LIBRO: "Libro", LAPTOP: "Laptop", PROYECTOR: "Proyector", CARGADOR: "Cargador", MOUSE: "Mouse", TABLET: "Tablet", OTRO: "Otro", DISPONIBLE: "Disponible", PRESTADO: "Prestado", RESERVADO: "Reservado", DANADO: "Dañado", MANTENIMIENTO: "Mantenimiento", PERDIDO: "Perdido" };
const drawings = {
  LAPTOP: '<rect x="17" y="9" width="66" height="45" rx="4"/><rect x="22" y="14" width="56" height="34" rx="1"/><path d="M17 54 8 64h84l-9-10M39 58h22"/>',
  LIBRO: '<path d="M15 12c14-4 25-2 35 4 10-6 21-8 35-4v49c-14-4-25-2-35 4-10-6-21-8-35-4Z"/><path d="M50 16v49M23 25l18 3M23 34l18 3M23 43l18 3M59 28l18-3M59 37l18-3M59 46l18-3"/>',
  PROYECTOR: '<rect x="10" y="23" width="80" height="34" rx="7"/><circle cx="69" cy="40" r="12"/><circle cx="69" cy="40" r="7"/><path d="M20 35h18M20 41h18M20 47h12M23 57v5M77 57v5M23 18h25"/>',
  TABLET: '<rect x="28" y="5" width="44" height="63" rx="5"/><rect x="33" y="12" width="34" height="45" rx="1"/><circle cx="50" cy="62" r="1"/>',
  MOUSE: '<path d="M30 35a20 20 0 0 1 40 0v15a20 20 0 0 1-40 0ZM50 15V3M30 36h40M50 15v21"/>',
  CARGADOR: '<rect x="24" y="24" width="40" height="32" rx="5"/><path d="M34 24V13M53 24V13M64 40h10a10 10 0 0 1 0 20H57M44 31l-6 11h11l-5 9"/>',
  OTRO: '<path d="m17 22 33-14 33 14v34L50 70 17 56ZM17 22l33 14 33-14M50 36v34M33 15l33 14"/>'
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data)
  });
  if(response.status===401){window.location.replace('/login');throw new Error('La sesión terminó.');}
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "No se pudo completar la operación.");
  return result;
}

function populate(selector, values, label, value) {
  const select = $(selector);
  select.replaceChildren();
  values.forEach((item) => select.add(new Option(label(item), value(item))));
}

async function load() {
  $("#status").textContent = "Cargando inventario...";
  $("#retry").hidden = true;
  try {
    catalog = await api("/api/catalogo");
    const currentType = $("#type-filter").value;
    populate("#type-filter", ["", ...catalog.tipos], (t) => labels[t] || "Todos los tipos", (t) => t);
    $("#type-filter").value = currentType;
    populate("#resource-type", catalog.tipos, (t) => labels[t], (t) => t);
    populate("#resource-category", catalog.categorias, (c) => c.nombre, (c) => c.idCategoria);
    $("#stat-resources").textContent = catalog.recursos.length;
    $("#stat-total").textContent = catalog.recursos.reduce((sum, r) => sum + r.total, 0);
    $("#stat-available").textContent = catalog.recursos.reduce((sum, r) => sum + r.disponibles, 0);
    $("#new-resource").disabled = false;
    $("#status").textContent = "";
    render();
    return true;
  } catch (error) {
    $("#status").textContent = "No se pudo actualizar el catálogo. Verifica que el servidor esté iniciado.";
    $("#retry").hidden = false;
    return false;
  }
}

const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function render() {
  const query = normalize($("#search").value.trim());
  const type = $("#type-filter").value;
  const availability = $("#availability").value;
  const results = catalog.recursos.filter((r) => {
    const searchable = normalize([r.nombre, r.marca, r.modelo, ...r.bienes.map((b) => b.codigoInventario)].join(" "));
    return searchable.includes(query) && (!type || r.tipo === type) &&
      (!availability || (availability === "yes" ? r.disponibles > 0 : r.disponibles === 0));
  });
  $("#cards").replaceChildren();
  $("#result-count").textContent = results.length;
  $("#empty").hidden = results.length > 0;
  $("#empty-title").textContent = catalog.recursos.length ? "No encontramos coincidencias" : "Tu inventario empieza aquí";
  $("#empty-description").textContent = catalog.recursos.length ? "Prueba con otro nombre o limpia los filtros." : "Registra un recurso y su primer ejemplar para empezar.";
  results.forEach((r) => {
    const card = element("article", "resource-card");
    const art = element("div", "card-art");
    art.dataset.type = r.tipo;
    art.setAttribute("aria-hidden", "true");
    // Solo SVG constantes de la aplicación; los datos del usuario usan textContent.
    art.innerHTML = `<svg viewBox="0 0 100 76">${drawings[r.tipo] || drawings.OTRO}</svg>`;
    const content = element("div", "card-content");
    content.append(element("span", "card-type", labels[r.tipo].toUpperCase()), element("h3", "", r.nombre),
      element("div", "card-meta", [r.marca, r.modelo].filter(Boolean).join(" · ") || r.categoria));
    const bottom = element("div", "card-bottom");
    bottom.append(element("span", `badge ${r.disponibles ? "" : "unavailable"}`, `${r.disponibles} de ${r.total} disponibles`));
    const button = element("button", "card-button", "Ver detalle ");
    button.setAttribute("aria-label", `Ver detalle de ${r.nombre}`);
    button.addEventListener("click", () => showDetail(r.idRecurso));
    bottom.append(button);
    content.append(bottom);
    card.append(art, content);
    $("#cards").append(card);
  });
}

function showDetail(id) {
  activeResource = id;
  const r = catalog.recursos.find((item) => item.idRecurso === id);
  $("#detail-type").textContent = `${labels[r.tipo]} · ${r.categoria}`;
  $("#detail-title").textContent = r.nombre;
  $("#detail-meta").textContent = [r.marca, r.modelo].filter(Boolean).join(" · ") || "Sin marca o modelo especificados";
  $("#detail-description").textContent = r.descripcion || "Sin descripción adicional.";
  $("#bien-rows").replaceChildren();
  r.bienes.forEach((b) => {
    const row = element("tr");
    const code = element("td", "", b.codigoInventario);
    code.append(element("small", "", b.numeroSerie || "Sin número de serie"));
    const state = element("td");
    state.append(element("span", `badge ${b.estado === "DISPONIBLE" ? "" : "unavailable"}`, labels[b.estado]));
    row.append(code, element("td", "", b.ubicacion), element("td", "", b.fechaAdquisicion.split("-").reverse().join("/")), state);
    $("#bien-rows").append(row);
  });
  if (!$("#detail-dialog").open) $("#detail-dialog").showModal();
}

function openForm(id = null) {
  addingTo = id;
  $("#resource-form").reset();
  $("#form-error").hidden = true;
  $("#resource-fields").hidden = id !== null;
  $("#resource-fields").disabled = id !== null;
  $("#form-title").textContent = id ? "Agregar ejemplar" : "Registrar recurso";
  $("#form-description").textContent = id ? catalog.recursos.find((r) => r.idRecurso === id).nombre : "Describe el recurso y registra su primer ejemplar físico.";
  $("#bien-legend").textContent = id ? "Datos del bien material" : "02 · Primer bien material";
  $("#save").textContent = id ? "Guardar ejemplar" : "Guardar recurso";
  $("#resource-dialog").showModal();
}

$("#resource-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.target));
  const bien = Object.fromEntries(["codigoInventario", "ubicacion"].map((key) => [key, values[key]]));
  const resourceId = addingTo;
  $("#save").disabled = true;
  $("#save").textContent = "Guardando...";
  $("#form-error").hidden = true;
  try {
    let savedId = resourceId;
    if (resourceId) {
      await api(`/api/recursos/${resourceId}/bienes`, bien);
    } else {
      const recurso = Object.fromEntries(["nombre", "tipo", "marca", "modelo", "descripcion"].map((key) => [key, values[key]]));
      recurso.idCategoriaRef = Number(values.idCategoriaRef);
      const result = await api("/api/recursos", { recurso, bien });
      savedId = result.idRecurso;
    }
    $("#resource-dialog").close();
    const refreshed = await load();
    if (refreshed && resourceId) showDetail(savedId);
    notify(refreshed ? (resourceId ? "Ejemplar registrado correctamente." : "Recurso registrado correctamente.") : "Guardado correctamente. Reintenta la conexión para actualizar el catálogo.");
  } catch (error) {
    $("#form-error").textContent = error.message || "No se pudo guardar.";
    $("#form-error").hidden = false;
  } finally {
    $("#save").disabled = false;
    $("#save").textContent = resourceId ? "Guardar ejemplar" : "Guardar recurso";
  }
});

function notify(message) {
  clearTimeout(toastTimer);
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => { $("#toast").hidden = true; }, 5000);
}

$("#new-resource").addEventListener("click", () => openForm());
$("#add-bien").addEventListener("click", () => openForm(activeResource));
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => {
  if (!$("#save").disabled) document.getElementById(button.dataset.close).close();
}));
$("#resource-dialog").addEventListener("cancel", (event) => { if ($("#save").disabled) event.preventDefault(); });
$("#retry").addEventListener("click", load);
$("#search").addEventListener("input", render);
$("#type-filter").addEventListener("change", render);
$("#availability").addEventListener("change", render);
$("#clear-filters").addEventListener("click", () => {
  $("#search").value = "";
  $("#type-filter").value = "";
  $("#availability").value = "";
  render();
});
load();
