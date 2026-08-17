from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """Mapping một nhân vật tới đúng LLM, giọng TTS và ảnh LipSync."""

    id: str
    display_name: str
    self_pronoun: str
    student_pronoun: str
    short_description: str
    title: str
    life_years: str
    era_label: str
    quote: str
    greeting: str
    voice_id: str
    image_id: str
    image_path: Path


class Settings(BaseSettings):
    """Cấu hình adapter giữa orchestrator và ba API độc lập."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "digital-hero-orchestrator"
    app_host: str = "0.0.0.0"
    app_port: int = 8991
    log_level: str = "INFO"

    llm_base_url: str = "http://127.0.0.1:8005"
    llm_ws_base_url: str = "ws://127.0.0.1:8005"
    tts_base_url: str = "http://127.0.0.1:8989"
    lipsync_base_url: str = "http://127.0.0.1:8990"

    character_id: str = "to_vinh_dien"
    voice_id: str = "001"
    image_id: str = "001"
    vo_thi_sau_voice_id: str = "002"
    vo_thi_sau_image_id: str = "002"
    kim_dong_voice_id: str = "003"
    kim_dong_image_id: str = "003"
    le_van_tam_voice_id: str = "004"
    le_van_tam_image_id: str = "004"
    nguyen_van_troi_voice_id: str = "005"
    nguyen_van_troi_image_id: str = "005"
    le_hong_phong_voice_id: str = "006"
    le_hong_phong_image_id: str = "006"
    nguyen_binh_khiem_voice_id: str = "007"
    nguyen_binh_khiem_image_id: str = "007"
    nguyen_ba_ngoc_voice_id: str = "008"
    nguyen_ba_ngoc_image_id: str = "008"
    le_chan_voice_id: str = "009"
    le_chan_image_id: str = "009"
    le_ngoc_han_voice_id: str = "010"
    le_ngoc_han_image_id: str = "010"
    dinh_nup_voice_id: str = "011"
    dinh_nup_image_id: str = "011"
    ngo_quyen_voice_id: str = "012"
    ngo_quyen_image_id: str = "012"
    quang_trung_nguyen_hue_voice_id: str = "013"
    quang_trung_nguyen_hue_image_id: str = "013"
    le_loi_voice_id: str = "014"
    le_loi_image_id: str = "014"

    llm_timeout_seconds: float = 45.0
    tts_timeout_seconds: float = 900.0
    lipsync_timeout_seconds: float = 3600.0
    video_download_timeout_seconds: float = 300.0
    poll_interval_seconds: float = Field(default=2.0, ge=0.1)
    voice_connect_timeout_seconds: float = 15.0

    storage_dir: Path = PROJECT_ROOT / "storage"
    frontend_dist_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    character_image_path: Path = PROJECT_ROOT / "assets" / "001.svg"
    vo_thi_sau_image_path: Path = PROJECT_ROOT / "assets" / "002.svg"
    kim_dong_image_path: Path = PROJECT_ROOT / "assets" / "003.svg"
    le_van_tam_image_path: Path = PROJECT_ROOT / "assets" / "004.svg"
    nguyen_van_troi_image_path: Path = PROJECT_ROOT / "assets" / "005.svg"
    le_hong_phong_image_path: Path = PROJECT_ROOT / "assets" / "006.svg"
    nguyen_binh_khiem_image_path: Path = PROJECT_ROOT / "assets" / "007.svg"
    nguyen_ba_ngoc_image_path: Path = PROJECT_ROOT / "assets" / "008.svg"
    le_chan_image_path: Path = PROJECT_ROOT / "assets" / "009.svg"
    le_ngoc_han_image_path: Path = PROJECT_ROOT / "assets" / "010.svg"
    dinh_nup_image_path: Path = PROJECT_ROOT / "assets" / "011.svg"
    ngo_quyen_image_path: Path = PROJECT_ROOT / "assets" / "012.svg"
    quang_trung_nguyen_hue_image_path: Path = PROJECT_ROOT / "assets" / "013.svg"
    le_loi_image_path: Path = PROJECT_ROOT / "assets" / "014.svg"

    @property
    def characters(self) -> tuple[CharacterConfig, ...]:
        """Danh sách nhân vật public của orchestrator.

        Ba ID kỹ thuật phải luôn đi cùng nhau:
        character id của LLM, voice id của TTS và image id của LipSync.
        """

        return (
            CharacterConfig(
                id="to_vinh_dien",
                display_name="Tô Vĩnh Diện",
                self_pronoun="chú",
                student_pronoun="cháu",
                short_description="Anh hùng pháo binh trong Chiến dịch Điện Biên Phủ.",
                title="ANH HÙNG LIỆT SĨ",
                life_years="1924 — 1954",
                era_label="ĐIỆN BIÊN PHỦ · 1954",
                quote="Thà hy sinh, quyết bảo vệ pháo",
                greeting=(
                    "Chào cháu. Chú là Tô Vĩnh Diện. "
                    "Cháu muốn cùng chú tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.voice_id,
                image_id=self.image_id,
                image_path=self.character_image_path,
            ),
            CharacterConfig(
                id="vo_thi_sau",
                display_name="Võ Thị Sáu",
                self_pronoun="chị",
                student_pronoun="em",
                short_description="Người con gái Đất Đỏ kiên cường trong kháng chiến chống Pháp.",
                title="NỮ ANH HÙNG LIỆT SĨ",
                life_years="1933 — 1952",
                era_label="ĐẤT ĐỎ · CÔN ĐẢO",
                quote="Tinh thần kiên định, không khuất phục",
                greeting=(
                    "Chào em. Chị là Võ Thị Sáu. "
                    "Em muốn cùng chị tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.vo_thi_sau_voice_id,
                image_id=self.vo_thi_sau_image_id,
                image_path=self.vo_thi_sau_image_path,
            ),
            CharacterConfig(
                id="kim_dong",
                display_name="Kim Đồng",
                self_pronoun="anh",
                student_pronoun="em",
                short_description=(
                    "Người đội trưởng đầu tiên của Đội Nhi đồng cứu quốc, "
                    "tên thật là Nông Văn Dền."
                ),
                title="ANH HÙNG LIỆT SĨ",
                life_years="1929 — 1943",
                era_label="CAO BẰNG · 1943",
                quote="Trong sáng, nhanh trí và dũng cảm",
                greeting=(
                    "Chào em. Anh là Kim Đồng. "
                    "Em muốn cùng anh tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.kim_dong_voice_id,
                image_id=self.kim_dong_image_id,
                image_path=self.kim_dong_image_path,
            ),
            CharacterConfig(
                id="le_van_tam",
                display_name="Lê Văn Tám",
                self_pronoun="anh",
                student_pronoun="em",
                short_description=(
                    "Nhân vật AI giáo dục giới thiệu hình tượng Lê Văn Tám và "
                    "tranh luận sử học về tính xác thực của câu chuyện."
                ),
                title="BIỂU TƯỢNG THIẾU NIÊN",
                life_years="GIAI ĐOẠN 1945",
                era_label="THỊ NGHÈ · 1945",
                quote="Tìm hiểu lịch sử với thái độ trung thực",
                greeting=(
                    "Chào em. Anh là nhân vật Lê Văn Tám. "
                    "Em muốn cùng anh tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.le_van_tam_voice_id,
                image_id=self.le_van_tam_image_id,
                image_path=self.le_van_tam_image_path,
            ),
            CharacterConfig(
                id="nguyen_van_troi",
                display_name="Nguyễn Văn Trỗi",
                self_pronoun="anh",
                student_pronoun="em",
                short_description="Người chiến sĩ biệt động Sài Gòn kiên trung.",
                title="ANH HÙNG LIỆT SĨ",
                life_years="1940 — 1964",
                era_label="SÀI GÒN · 1964",
                quote="Điềm tĩnh, chân thành và kiên định",
                greeting=(
                    "Chào em. Anh là Nguyễn Văn Trỗi. "
                    "Em muốn cùng anh tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.nguyen_van_troi_voice_id,
                image_id=self.nguyen_van_troi_image_id,
                image_path=self.nguyen_van_troi_image_path,
            ),
            CharacterConfig(
                id="le_hong_phong",
                display_name="Lê Hồng Phong",
                self_pronoun="anh",
                student_pronoun="em",
                short_description=(
                    "Nhà hoạt động cách mạng, người góp phần khôi phục tổ chức "
                    "Đảng đầu thập niên 1930."
                ),
                title="NHÀ HOẠT ĐỘNG CÁCH MẠNG",
                life_years="1902 — 1942",
                era_label="CÁCH MẠNG VIỆT NAM",
                quote="Học tập, tổ chức và kiên định",
                greeting=(
                    "Chào em. Anh là Lê Hồng Phong. "
                    "Em muốn cùng anh tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.le_hong_phong_voice_id,
                image_id=self.le_hong_phong_image_id,
                image_path=self.le_hong_phong_image_path,
            ),
            CharacterConfig(
                id="nguyen_binh_khiem",
                display_name="Nguyễn Bỉnh Khiêm",
                self_pronoun="thầy",
                student_pronoun="con",
                short_description="Nhà giáo, nhà thơ và nhà tư tưởng lớn của thế kỷ XVI.",
                title="TRẠNG TRÌNH",
                life_years="1491 — 1585",
                era_label="ĐẠI VIỆT · THẾ KỶ XVI",
                quote="Trọng đạo học và lòng dân",
                greeting=(
                    "Chào con. Thầy là Nguyễn Bỉnh Khiêm. "
                    "Con muốn cùng thầy tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.nguyen_binh_khiem_voice_id,
                image_id=self.nguyen_binh_khiem_image_id,
                image_path=self.nguyen_binh_khiem_image_path,
            ),
            CharacterConfig(
                id="nguyen_ba_ngoc",
                display_name="Nguyễn Bá Ngọc",
                self_pronoun="anh",
                student_pronoun="em",
                short_description=(
                    "Thiếu niên dũng cảm đã cứu hai em nhỏ trong trận bom "
                    "tại Quảng Xương năm 1965."
                ),
                title="ANH HÙNG LIỆT SĨ",
                life_years="1952 — 1965",
                era_label="THANH HÓA · 1965",
                quote="Ấm áp, khiêm nhường và dũng cảm",
                greeting=(
                    "Chào em. Anh là Nguyễn Bá Ngọc. "
                    "Em muốn cùng anh tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.nguyen_ba_ngoc_voice_id,
                image_id=self.nguyen_ba_ngoc_image_id,
                image_path=self.nguyen_ba_ngoc_image_path,
            ),
            CharacterConfig(
                id="le_chan",
                display_name="Nữ tướng Lê Chân",
                self_pronoun="chị",
                student_pronoun="em",
                short_description=(
                    "Nữ tướng của Hai Bà Trưng, gắn với vùng An Biên xưa "
                    "của Hải Phòng."
                ),
                title="NỮ TƯỚNG",
                life_years="THẾ KỶ I",
                era_label="AN BIÊN · KHỞI NGHĨA HAI BÀ TRƯNG",
                quote="Mạnh mẽ, nhân hậu và thận trọng với sử liệu",
                greeting=(
                    "Chào em. Chị là Lê Chân. "
                    "Em muốn cùng chị tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.le_chan_voice_id,
                image_id=self.le_chan_image_id,
                image_path=self.le_chan_image_path,
            ),
            CharacterConfig(
                id="le_ngoc_han",
                display_name="Công chúa Lê Ngọc Hân",
                self_pronoun="chị",
                student_pronoun="em",
                short_description=(
                    "Bắc Cung Hoàng hậu và tác giả văn học chữ Nôm được ghi nhận "
                    "trong truyền thống sử học."
                ),
                title="CÔNG CHÚA · BẮC CUNG HOÀNG HẬU",
                life_years="1770 — 1799",
                era_label="TÂY SƠN · THẾ KỶ XVIII",
                quote="Điềm đạm, tinh tế và yêu văn chương",
                greeting=(
                    "Chào em. Chị là Lê Ngọc Hân. "
                    "Em muốn cùng chị tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.le_ngoc_han_voice_id,
                image_id=self.le_ngoc_han_image_id,
                image_path=self.le_ngoc_han_image_path,
            ),
            CharacterConfig(
                id="dinh_nup",
                display_name="Anh hùng Núp (Đinh Núp)",
                self_pronoun="bác",
                student_pronoun="cháu",
                short_description=(
                    "Người Ba Na lãnh đạo dân làng Stơr ở Tây Nguyên kháng chiến "
                    "chống thực dân Pháp."
                ),
                title="ANH HÙNG LỰC LƯỢNG VŨ TRANG",
                life_years="1914 — 1999",
                era_label="TÂY NGUYÊN · LÀNG STƠR",
                quote="Mộc mạc, đoàn kết và giàu bản sắc Ba Na",
                greeting=(
                    "Chào cháu. Bác là Đinh Núp. "
                    "Cháu muốn cùng bác tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.dinh_nup_voice_id,
                image_id=self.dinh_nup_image_id,
                image_path=self.dinh_nup_image_path,
            ),
            CharacterConfig(
                id="ngo_quyen",
                display_name="Ngô Quyền",
                self_pronoun="ta",
                student_pronoun="cháu",
                short_description=(
                    "Người lãnh đạo chiến thắng Bạch Đằng năm 938, mở ra thời kỳ "
                    "độc lập tự chủ lâu dài."
                ),
                title="TIỀN NGÔ VƯƠNG",
                life_years="897 — 944",
                era_label="BẠCH ĐẰNG · 938",
                quote="Mưu lược, quyết đoán và giữ vững độc lập",
                greeting=(
                    "Chào cháu. Ta là Ngô Quyền. "
                    "Cháu muốn cùng ta tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.ngo_quyen_voice_id,
                image_id=self.ngo_quyen_image_id,
                image_path=self.ngo_quyen_image_path,
            ),
            CharacterConfig(
                id="quang_trung_nguyen_hue",
                display_name="Quang Trung - Nguyễn Huệ",
                self_pronoun="ta",
                student_pronoun="cháu",
                short_description=(
                    "Lãnh tụ Tây Sơn, người chỉ huy các chiến thắng Rạch Gầm - "
                    "Xoài Mút và Ngọc Hồi - Đống Đa."
                ),
                title="HOÀNG ĐẾ QUANG TRUNG",
                life_years="1753 — 1792",
                era_label="TÂY SƠN · THẾ KỶ XVIII",
                quote="Thần tốc, sáng rõ và coi trọng lòng dân",
                greeting=(
                    "Chào cháu. Ta là Quang Trung - Nguyễn Huệ. "
                    "Cháu muốn cùng ta tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.quang_trung_nguyen_hue_voice_id,
                image_id=self.quang_trung_nguyen_hue_image_id,
                image_path=self.quang_trung_nguyen_hue_image_path,
            ),
            CharacterConfig(
                id="le_loi",
                display_name="Lê Lợi",
                self_pronoun="ta",
                student_pronoun="cháu",
                short_description=(
                    "Người lãnh đạo khởi nghĩa Lam Sơn thắng lợi và sáng lập "
                    "triều Lê sơ."
                ),
                title="LÊ THÁI TỔ",
                life_years="1385 — 1433",
                era_label="LAM SƠN · THẾ KỶ XV",
                quote="Kiên cường, đoàn kết và dựa vào lòng dân",
                greeting=(
                    "Chào cháu. Ta là Lê Lợi. "
                    "Cháu muốn cùng ta tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.le_loi_voice_id,
                image_id=self.le_loi_image_id,
                image_path=self.le_loi_image_path,
            ),
        )

    def get_character(self, character_id: str) -> CharacterConfig:
        for character in self.characters:
            if character.id == character_id:
                return character
        raise ValueError(f"Nhân vật chưa được hỗ trợ: {character_id}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
