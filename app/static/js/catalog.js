document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("catalog-search-input");
  const statusFilter = document.getElementById("catalog-status-filter");
  const cards = Array.from(document.querySelectorAll(".catalog-card"));
  const resultsInfo = document.getElementById("catalog-results-info");
  const emptyState = document.getElementById("catalog-empty-state");

  if (!searchInput || !statusFilter || !cards.length) {
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

  searchInput.addEventListener("input", filterCatalog);
  statusFilter.addEventListener("change", filterCatalog);
  filterCatalog();
});
