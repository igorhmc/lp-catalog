function bindTrackRowActions(container) {
  container.querySelector(".remove-track").onclick = (event) => {
    event.currentTarget.closest(".track-item").remove();
  };
}

const GUIDED_SQUARE_TYPES = new Set(["front", "back", "insert", "spine", "defect", "other"]);
const GUIDED_CIRCLE_TYPES = new Set(["label_a", "label_b", "runout_a", "runout_b"]);

let guidedCameraStream = null;
let guidedCaptureBlob = null;

function getGuidedMaskType(photoType) {
  if (GUIDED_CIRCLE_TYPES.has(photoType)) {
    return "circle";
  }
  return "square";
}

function updateGuidedMask() {
  const previewShell = document.getElementById("camera-preview-shell");
  const squareOverlay = document.querySelector(".camera-overlay-square");
  const circleOverlay = document.querySelector(".camera-overlay-circle");
  const photoType = document.getElementById("guided-photo-type")?.value || "front";
  const maskType = getGuidedMaskType(photoType);

  previewShell?.classList.toggle("mask-circle", maskType === "circle");
  previewShell?.classList.toggle("mask-square", maskType !== "circle");
  squareOverlay?.classList.toggle("is-hidden", maskType === "circle");
  circleOverlay?.classList.toggle("is-hidden", maskType !== "circle");
}

function setGuidedStatus(message) {
  const status = document.getElementById("guided-camera-status");
  if (status) {
    status.textContent = message;
  }
}

async function stopGuidedCamera() {
  if (guidedCameraStream) {
    guidedCameraStream.getTracks().forEach((track) => track.stop());
    guidedCameraStream = null;
  }
}

async function startGuidedCamera() {
  const video = document.getElementById("guided-camera-preview");
  const captureButton = document.getElementById("capture-guided-photo");
  const uploadButton = document.getElementById("upload-guided-photo");
  const canvas = document.getElementById("guided-camera-canvas");

  if (!navigator.mediaDevices?.getUserMedia) {
    setGuidedStatus("Este navegador não suporta câmera guiada. Use o envio normal abaixo.");
    return;
  }

  await stopGuidedCamera();
  guidedCaptureBlob = null;
  uploadButton.disabled = true;
  canvas.classList.add("is-hidden");
  video.classList.remove("is-hidden");

  try {
    guidedCameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1920 },
      },
      audio: false,
    });
    video.srcObject = guidedCameraStream;
    await video.play();
    captureButton.disabled = false;
    setGuidedStatus("Câmera pronta. Enquadre o disco na máscara e toque em Capturar.");
  } catch (error) {
    captureButton.disabled = true;
    setGuidedStatus("Não foi possível abrir a câmera. Verifique a permissão do navegador ou use o envio normal.");
  }
}

function captureGuidedPhoto() {
  const video = document.getElementById("guided-camera-preview");
  const canvas = document.getElementById("guided-camera-canvas");
  const uploadButton = document.getElementById("upload-guided-photo");
  const captureButton = document.getElementById("capture-guided-photo");

  if (!video.videoWidth || !video.videoHeight) {
    setGuidedStatus("A câmera ainda não está pronta.");
    return;
  }

  const cropSize = Math.min(video.videoWidth, video.videoHeight);
  const sourceX = Math.floor((video.videoWidth - cropSize) / 2);
  const sourceY = Math.floor((video.videoHeight - cropSize) / 2);

  canvas.width = cropSize;
  canvas.height = cropSize;

  const context = canvas.getContext("2d");
  context.drawImage(video, sourceX, sourceY, cropSize, cropSize, 0, 0, cropSize, cropSize);

  canvas.classList.remove("is-hidden");
  video.classList.add("is-hidden");
  captureButton.disabled = false;

  canvas.toBlob((blob) => {
    guidedCaptureBlob = blob;
    uploadButton.disabled = !blob;
    setGuidedStatus(blob ? "Captura pronta para envio." : "Falha ao gerar a captura.");
  }, "image/jpeg", 0.92);
}

async function uploadGuidedPhoto(copyId) {
  const photoType = document.getElementById("guided-photo-type").value;
  const isPrimary = document.getElementById("guided-is-primary").checked;

  if (!guidedCaptureBlob) {
    setGuidedStatus("Capture uma imagem antes de enviar.");
    return;
  }

  const data = new FormData();
  data.append("photo_type", photoType);
  data.append("is_primary", isPrimary ? "true" : "false");
  data.append("photos", guidedCaptureBlob, `${photoType}-${Date.now()}.jpg`);

  const response = await fetch(`/api/v1/copies/id/${copyId}/photos`, {
    method: "POST",
    body: data,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Erro ao enviar captura guiada");
  }
}

function addTrack() {
  const tpl = document.getElementById("track-template");
  const node = tpl.content.cloneNode(true);
  const row = node.querySelector(".track-item");
  bindTrackRowActions(row);
  document.getElementById("tracks-list").appendChild(node);
}

function collectTracks() {
  return Array.from(document.querySelectorAll(".track-item"))
    .map((track) => {
      const discNumberRaw = track.querySelector("[name='track_disc_number']").value;
      return {
        disc_number: discNumberRaw ? Number.parseInt(discNumberRaw, 10) : null,
        side: track.querySelector("[name='track_side']").value.trim() || null,
        position: track.querySelector("[name='track_position']").value.trim(),
        title: track.querySelector("[name='track_title']").value.trim(),
        duration: track.querySelector("[name='track_duration']").value.trim() || "00:00",
      };
    })
    .filter((track) => track.position && track.title);
}

function buildPayload() {
  const slotId = Number.parseInt(document.getElementById("storage_slot_id").value, 10);
  const discogsId = Number.parseInt(document.getElementById("discogs_id").value, 10);
  const rpm = Number.parseInt(document.getElementById("rpm").value, 10);
  const discsCount = Number.parseInt(document.getElementById("discs_count").value, 10);
  const purchasePrice = document.getElementById("purchase_price").value
    ? Number.parseFloat(document.getElementById("purchase_price").value)
    : null;

  return {
    title: document.getElementById("title").value.trim(),
    artist_name: document.getElementById("artist_name").value.trim(),
    year: document.getElementById("year").value
      ? Number.parseInt(document.getElementById("year").value, 10)
      : null,
    genre: document.getElementById("genre").value.trim() || null,
    country: document.getElementById("country").value.trim() || null,
    label_name: document.getElementById("label_name").value.trim() || null,
    catalog_number: document.getElementById("catalog_number").value.trim() || null,
    barcode: document.getElementById("barcode").value.trim() || null,
    format: document.getElementById("format").value.trim() || null,
    rpm: Number.isFinite(rpm) ? rpm : null,
    discs_count: Number.isFinite(discsCount) ? discsCount : null,
    style: document.getElementById("style").value.trim() || null,
    discogs_id: Number.isFinite(discogsId) ? discogsId : null,
    cover_path: document.getElementById("cover_path").value || null,
    cover_url: document.getElementById("cover_url").value || null,
    notes: document.getElementById("notes").value.trim() || null,
    status: document.getElementById("status").value,
    media_condition: document.getElementById("media_condition").value || null,
    sleeve_condition: document.getElementById("sleeve_condition").value || null,
    has_insert: document.getElementById("has_insert").checked,
    has_obi: document.getElementById("has_obi").checked,
    purchase_date: document.getElementById("purchase_date").value || null,
    purchase_price: purchasePrice,
    purchase_from: document.getElementById("purchase_from").value.trim() || null,
    copy_notes: document.getElementById("copy_notes").value.trim() || null,
    storage_slot_id: Number.isFinite(slotId) ? slotId : null,
    slot_position: document.getElementById("slot_position").value.trim() || null,
    tracks: collectTracks(),
  };
}

async function suggestSlotPosition() {
  const slotSelect = document.getElementById("storage_slot_id");
  const positionInput = document.getElementById("slot_position");
  const helpText = document.getElementById("slot-position-help");
  const form = document.getElementById("editForm");
  const slotId = Number.parseInt(slotSelect.value, 10);

  if (!Number.isFinite(slotId)) {
    positionInput.disabled = false;
    positionInput.placeholder = "Ex.: 010";
    if (helpText) {
      helpText.textContent = "Para nichos de triagem/pending, a posicao individual nao e usada.";
    }
    return;
  }

  const params = new URLSearchParams({ exclude_copy_id: form.dataset.copyId });

  try {
    const response = await fetch(`/api/v1/copies/meta/storage/${slotId}/next-position?${params.toString()}`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    if (!payload.uses_positions) {
      positionInput.value = "";
      positionInput.dataset.suggested = "";
      positionInput.dataset.manual = "";
      positionInput.disabled = true;
      positionInput.placeholder = "Nao se aplica";
      if (helpText) {
        helpText.textContent = "Este nicho e de triagem/pending. O sistema guarda apenas a quantidade de discos ali.";
      }
      return;
    }
    positionInput.disabled = false;
    positionInput.placeholder = "Ex.: 010";
    if (helpText) {
      helpText.textContent = "Para nichos de triagem/pending, a posicao individual nao e usada.";
    }
    if (!positionInput.dataset.manual || !positionInput.value.trim()) {
      positionInput.value = payload.next_position || "";
      positionInput.dataset.suggested = payload.next_position || "";
      positionInput.dataset.manual = "";
    }
  } catch (_) {
    // mantem valor manual atual
  }
}

async function uploadPhotos(copyId, form) {
  const data = new FormData(form);
  const response = await fetch(`/api/v1/copies/id/${copyId}/photos`, {
    method: "POST",
    body: data,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Erro ao enviar fotos");
  }
}

async function deletePhoto(copyId, photoId) {
  const response = await fetch(`/api/v1/copies/id/${copyId}/photos/${photoId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Erro ao excluir foto");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".track-item").forEach(bindTrackRowActions);
  document.getElementById("add-track").addEventListener("click", addTrack);
  const slotSelect = document.getElementById("storage_slot_id");
  const positionInput = document.getElementById("slot_position");
  const guidedTypeSelect = document.getElementById("guided-photo-type");
  const startGuidedCameraButton = document.getElementById("start-guided-camera");
  const captureGuidedPhotoButton = document.getElementById("capture-guided-photo");
  const uploadGuidedPhotoButton = document.getElementById("upload-guided-photo");
  const editForm = document.getElementById("editForm");

  slotSelect.addEventListener("change", suggestSlotPosition);
  positionInput.addEventListener("input", () => {
    const suggested = positionInput.dataset.suggested || "";
    positionInput.dataset.manual = positionInput.value.trim() && positionInput.value.trim() !== suggested ? "true" : "";
  });
  void suggestSlotPosition();
  updateGuidedMask();
  guidedTypeSelect?.addEventListener("change", updateGuidedMask);
  startGuidedCameraButton?.addEventListener("click", () => {
    void startGuidedCamera();
  });
  captureGuidedPhotoButton?.addEventListener("click", captureGuidedPhoto);
  uploadGuidedPhotoButton?.addEventListener("click", async () => {
    try {
      uploadGuidedPhotoButton.disabled = true;
      await uploadGuidedPhoto(editForm.dataset.copyId);
      setGuidedStatus("Foto enviada. Recarregando a galeria...");
      window.location.reload();
    } catch (error) {
      uploadGuidedPhotoButton.disabled = false;
      setGuidedStatus(error.message);
    }
  });

  editForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const copyId = form.dataset.copyId;

    try {
      const response = await fetch(`/api/v1/copies/id/${copyId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });

      if (response.ok) {
        window.location.href = `/copies/id/${copyId}`;
        return;
      }

      const error = await response.json().catch(() => ({}));
      alert(`Erro ao salvar: ${error.detail || "Erro desconhecido"}`);
    } catch (error) {
      alert(`Erro ao salvar: ${error.message}`);
    }
  });

  const uploadForm = document.getElementById("photo-upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const copyId = uploadForm.dataset.copyId;
      try {
        await uploadPhotos(copyId, uploadForm);
        window.location.reload();
      } catch (error) {
        alert(error.message);
      }
    });
  }

  document.querySelectorAll("[data-delete-photo]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("Excluir esta foto?")) {
        return;
      }
      try {
        await deletePhoto(button.dataset.copyId, button.dataset.deletePhoto);
        window.location.reload();
      } catch (error) {
        alert(error.message);
      }
    });
  });

  window.addEventListener("beforeunload", () => {
    void stopGuidedCamera();
  });
});
