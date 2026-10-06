# Cập nhật orchestrator và LLM_V3 lên 48 nhân vật

Orchestrator dùng catalog `data/characters.json`, cùng 48 character_id của
Historical RAG API (repo GitHub `sonday205/LLM_V3`). Các cổng giữ nguyên:
LLM 8005, TTS 8989, LipSync 8990, orchestrator 8991.
Frontend lấy danh sách từ API, không có danh sách 48 nhân vật hard-code riêng.

## 1. Nạp dữ liệu mới vào LLM

Trong thư mục repo LLM_V3 trên server, giữ nguyên `.env` đang hoạt động:

```bash
git pull --ff-only
docker compose build
docker compose run --rm ingest
docker compose up -d api
```

Ingest phải thành công trước khi kiểm tra 48 nhân vật; giữ embedding provider
tương thích database hiện tại. Chỉ pull file chưa cập nhật danh sách trong DB.

## 2. Cập nhật orchestrator

Trong thư mục repo orchestrator trên server:

```bash
git pull --ff-only
# Chỉnh .env hiện có; không copy đè làm mất cấu hình đang chạy.
docker compose config --quiet
docker compose up -d --build
curl --fail http://127.0.0.1:8991/api/v1/characters
```

Nếu Git báo local changes, giữ/commit/stash chúng trước; không reset hard.
`LLM_API_KEY` chỉ là application key gửi qua `X-API-Key`, khớp auth của
LLM_V3 nếu bật; không phải Gemini/OpenAI key. Provider key chỉ đặt ở LLM_V3.

## 3. Mapping giọng và ảnh

Giữ các biến môi trường cũ của 001–014. Mã mặc định của nhân vật mới là
015–048, xem [CHARACTERS.md](../CHARACTERS.md).
TTS cần `voice_data/<voice_id>/ref.txt` và audio mẫu.
LipSync cần ảnh thật theo `<image_id>.jpg|jpeg|png` trong storage của nó.
Mapping không tự tạo tài nguyên media.

Ví dụ bổ sung vào `.env` của orchestrator:

```dotenv
CHARACTER_PORTRAITS_HOST_DIR=/home/cbrain/ai_digital_hero/LipSync_CB/images
CHARACTER_OVERRIDES_JSON={}
```

Compose mount thư mục trên read-only vào `/app/portraits` để hiển thị ảnh
015–048. Khi chạy Python trực tiếp, dùng `PORTRAIT_DIR` với đường dẫn host.
Ảnh thiếu dùng placeholder trên UI; placeholder không được gửi cho LipSync.
Đổi mapping bất kỳ bằng JSON (đường dẫn image_path phải tồn tại bên trong container):

```dotenv
CHARACTER_OVERRIDES_JSON={"ho_xuan_huong":{"voice_id":"047","image_id":"047","image_path":"/app/portraits/047.jpg"}}
```

LipSync hiện trả video của toàn bộ ảnh. UI thay ảnh tĩnh bằng video full-frame
cho mọi nhân vật, giữ tỷ lệ bằng `object-fit: contain`; không dùng tọa độ
`head_position.json` để ghép vùng mặt. Khi video kết thúc hoặc lỗi, UI quay lại ảnh tĩnh.

## Kiểm tra không cần GPU

```bash
python -m pytest -q
cd frontend
npm ci
npm run build
```

Test mock kiểm tra routing/catalog/media mapping/auth, không xác nhận chất lượng
LLM hay khả năng tạo video thật. Sau triển khai cần kiểm tra cả
`http://127.0.0.1:8005/v1/characters` (thêm X-API-Key nếu bật auth) và API
orchestrator: hai bên phải có cùng 48 ID. Chỉ test media thật trên máy có GPU.

## Cập nhật mapping 015–019 (2026-10-07)

Giữ nguyên 001–014. Mapping mới:
`pham_ngoc_thao → 015`, `vu_ngoc_nha → 016`, `dang_tran_duc → 017`,
`pham_xuan_an → 018`, `le_duc_thuy → 019`.
019 là Lê Đức Thúy, nguyên Thống đốc Ngân hàng Nhà nước, theo
[Wikipedia người dùng cung cấp](https://vi.wikipedia.org/wiki/L%C3%AA_%C4%90%E1%BB%A9c_Th%C3%BAy).
Không gán quân hàm Thiếu tướng; không dùng hồ sơ Lê Hữu Thúy cho 019. Lê Hữu Thúy giữ mã 020; Lý Tự Trọng
chuyển sang 048 để không trùng 015. Các mã 021–047 giữ nguyên.
ID API vẫn là slug; mã ba chữ số dùng cho voice/image.

Orchestrator hỗ trợ các biến `<CHARACTER_ID>_VOICE_ID`, `_IMAGE_ID`, `_IMAGE_PATH`
cho năm nhân vật trên, gồm `LE_DUC_THUY_*` cho 019.
Trên SSH, đặt ảnh thật trong LipSync và `voice_data/<id>/ref.txt` cùng audio mẫu
trong TTS theo mapping này. Có thể dùng `<CHARACTER_ID>_IMAGE_HOST_PATH` để mount
ảnh vào orchestrator; kiểm tra `CHARACTER_OVERRIDES_JSON` tránh override cũ.

Sau khi cập nhật source, trong repo LLM chạy:

```bash
docker compose build
docker compose run --rm ingest
docker compose up -d api
```

Phải ingest lại, không dùng `--missing-only`, để cập nhật nhân vật đã có trong DB.
Sau đó trong repo orchestrator:

```bash
docker compose up -d --build orchestrator
curl --fail http://127.0.0.1:8991/api/v1/characters
```
