document.addEventListener("DOMContentLoaded", () => {
  const usageStatusOptions = [
    ["disponivel", "Disponível"],
    ["emprestado", "Emprestado"],
    ["reservado", "Reservado"],
    ["indisponivel", "Indisponível"],
  ];
  const physicalStatusOptions = [
    ["no_lugar", "No lugar"],
    ["a_guardar", "A guardar"],
    ["triagem", "Triagem"],
    ["fora_do_lugar", "Fora do lugar"],
    ["sem_posicao", "Sem posição"],
  ];
  const form = document.getElementById("normalize-slot-form");
  const slotCards = Array.from(document.querySelectorAll(".slot-cube-action[data-slot-id]"));
  const detailsPanel = document.getElementById("slot-details-panel");
  const detailsTitle = document.getElementById("slot-details-title");
  const detailsSubtitle = document.getElementById("slot-details-subtitle");
  const detailsMeta = document.getElementById("slot-details-meta");
  const detailsBody = document.getElementById("slot-details-body");
  const closeButton = document.getElementById("slot-details-close");

  const renderStatusSelect = (copy, field, options) => `
    <label>
      <span>${field === "usage_status" ? "Uso" : "Organização"}</span>
      <select class="copy-status-select" data-copy-status-field="${field}" data-copy-id="${copy.id}">
        ${options
          .map(
            ([value, label]) => `<option value="${value}" ${copy[field] === value ? "selected" : ""}>${label}</option>`
          )
          .join("")}
      </select>
    </label>
  `;

  const renderSlotContents = (payload) => {
    detailsTitle.textContent = `${payload.storage_unit_code}-${payload.slot_code}`;
    detailsSubtitle.textContent = payload.purpose || "Sem finalidade definida";
    detailsMeta.innerHTML = `
      <span class="pill pill-soft">${payload.occupied_count} cadastrados</span>
      ${payload.uses_positions ? `<span class="pill pill-soft">Próxima: ${payload.next_position}</span>` : `<span class="pill pill-soft">Sem posição individual</span>`}
      ${payload.capacity_estimate ? `<span class="pill pill-soft">Capacidade: ${payload.capacity_estimate}</span>` : ""}
    `;

    if (!payload.copies.length) {
      detailsBody.innerHTML = '<p class="muted">Nenhum disco cadastrado neste nicho ainda.</p>';
      return;
    }

    detailsBody.innerHTML = `
      <div class="slot-copy-list">
        ${payload.copies
          .map(
            (copy) => `
              <article class="slot-copy-item">
                <a class="slot-copy-link" href="/copies/id/${copy.id}">
                  <div class="slot-copy-main">
                    <strong>${payload.uses_positions ? (copy.slot_position || "--") : "•"}</strong>
                    <div>
                      <div class="slot-copy-title">${copy.title}</div>
                      <div class="sub">${copy.artist_name}${copy.year ? ` · ${copy.year}` : ""}</div>
                    </div>
                  </div>
                  <div class="slot-copy-side">
                    <span class="pill">${copy.copy_code || "Sem código"}</span>
                  </div>
                </a>
                <div class="slot-status-controls">
                  ${renderStatusSelect(copy, "usage_status", usageStatusOptions)}
                  ${renderStatusSelect(copy, "physical_status", physicalStatusOptions)}
                </div>
              </article>
            `
          )
          .join("")}
      </div>
    `;
  };

  const updateCopyStatus = async (select) => {
    const copyId = Number.parseInt(select.dataset.copyId, 10);
    const field = select.dataset.copyStatusField;
    if (!Number.isFinite(copyId) || !field) {
      return;
    }

    select.disabled = true;
    try {
      const response = await fetch(`/api/v1/copies/id/${copyId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: select.value }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Erro ao atualizar status");
      }
      window.location.reload();
    } catch (error) {
      alert(error.message);
      select.disabled = false;
    }
  };

  const setSelectedCard = (activeCard) => {
    slotCards.forEach((card) => {
      card.classList.toggle("slot-cube-selected", card === activeCard);
    });
  };

  const openSlotDetails = async (card) => {
    const slotId = Number.parseInt(card.dataset.slotId, 10);
    if (!Number.isFinite(slotId) || !detailsPanel) {
      return;
    }

    setSelectedCard(card);
    detailsPanel.classList.remove("is-hidden");
    detailsTitle.textContent = card.dataset.slotLabel || "Nicho";
    detailsSubtitle.textContent = card.dataset.slotPurpose || "Carregando...";
    detailsMeta.innerHTML = "";
    detailsBody.innerHTML = '<p class="muted">Carregando conteúdo do nicho...</p>';

    try {
      const response = await fetch(`/api/v1/copies/meta/storage/${slotId}/contents`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Erro ao carregar o nicho");
      }
      renderSlotContents(payload);
      detailsPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      detailsBody.innerHTML = `<p class="muted">${error.message}</p>`;
    }
  };

  slotCards.forEach((card) => {
    card.addEventListener("click", () => {
      void openSlotDetails(card);
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        void openSlotDetails(card);
      }
    });
  });

  closeButton?.addEventListener("click", () => {
    detailsPanel?.classList.add("is-hidden");
    setSelectedCard(null);
  });

  detailsBody?.addEventListener("change", (event) => {
    const select = event.target.closest(".copy-status-select");
    if (!select) {
      return;
    }
    void updateCopyStatus(select);
  });

  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const slotId = Number.parseInt(form.slot_id.value, 10);
    if (!Number.isFinite(slotId)) {
      alert("Escolha um nicho.");
      return;
    }

    if (!window.confirm("Normalizar as posições deste nicho?")) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/copies/meta/storage/${slotId}/normalize`, {
        method: "POST",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Erro ao normalizar nicho");
      }

      alert(
        payload.message
          ? payload.message
          : payload.normalized_count > 0
          ? `Nicho ${payload.storage_unit_code}-${payload.slot_code} normalizado. ${payload.normalized_count} posições atualizadas.`
          : `Nicho ${payload.storage_unit_code}-${payload.slot_code} já estava normalizado.`
      );
      window.location.reload();
    } catch (error) {
      alert(error.message);
    }
  });
});
