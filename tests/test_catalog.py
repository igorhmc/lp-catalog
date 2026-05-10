import httpx


def get_storage_slot_id(client, unit_code="K1", slot_code="B2"):
    response = client.get("/api/v1/copies/meta/storage")
    assert response.status_code == 200, response.text
    for unit in response.json():
        if unit["code"] != unit_code:
            continue
        for slot in unit["slots"]:
            if slot["slot_code"] == slot_code:
                return slot["id"]
    raise AssertionError(f"slot {unit_code}-{slot_code} not found")


def create_copy(client, title="Asa Branca em Vinil", artist="Trio Nordestino", slot_code="B2", slot_position="07"):
    response = client.post(
        "/api/v1/copies/",
        json={
            "title": title,
            "artist_name": artist,
            "year": 1982,
            "genre": "Forro",
            "country": "Brazil",
            "label_name": "CBS",
            "catalog_number": "138.123",
            "format": "LP",
            "discs_count": 1,
            "style": "Forró",
            "status": "catalogado",
            "media_condition": "VG+",
            "sleeve_condition": "VG",
            "storage_slot_id": get_storage_slot_id(client, "K1", slot_code),
            "slot_position": slot_position,
            "copy_notes": "Cópia revisada",
            "notes": "Primeira prensagem",
            "tracks": [
                {"disc_number": 1, "side": "A", "position": "A1", "title": "Asa Branca", "duration": "03:12"},
                {"disc_number": 1, "side": "A", "position": "A2", "title": "Baião", "duration": "02:58"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_copy_in_unit(client, unit_code="K1", title="Asa Branca em Vinil", artist="Trio Nordestino", slot_code="B2", slot_position="07"):
    response = client.post(
        "/api/v1/copies/",
        json={
            "title": title,
            "artist_name": artist,
            "year": 1982,
            "genre": "Forro",
            "country": "Brazil",
            "label_name": "CBS",
            "catalog_number": "138.123",
            "format": "LP",
            "discs_count": 1,
            "style": "Forró",
            "status": "catalogado",
            "media_condition": "VG+",
            "sleeve_condition": "VG",
            "storage_slot_id": get_storage_slot_id(client, unit_code, slot_code),
            "slot_position": slot_position,
            "copy_notes": "Cópia revisada",
            "notes": "Primeira prensagem",
            "tracks": [
                {"disc_number": 1, "side": "A", "position": "A1", "title": "Asa Branca", "duration": "03:12"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_copy_crud_flow(client):
    created = create_copy(client)
    copy_id = created["id"]

    detail_response = client.get(f"/api/v1/copies/id/{copy_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["album"]["title"] == "Asa Branca em Vinil"
    assert detail_payload["album"]["notes"] == "Primeira prensagem"
    assert detail_payload["location_code"] == "K1-B2-007"
    assert detail_payload["copy_code"].startswith("LP-")
    assert len(detail_payload["album"]["tracks"]) == 2

    update_response = client.put(
        f"/api/v1/copies/id/{copy_id}",
        json={
            "title": "Asa Branca Remaster",
            "artist_name": "Trio Nordestino",
            "year": 1984,
            "genre": "Forro",
            "country": "Brazil",
            "label_name": "CBS",
            "catalog_number": "138.123",
            "format": "LP",
            "discs_count": 1,
            "style": "Forró",
            "status": "guardado",
            "media_condition": "NM",
            "sleeve_condition": "VG+",
            "storage_slot_id": get_storage_slot_id(client, "K1", "B3"),
            "slot_position": "03",
            "copy_notes": "Cópia revisada",
            "notes": "Edicao revisada",
            "tracks": [
                {"disc_number": 1, "side": "B", "position": "B1", "title": "Xote das Meninas", "duration": "03:45"},
            ],
        },
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["album"]["title"] == "Asa Branca Remaster"

    detail_page = client.get(f"/copies/id/{copy_id}")
    assert detail_page.status_code == 200
    assert "Cópia revisada" in detail_page.text
    assert "K1-B3" in detail_page.text
    assert "Xote das Meninas" in detail_page.text

    delete_response = client.delete(f"/api/v1/copies/id/{copy_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/copies/id/{copy_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Copy not found"


def test_catalog_home_search_matches_artist_partial(client):
    create_copy(client, title="Noites do Sertão", artist="Quarteto Nordestino")

    home_response = client.get("/", params={"q": "Nordes"})
    assert home_response.status_code == 200
    assert "Noites do Sertão" in home_response.text
    assert "Quarteto Nordestino" in home_response.text


def test_catalog_home_search_matches_storage_location(client):
    create_copy(client, title="Forró de Nicho", artist="Mestre Lua")

    home_response = client.get("/", params={"q": "B2"})
    assert home_response.status_code == 200
    assert "Forró de Nicho" in home_response.text
    assert "K1-B2-007" in home_response.text


def test_catalog_home_search_matches_location_code(client):
    create_copy(client, title="Forró Codificado", artist="Mestre Lua")

    home_response = client.get("/", params={"q": "K1-B2-007"})
    assert home_response.status_code == 200
    assert "Forró Codificado" in home_response.text


def test_next_slot_position_suggests_first_gap_with_step_10(client):
    slot_id = get_storage_slot_id(client, "K1", "B2")

    first = client.get(f"/api/v1/copies/meta/storage/{slot_id}/next-position")
    assert first.status_code == 200
    assert first.json()["next_position"] == "010"

    create_copy(client, title="Forró Um", artist="Mestre Lua", slot_code="B2")

    second = client.get(f"/api/v1/copies/meta/storage/{slot_id}/next-position")
    assert second.status_code == 200
    assert second.json()["next_position"] == "010"
    assert "007" in second.json()["used_positions"]

    client.post(
        "/api/v1/copies/",
        json={
            "title": "Forró Dois",
            "artist_name": "Mestre Lua",
            "year": 1983,
            "genre": "Forro",
            "country": "Brazil",
            "label_name": "CBS",
            "catalog_number": "138.124",
            "format": "LP",
            "discs_count": 1,
            "style": "Forró",
            "status": "catalogado",
            "media_condition": "VG+",
            "sleeve_condition": "VG",
            "storage_slot_id": slot_id,
            "slot_position": "010",
            "copy_notes": "Segunda cópia",
            "notes": "Outra prensagem",
            "tracks": [
                {"disc_number": 1, "side": "A", "position": "A1", "title": "Faixa 1", "duration": "03:00"},
            ],
        },
    )

    third = client.get(f"/api/v1/copies/meta/storage/{slot_id}/next-position")
    assert third.status_code == 200
    assert third.json()["next_position"] == "020"


def test_pending_slot_ignores_individual_position(client):
    created = create_copy_in_unit(
        client,
        unit_code="K2",
        title="Fila de Triagem",
        artist="Artista Pendente",
        slot_code="B2",
        slot_position="030",
    )

    assert created["slot_position"] is None
    assert created["location_code"] == "K2-B2"

    slot_id = get_storage_slot_id(client, "K2", "B2")
    next_position = client.get(f"/api/v1/copies/meta/storage/{slot_id}/next-position")
    assert next_position.status_code == 200
    assert next_position.json()["uses_positions"] is False
    assert next_position.json()["next_position"] is None
    assert next_position.json()["used_positions"] == []


def test_normalize_slot_positions_rebalances_slot(client):
    slot_id = get_storage_slot_id(client, "K1", "B2")
    first = create_copy(client, title="B Disco", artist="Artista B", slot_code="B2", slot_position="030")
    second = create_copy(client, title="A Disco", artist="Artista A", slot_code="B2", slot_position="070")
    third = create_copy(client, title="C Disco", artist="Artista C", slot_code="B2", slot_position="090")

    response = client.post(f"/api/v1/copies/meta/storage/{slot_id}/normalize")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["normalized_count"] == 3
    assert payload["copies_in_slot"] == 3

    copy_a = client.get(f"/api/v1/copies/id/{second['id']}").json()
    copy_b = client.get(f"/api/v1/copies/id/{first['id']}").json()
    copy_c = client.get(f"/api/v1/copies/id/{third['id']}").json()

    assert copy_a["location_code"] == "K1-B2-010"
    assert copy_b["location_code"] == "K1-B2-020"
    assert copy_c["location_code"] == "K1-B2-030"


def test_storage_overview_reports_fill_and_positions(client):
    create_copy(client, title="Forró Visão 1", artist="Artista A", slot_code="B2", slot_position="010")
    create_copy(client, title="Forró Visão 2", artist="Artista B", slot_code="B2", slot_position="030")

    response = client.get("/api/v1/copies/meta/storage/overview")
    assert response.status_code == 200, response.text
    overview = response.json()
    k1 = next(item for item in overview if item["code"] == "K1")
    b2 = next(slot for slot in k1["slots"] if slot["slot_code"] == "B2")

    assert b2["occupied_count"] == 2
    assert b2["occupied_positions"] == ["010", "030"]
    assert b2["next_position"] == "020"
    assert b2["available_count"] == 58


def test_slot_contents_returns_copies_in_selected_slot(client):
    create_copy(client, title="Forró no Nicho", artist="Artista A", slot_code="B2", slot_position="010")
    create_copy(client, title="Outro Nicho", artist="Artista B", slot_code="A1", slot_position="010")
    slot_id = get_storage_slot_id(client, "K1", "B2")

    response = client.get(f"/api/v1/copies/meta/storage/{slot_id}/contents")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["storage_unit_code"] == "K1"
    assert payload["slot_code"] == "B2"
    assert payload["occupied_count"] == 1
    assert payload["copies"][0]["title"] == "Forró no Nicho"
    assert payload["copies"][0]["artist_name"] == "Artista A"
    assert payload["copies"][0]["slot_position"] == "010"


def test_home_renders_visual_storage_grid_and_versioned_assets(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "shelf-shell" in response.text
    assert "slot-position-grid" in response.text
    assert "slot-details-panel" in response.text
    assert "/static/styles.css?v=" in response.text
    assert "/static/js/home.js?v=" in response.text


def test_blank_discogs_query_returns_400(client):
    response = client.get("/api/v1/albums/search", params={"q": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "O termo de busca não pode estar vazio"


def test_edit_page_exposes_guided_mobile_capture(client):
    created = create_copy(client)
    response = client.get(f"/copies/id/{created['id']}/edit")
    assert response.status_code == 200
    assert "Captura guiada no celular" in response.text
    assert 'capture="environment"' in response.text
    assert "guided-camera-preview" in response.text


def test_discogs_errors_return_502(client, monkeypatch):
    async def failing_search(self, query: str, limit: int = 5, page: int = 1):
        raise httpx.ConnectError(
            "discogs down",
            request=httpx.Request("GET", "https://api.discogs.com/database/search"),
        )

    from services.discogs import DiscogsService

    monkeypatch.setattr(DiscogsService, "search_releases", failing_search)
    response = client.get("/api/v1/albums/search", params={"q": "forro"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Discogs request failed"
