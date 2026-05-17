document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("catalog-search-input");
  const statusFilter = document.getElementById("catalog-status-filter");
  const filterToggle = document.getElementById("catalog-filter-toggle");
  const filterOptions = document.getElementById("catalog-filter-options");
  const filterOptionButtons = Array.from(document.querySelectorAll(".catalog-filter-option"));
  const cards = Array.from(document.querySelectorAll(".catalog-card"));
  const resultsInfo = document.getElementById("catalog-results-info");
  const emptyState = document.getElementById("catalog-empty-state");

  if (!searchInput || !statusFilter || !filterToggle || !filterOptions) {
    return;
  }

  const normalize = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();

  cards.forEach((card) => {
    card.dataset.searchNormalized = normalize(card.dataset.search);
  });

  const formatCount = (count) => {
    if (count === 1) {
      return "1 exemplar encontrado";
    }
    if (count > 1) {
      return `${count} exemplares encontrados`;
    }
    return "Nenhum exemplar encontrado";
  };

  const filterCatalog = () => {
    const query = normalize(searchInput.value);
    const status = statusFilter.value;
    let visibleCount = 0;

    cards.forEach((card) => {
      const matchesQuery = !query || card.dataset.searchNormalized.includes(query);
      const matchesStatus = !status || card.dataset.status === status;
      const isVisible = matchesQuery && matchesStatus;

      card.classList.toggle("is-hidden", !isVisible);
      if (isVisible) {
        visibleCount += 1;
      }
    });

    const hasActiveFilter = Boolean(query || status);
    resultsInfo.textContent = formatCount(visibleCount);
    resultsInfo.classList.toggle("is-hidden", !hasActiveFilter);
    emptyState.classList.toggle("is-hidden", visibleCount > 0);
  };

  const setFilterMenuOpen = (isOpen) => {
    filterOptions.hidden = !isOpen;
    filterToggle.setAttribute("aria-expanded", String(isOpen));
  };

  const selectStatusFilter = (button) => {
    const value = button.dataset.statusValue || "";
    const label = button.dataset.statusLabel || "Todos os status";
    statusFilter.value = value;
    filterOptionButtons.forEach((optionButton) => {
      const isSelected = optionButton === button;
      optionButton.classList.toggle("is-selected", isSelected);
      optionButton.setAttribute("aria-checked", String(isSelected));
    });
    filterToggle.classList.toggle("has-active-filter", Boolean(value));
    filterToggle.setAttribute("aria-label", `Filtrar por status${value ? `: ${label}` : ""}`);
    filterToggle.setAttribute("title", `Filtrar por status${value ? `: ${label}` : ""}`);
    setFilterMenuOpen(false);
    filterCatalog();
  };

  searchInput.addEventListener("input", filterCatalog);
  filterToggle.addEventListener("click", () => {
    setFilterMenuOpen(filterOptions.hidden);
  });
  filterOptionButtons.forEach((button) => {
    button.addEventListener("click", () => selectStatusFilter(button));
  });
  document.addEventListener("click", (event) => {
    if (!filterToggle.contains(event.target) && !filterOptions.contains(event.target)) {
      setFilterMenuOpen(false);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setFilterMenuOpen(false);
      filterToggle.focus();
    }
  });
  filterCatalog();
});
