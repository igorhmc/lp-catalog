from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from core.config import get_settings
from models.copy import Copy, CopyPhoto


class PhotoAnalysisUnavailable(RuntimeError):
    pass


class PhotoAnalysisService:
    endpoint = "https://api.openai.com/v1/responses"

    async def analyze_copy(self, copy: Copy) -> list[dict[str, Any]]:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise PhotoAnalysisUnavailable("Configure OPENAI_API_KEY para usar a análise automática de fotos.")

        photos = self._select_photos(copy.photos)
        if not photos:
            return []

        content: list[dict[str, Any]] = [{"type": "input_text", "text": self._build_prompt(copy, photos)}]
        for photo in photos:
            image_url = self._photo_data_url(photo, settings.COVERS_DIR)
            content.append({"type": "input_image", "image_url": image_url, "detail": "high"})

        payload = {
            "model": settings.OPENAI_PHOTO_ANALYSIS_MODEL,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "lp_photo_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "suggestions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "field_name": {"type": "string"},
                                        "suggested_value": {"type": "string"},
                                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                                        "rationale": {"type": "string"},
                                        "source_photo_ids": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                        },
                                    },
                                    "required": [
                                        "field_name",
                                        "suggested_value",
                                        "confidence",
                                        "rationale",
                                        "source_photo_ids",
                                    ],
                                },
                            }
                        },
                        "required": ["suggestions"],
                    },
                }
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code >= 400:
            raise PhotoAnalysisUnavailable(f"Falha na análise automática: {response.text[:300]}")

        data = response.json()
        output_text = data.get("output_text") or self._extract_output_text(data)
        try:
            parsed = json.loads(output_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise PhotoAnalysisUnavailable("A análise retornou um formato inválido.") from exc

        suggestions = parsed.get("suggestions")
        if not isinstance(suggestions, list):
            return []
        return [item for item in suggestions if isinstance(item, dict)]

    def _select_photos(self, photos: list[CopyPhoto]) -> list[CopyPhoto]:
        priority = {
            "front": 0,
            "back": 1,
            "label_a": 2,
            "label_b": 3,
            "runout_a": 4,
            "runout_b": 5,
            "insert": 6,
            "spine": 7,
            "defect": 8,
            "other": 9,
        }
        return sorted(photos, key=lambda item: (priority.get(item.photo_type, 99), item.id))[:8]

    def _photo_data_url(self, photo: CopyPhoto, covers_dir: str) -> str:
        file_path = Path(photo.file_path)
        absolute_path = file_path if file_path.is_absolute() else Path(covers_dir).parent / file_path
        if not absolute_path.exists():
            raise PhotoAnalysisUnavailable(f"Arquivo de foto não encontrado: {photo.file_path}")

        mime_type = mimetypes.guess_type(str(absolute_path))[0] or "image/jpeg"
        encoded = base64.b64encode(absolute_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _build_prompt(self, copy: Copy, photos: list[CopyPhoto]) -> str:
        album = copy.album
        artist = album.artist
        tracks = [
            {
                "disc_number": track.disc_number,
                "side": track.side,
                "position": track.position,
                "title": track.title,
                "duration": track.duration,
            }
            for track in album.tracks
        ]
        photo_refs = [
            {"id": photo.id, "type": photo.photo_type, "file_path": photo.file_path}
            for photo in photos
        ]
        current = {
            "artist.name": artist.name if artist else None,
            "album.title": album.title,
            "album.year": album.year,
            "album.country": album.country,
            "album.label_name": album.label_name,
            "album.catalog_number": album.catalog_number,
            "album.barcode": album.barcode,
            "album.format": album.format,
            "album.rpm": album.rpm,
            "album.discs_count": album.discs_count,
            "album.style": album.style,
            "album.notes": album.notes,
            "copy.media_condition": copy.media_condition,
            "copy.sleeve_condition": copy.sleeve_condition,
            "copy.has_insert": copy.has_insert,
            "copy.has_obi": copy.has_obi,
            "copy.notes": copy.notes,
            "tracks": tracks,
            "photos": photo_refs,
        }
        allowed_fields = [
            "artist.name",
            "album.title",
            "album.year",
            "album.country",
            "album.label_name",
            "album.catalog_number",
            "album.barcode",
            "album.format",
            "album.rpm",
            "album.discs_count",
            "album.style",
            "album.notes",
            "copy.media_condition",
            "copy.sleeve_condition",
            "copy.has_insert",
            "copy.has_obi",
            "copy.notes",
        ]
        return (
            "Analise fotos de um disco de vinil e sugira apenas correções ou dados adicionais "
            "que estejam visíveis nas imagens. Não invente dados. Não sugira algo se a foto não "
            "estiver clara. Use português no rationale. Responda somente no JSON schema pedido. "
            "Cada sugestão deve usar um field_name desta lista: "
            f"{', '.join(allowed_fields)}. "
            "Para condições, use valores como M, NM, VG+, VG, G ou P apenas quando houver base visual. "
            "Para booleanos, use true ou false como texto. Dados atuais:\n"
            f"{json.dumps(current, ensure_ascii=False)}"
        )

    def _extract_output_text(self, data: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    chunks.append(content["text"])
        return "\n".join(chunks)
