document.addEventListener("DOMContentLoaded", () => {
  const deleteButton = document.querySelector("[data-delete-copy]");
  if (!deleteButton) {
    return;
  }

  deleteButton.addEventListener("click", async () => {
    const copyId = deleteButton.dataset.deleteCopy;
    if (!window.confirm("Tem certeza que deseja excluir este exemplar? Esta ação não pode ser desfeita.")) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/copies/id/${copyId}`, { method: "DELETE" });
      if (response.ok) {
        window.location.href = "/";
        return;
      }
      const error = await response.json();
      alert(`Erro ao excluir o exemplar: ${error.detail}`);
    } catch (error) {
      alert("Erro ao excluir o exemplar");
    }
  });
});
