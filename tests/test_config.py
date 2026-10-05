import pytest

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
    "ly_tu_trong": ("015", "015"),
    "pham_ngoc_thao": ("016", "016"),
    "vu_ngoc_nha": ("017", "017"),
    "dang_tran_duc": ("018", "018"),
    "pham_xuan_an": ("019", "019"),
    "le_huu_thuy": ("020", "020"),
    "hung_vuong": ("021", "021"),
    "an_duong_vuong": ("022", "022"),
    "hai_ba_trung": ("023", "023"),
    "ba_trieu": ("024", "024"),
    "ly_nam_de": ("025", "025"),
    "trieu_quang_phuc": ("026", "026"),
    "phung_hung": ("027", "027"),
    "mai_thuc_loan": ("028", "028"),
    "khuc_thua_du": ("029", "029"),
    "duong_dinh_nghe": ("030", "030"),
    "dinh_bo_linh": ("031", "031"),
    "le_hoan": ("032", "032"),
    "ly_thai_to": ("033", "033"),
    "ly_thuong_kiet": ("034", "034"),
    "tran_hung_dao": ("035", "035"),
    "nguyen_trai": ("036", "036"),
    "thanh_thien": ("037", "037"),
    "duong_van_nga": ("038", "038"),
    "y_lan": ("039", "039"),
    "tran_thi_dung": ("040", "040"),
    "ly_chieu_hoang": ("041", "041"),
    "an_tu": ("042", "042"),
    "huyen_tran": ("043", "043"),
    "nguyen_thi_anh": ("044", "044"),
    "nguyen_thi_due": ("045", "045"),
    "doan_thi_diem": ("046", "046"),
    "ho_xuan_huong": ("047", "047"),
}


def test_all_llm_characters_have_voice_and_lipsync_mapping() -> None:
    settings = Settings(_env_file=None)

    actual_mapping = {
        character.id: (character.voice_id, character.image_id)
        for character in settings.characters
    }

    assert actual_mapping == EXPECTED_CHARACTER_MAPPING
    assert len({character.voice_id for character in settings.characters}) == 47
    assert len({character.image_id for character in settings.characters}) == 47


def test_generic_character_override() -> None:
    settings = Settings(
        _env_file=None,
        character_overrides_json='{"ho_xuan_huong":{"voice_id":"custom-voice","image_id":"custom-image","image_path":"/tmp/portrait.jpg"}}',
    )
    character = settings.get_character("ho_xuan_huong")
    assert character.voice_id == "custom-voice"
    assert character.image_id == "custom-image"
    assert str(character.image_path) == "/tmp/portrait.jpg"


@pytest.mark.parametrize(
    "overrides",
    [
        '{"unknown":{"voice_id":"001"}}',
        '{"ho_xuan_huong":{"unsupported":"value"}}',
        '{"ho_xuan_huong":{"voice_id":""}}',
        "[]",
    ],
)
def test_invalid_overrides_are_rejected(overrides: str) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, character_overrides_json=overrides).characters


def test_character_mapping_can_be_overridden_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("LE_LOI_VOICE_ID", "voice-le-loi")
    monkeypatch.setenv("LE_LOI_IMAGE_ID", "portrait-le-loi")

    character = Settings().get_character("le_loi")

    assert character.voice_id == "voice-le-loi"
    assert character.image_id == "portrait-le-loi"


def test_llm_api_key_is_only_exposed_as_server_to_server_header() -> None:
    assert Settings(llm_api_key=None).llm_headers == {}
    assert Settings(llm_api_key="  application-secret  ").llm_headers == {
        "X-API-Key": "application-secret"
    }
