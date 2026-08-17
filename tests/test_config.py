from app.config import Settings


EXPECTED_CHARACTER_MAPPING = {
    "to_vinh_dien": ("001", "001"),
    "vo_thi_sau": ("002", "002"),
    "kim_dong": ("003", "003"),
    "le_van_tam": ("004", "004"),
    "nguyen_van_troi": ("005", "005"),
    "le_hong_phong": ("006", "006"),
    "nguyen_binh_khiem": ("007", "007"),
    "nguyen_ba_ngoc": ("008", "008"),
    "le_chan": ("009", "009"),
    "le_ngoc_han": ("010", "010"),
    "dinh_nup": ("011", "011"),
    "ngo_quyen": ("012", "012"),
    "quang_trung_nguyen_hue": ("013", "013"),
    "le_loi": ("014", "014"),
}


def test_all_llm_characters_have_voice_and_lipsync_mapping() -> None:
    settings = Settings()

    actual_mapping = {
        character.id: (character.voice_id, character.image_id)
        for character in settings.characters
    }

    assert actual_mapping == EXPECTED_CHARACTER_MAPPING
    assert len({character.voice_id for character in settings.characters}) == 14
    assert len({character.image_id for character in settings.characters}) == 14


def test_character_mapping_can_be_overridden_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("LE_LOI_VOICE_ID", "voice-le-loi")
    monkeypatch.setenv("LE_LOI_IMAGE_ID", "portrait-le-loi")

    character = Settings().get_character("le_loi")

    assert character.voice_id == "voice-le-loi"
    assert character.image_id == "portrait-le-loi"
