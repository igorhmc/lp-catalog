let selectedAlbum = null;
let currentSearch = {
  query: "",
  page: 1,
  hasMore: false,
};

function splitTrackPosition(rawPosition, rawSide = "") {
  const position = String(rawPosition || "").trim();
  const side = String(rawSide || "").trim();
  const match = position.match(/^([A-Za-z]+)\s*[-.]?\s*(\d+)$/);

  if (!match) {
    return { side, position };
  }

  const parsedSide = match[1].toUpperCase();
  if (side && side.toUpperCase() !== parsedSide) {
    return { side, position };
  }

  return {
    side: side || parsedSide,
    position: match[2],
  };
}

function normalizeTrack(track = {}) {
  const split = splitTrackPosition(track.position, track.side);
  return {
    disc_number: track.disc_number || "",
    side: split.side,
    position: split.position,
    title: track.title || "",
    duration: track.duration || "",
  };
}

function normalizeTrackRow(row) {
  const sideInput = row.querySelector("[name='track_side']");
  const positionInput = row.querySelector("[name='track_position']");
  const split = splitTrackPosition(positionInput.value, sideInput.value);

  sideInput.value = split.side;
  positionInput.value = split.position;
}

async function suggestSlotPosition() {
  const slotSelect = document.querySelector("[name='storage_slot_id']");
  const positionInput = document.querySelector("[name='slot_position']");
  const helpText = document.getElementById("slot-position-help");
  const slotId = Number.parseInt(slotSelect.value, 10);

  if (!Number.isFinite(slotId)) {
    if (!positionInput.dataset.manual) {
      positionInput.value = "";
    }
    positionInput.disabled = false;
    positionInput.placeholder = "Ex.: 010";
    if (helpText) {
      helpText.textContent = "Para nichos de triagem/pending, a posição individual não é usada.";
    }
    return;
  }

  try {
    const response = await fetch(`/api/v1/copies/meta/storage/${slotId}/next-position`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    if (!payload.uses_positions) {
      positionInput.value = "";
      positionInput.dataset.suggested = "";
      positionInput.dataset.manual = "";
      positionInput.disabled = true;
      positionInput.placeholder = "Não se aplica";
      if (helpText) {
      helpText.textContent = "Este nicho é de triagem/pending. O sistema guarda apenas a quantidade de discos ali.";
      }
      return;
    }
    positionInput.disabled = false;
    positionInput.placeholder = "Ex.: 010";
    if (helpText) {
      helpText.textContent = "Para nichos de triagem/pending, a posição individual não é usada.";
    }
    if (!positionInput.dataset.manual || !positionInput.value.trim()) {
      positionInput.value = payload.next_position || "";
      positionInput.dataset.suggested = payload.next_position || "";
      positionInput.dataset.manual = "";
    }
  } catch (_) {
    // Sugestão falhou; mantém preenchimento manual.
  }
}

function getResultsContainer() {
  return document.getElementById("results");
}

function renderResultCard(album) {
  const tpl = document.getElementById("result-template");
  const node = tpl.content.cloneNode(true);
  const img = node.querySelector("img");

  if (album.cover_url) {
    img.src = album.cover_url;
    img.alt = `Capa do álbum ${album.title}`;
  } else {
    img.replaceWith(document.createElement("span"));
    node.querySelector(".cover span").className = "ph";
    node.querySelector(".cover span").textContent = "Sem capa";
  }

  node.querySelector(".title").textContent = album.title;
  node.querySelector(".artist").textContent = album.artist;
  node.querySelector(".year").textContent = album.year || "";
  node.querySelector(".catalog").textContent = album.catalog_number || "";
  node.querySelector(".select-btn").addEventListener("click", () => prefillEditor(album));
  return node;
}

function clearTracks() {
  document.getElementById("tracks-list").innerHTML = "";
}

function addTrackRow(track = { disc_number: "", side: "", position: "", title: "", duration: "" }) {
  const normalizedTrack = normalizeTrack(track);
  const tpl = document.getElementById("track-template");
  const node = tpl.content.cloneNode(true);
  node.querySelector("[name='track_disc_number']").value = normalizedTrack.disc_number;
  node.querySelector("[name='track_side']").value = normalizedTrack.side;
  node.querySelector("[name='track_position']").value = normalizedTrack.position;
  node.querySelector("[name='track_title']").value = normalizedTrack.title;
  node.querySelector("[name='track_duration']").value = normalizedTrack.duration;
  node.querySelector("[name='track_position']").addEventListener("blur", (event) =>
    normalizeTrackRow(event.currentTarget.closest(".track-item"))
  );
  node.querySelector(".remove-track").onclick = (event) =>
    event.currentTarget.closest(".track-item").remove();
  document.getElementById("tracks-list").appendChild(node);
}

function updateCoverPreview(album) {
  const cover = document.getElementById("cover-preview");
  const placeholder = document.getElementById("cover-placeholder");

  if (album.cover_url) {
    cover.src = album.cover_url;
    cover.alt = `Capa do álbum ${album.title || ""}`;
    cover.classList.remove("is-hidden");
    placeholder.classList.add("is-hidden");
    return;
  }

  cover.removeAttribute("src");
  cover.alt = "Sem imagem";
  cover.classList.add("is-hidden");
  placeholder.classList.remove("is-hidden");
}

function prefillEditor(album) {
  selectedAlbum = JSON.parse(JSON.stringify(album));

  const editor = document.getElementById("editor");
  const form = document.getElementById("album-form");

  form.title.value = selectedAlbum.title || "";
  form.artist_name.value = selectedAlbum.artist || "";
  form.year.value = selectedAlbum.year || "";
  form.genre.value = selectedAlbum.genre || "";
  form.country.value = selectedAlbum.country || "";
  form.label_name.value = selectedAlbum.label_name || "";
  form.catalog_number.value = selectedAlbum.catalog_number || "";
  form.barcode.value = selectedAlbum.barcode || "";
  form.format.value = selectedAlbum.format || "";
  form.style.value = selectedAlbum.style || "";
  form.notes.value = selectedAlbum.notes || "";
  form.discogs_id.value = selectedAlbum.discogs_id || "";
  form.cover_url.value = selectedAlbum.cover_url || "";

  updateCoverPreview(selectedAlbum);

  clearTracks();
  (selectedAlbum.tracks || []).forEach((track) => addTrackRow(track));
  if (!selectedAlbum.tracks || selectedAlbum.tracks.length === 0) {
    addTrackRow();
  }

  editor.classList.remove("is-hidden");
  window.scrollTo({ top: editor.offsetTop - 12, behavior: "smooth" });
}

function openManualEditor() {
  prefillEditor({
    title: "",
    artist: "",
    year: "",
    genre: "",
    country: "",
    label_name: "",
    catalog_number: "",
    barcode: "",
    format: "",
    style: "",
    notes: "",
    discogs_id: "",
    cover_url: "",
    tracks: [],
  });
}

function collectTracks() {
  return Array.from(document.querySelectorAll("#tracks-list .track-item"))
    .map((row) => {
      const discNumberRaw = row.querySelector("[name='track_disc_number']").value;
      return {
        disc_number: discNumberRaw ? Number.parseInt(discNumberRaw, 10) : null,
        side: row.querySelector("[name='track_side']").value.trim() || null,
        position: row.querySelector("[name='track_position']").value.trim(),
        title: row.querySelector("[name='track_title']").value.trim(),
        duration: row.querySelector("[name='track_duration']").value.trim() || "00:00",
      };
    })
    .filter((track) => track.position && track.title);
}

function collectFormData() {
  const form = document.getElementById("album-form");
  const discogsId = Number.parseInt(form.discogs_id.value, 10);
  const rpm = Number.parseInt(form.rpm.value, 10);
  const discsCount = Number.parseInt(form.discs_count.value, 10);
  const slotId = Number.parseInt(form.storage_slot_id.value, 10);
  const purchasePrice = form.purchase_price.value ? Number.parseFloat(form.purchase_price.value) : null;

  return {
    title: form.title.value.trim(),
    artist_name: form.artist_name.value.trim(),
    year: form.year.value ? Number.parseInt(form.year.value, 10) : null,
    genre: form.genre.value.trim() || null,
    country: form.country.value.trim() || null,
    label_name: form.label_name.value.trim() || null,
    catalog_number: form.catalog_number.value.trim() || null,
    barcode: form.barcode.value.trim() || null,
    format: form.format.value.trim() || null,
    rpm: Number.isFinite(rpm) ? rpm : null,
    discs_count: Number.isFinite(discsCount) ? discsCount : null,
    style: form.style.value.trim() || null,
    discogs_id: Number.isFinite(discogsId) ? discogsId : null,
    cover_url: form.cover_url.value || null,
    cover_path: form.cover_path.value || null,
    notes: form.notes.value.trim() || null,
    status: form.status.value,
    usage_status: form.usage_status.value,
    physical_status: form.physical_status.value,
    media_condition: form.media_condition.value || null,
    sleeve_condition: form.sleeve_condition.value || null,
    has_insert: form.has_insert.checked,
    has_obi: form.has_obi.checked,
    purchase_date: form.purchase_date.value || null,
    purchase_price: purchasePrice,
    purchase_from: form.purchase_from.value.trim() || null,
    copy_notes: form.copy_notes.value.trim() || null,
    storage_slot_id: Number.isFinite(slotId) ? slotId : null,
    slot_position: form.slot_position.value.trim() || null,
    tracks: collectTracks(),
  };
}

async function loadMoreResults() {
  const results = getResultsContainer();
  const loadMoreBtn = document.querySelector(".load-more");

  if (loadMoreBtn) {
    loadMoreBtn.style.pointerEvents = "none";
    const button = loadMoreBtn.querySelector("button");
    if (button) {
      button.textContent = "Carregando mais resultados...";
      button.classList.add("loading");
    }
  }

  try {
    currentSearch.page += 1;
    const response = await fetch(
      `/api/v1/albums/search?q=${encodeURIComponent(currentSearch.query)}&page=${currentSearch.page}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (loadMoreBtn) {
      loadMoreBtn.remove();
    }

    const albums = Array.isArray(data) ? data : data.albums;
    const pagination = data.pagination || {
      page: currentSearch.page,
      pages: currentSearch.page,
      total: albums.length,
    };

    if (albums && albums.length > 0) {
      albums.forEach((album) => results.appendChild(renderResultCard(album)));
      currentSearch.hasMore = pagination.page < pagination.pages;
      if (currentSearch.hasMore) {
        addLoadMoreButton();
      }
      return;
    }

    const noMoreDiv = document.createElement("div");
    noMoreDiv.className = "load-more";
    noMoreDiv.innerHTML = '<p class="muted">Não há mais resultados para mostrar.</p>';
    results.appendChild(noMoreDiv);
  } catch (error) {
    if (loadMoreBtn) {
      loadMoreBtn.innerHTML = `<p class="muted">Erro ao carregar mais resultados: ${error.message}</p>`;
    }
  }
}

function addLoadMoreButton() {
  const results = getResultsContainer();
  const loadMoreContainer = document.createElement("div");
  loadMoreContainer.className = "load-more";
  const loadMoreBtn = document.createElement("button");
  loadMoreBtn.textContent = "Mostrar mais 5 resultados";
  loadMoreContainer.appendChild(loadMoreBtn);
  loadMoreContainer.onclick = loadMoreResults;
  results.appendChild(loadMoreContainer);
}

document.addEventListener("DOMContentLoaded", () => {
  const searchForm = document.getElementById("search-form");
  const results = getResultsContainer();
  const slotSelect = document.querySelector("[name='storage_slot_id']");
  const positionInput = document.querySelector("[name='slot_position']");

  slotSelect.addEventListener("change", suggestSlotPosition);
  positionInput.addEventListener("input", () => {
    const suggested = positionInput.dataset.suggested || "";
    positionInput.dataset.manual = positionInput.value.trim() && positionInput.value.trim() !== suggested ? "true" : "";
  });
  void suggestSlotPosition();

  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = event.target.q.value.trim();
    if (!query) {
      results.innerHTML = '<p class="muted">Por favor, digite um termo para busca.</p>';
      return;
    }

    currentSearch = { query, page: 1, hasMore: false };
    results.innerHTML = "Buscando...";

    try {
      const response = await fetch(`/api/v1/albums/search?q=${encodeURIComponent(query)}&page=1`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      const albums = Array.isArray(payload) ? payload : payload.albums;
      const pagination = payload.pagination || { page: 1, pages: 1, total: albums.length };

      results.innerHTML = "";
      if (!albums || albums.length === 0) {
        results.innerHTML = '<p class="muted">Nenhum resultado encontrado.</p>';
        return;
      }

      albums.forEach((album) => results.appendChild(renderResultCard(album)));
      currentSearch.hasMore = pagination.page < pagination.pages;
      if (currentSearch.hasMore) {
        addLoadMoreButton();
      }
    } catch (error) {
      results.innerHTML = `<p class="muted">Erro ao buscar: ${error.message}</p>`;
    }
  });

  document.getElementById("add-track").addEventListener("click", () => addTrackRow());
  document.getElementById("manual-entry").addEventListener("click", openManualEditor);
  document.getElementById("cancel-edit").addEventListener("click", () => {
    selectedAlbum = null;
    document.getElementById("editor").classList.add("is-hidden");
  });

  document.getElementById("album-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = collectFormData();

    try {
      const response = await fetch("/api/v1/copies/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        const created = await response.json();
        window.location.href = `/copies/id/${created.id}`;
        return;
      }
      const error = await response.json().catch(() => ({}));
      alert(error.detail || "Erro ao salvar exemplar");
    } catch (error) {
      alert("Erro ao salvar exemplar");
    }
  });
});
