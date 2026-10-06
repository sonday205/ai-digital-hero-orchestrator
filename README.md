# AI Digital Hero Orchestrator

Orchestrator độc lập kết nối ba API đang chạy sẵn:

```text
Browser
  ├── text ───────────────────────────────┐
  └── microphone → WebSocket proxy → LLM │
                                           ▼
LLM_V3 :8005 → OmniVoice TTS :8989 → SoulX LipSync :8990
                                           │
                                           ▼
                           Orchestrator + frontend :8991
```

Phiên bản hiện tại hỗ trợ **48 nhân vật**, đồng bộ ID với LLM_V3.
Danh sách đầy đủ: [CHARACTERS.md](CHARACTERS.md).
Catalog nằm ở `data/characters.json`; không cần thêm một khối Python cho mỗi nhân vật.
Hướng dẫn cập nhật server: [LLM_V3_MIGRATION.md](docs/LLM_V3_MIGRATION.md).

- Frontend: React + Vite + Tailwind CSS.
- Backend: FastAPI.
- Không sửa hoặc import code từ ba service upstream.
- Sidebar cho phép đổi nhân vật, tạo phiên mới và mở lại các phiên đã lưu trong
  `localStorage` của trình duyệt.

## Luồng xử lý

1. Frontend gửi `character_id`, `session_id` và câu hỏi tới `POST /api/v1/talk`.
2. Orchestrator tạo job riêng và trả HTTP `202`.
3. Orchestrator resolve mapping nhân vật, ví dụ Võ Thị Sáu thành
   `vo_thi_sau → voice 002 → image 002`.
4. Job gọi LLM lấy câu trả lời nhưng chưa công bố ra frontend.
5. Job gọi đúng giọng TTS và polling tới khi nhận `audio_path`.
6. Job chuyển đúng `image_id` cùng `audio_path` cho LipSync.
7. Job polling LipSync, xin URL có chữ ký và tải MP4 về storage của orchestrator.
8. Chỉ khi MP4 tải xong, API mới trả cả `answer` và `video_url`.
9. Frontend thay toàn bộ ảnh tĩnh bằng video LipSync, giữ đầy đủ khung hình và tỷ lệ
   bằng `object-fit: contain`; không ghép riêng vùng mặt. Video phát xong hoặc lỗi
   thì tự quay lại ảnh.

Voice không gọi LLM chat tự động. WebSocket voice chỉ stream transcript vào ô nhập theo từng `transcript.delta`. Khi nhận `transcript.final`, người dùng vẫn có thể sửa câu hỏi rồi bấm gửi.

## Cổng và endpoint

| Service | Cổng | Endpoint dùng bởi orchestrator |
| --- | ---: | --- |
| LLM | `8005` | `POST /v1/characters/{character_id}/chat` |
| LLM voice | `8005` | `WS /v1/characters/{character_id}/voice` |
| TTS | `8989` | `POST /api/v1/tts/generate`, `GET /status/{task_id}` |
| LipSync | `8990` | `POST /api/v1/lipsync/generate`, polling task, tải video |
| Orchestrator | `8991` | Frontend và API public |

Frontend chỉ truy cập cổng `8991`.

## Chạy local để phát triển

### 1. Backend

```bash
cd orchestrator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8991 --reload
```

### 2. Frontend dev server

Mở terminal khác:

```bash
cd orchestrator/frontend
npm install
npm run dev
```

Mở <http://127.0.0.1:5173>. Vite sẽ proxy REST và WebSocket sang FastAPI `8991`.

### 3. Chạy bản frontend đã build

```bash
cd orchestrator/frontend
npm run build
cd ..
uvicorn app.main:app --host 0.0.0.0 --port 8991
```

Mở <http://127.0.0.1:8991>.

Microphone của trình duyệt chỉ hoạt động trong secure context. Khi test qua SSH,
chọn một trong hai cách:

- Đặt HTTPS reverse proxy phía trước cổng `8991`; hoặc
- Tạo SSH tunnel `ssh -L 8991:127.0.0.1:8991 user@server` rồi mở
  <http://127.0.0.1:8991> trên máy cá nhân.

Không nên mở bằng `http://IP_SSH:8991` nếu cần microphone vì đa số trình duyệt
sẽ chặn `getUserMedia` trên HTTP không phải localhost.

## Chạy Docker trên SSH

Ba upstream phải expose đúng các cổng `8005`, `8989`, `8990` trên cùng host SSH.

Tạo `.env`:

```bash
cd orchestrator
cp .env.example .env
```

Trong `.env`, thêm đúng các đường dẫn ảnh đang có trên SSH. Ví dụ:

```dotenv
TO_VINH_DIEN_IMAGE_HOST_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/001.jpg
VO_THI_SAU_IMAGE_HOST_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/002.jpg
KIM_DONG_IMAGE_HOST_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/003.jpg
# ... tiếp tục tới LE_LOI_IMAGE_HOST_PATH trỏ tới 014.jpg
```

Các file này được mount read-only vào container orchestrator để frontend hiển thị
ảnh tĩnh. Nếu chưa cấu hình, nhân vật dùng SVG giữ chỗ chung trên
frontend. SVG này không phải ảnh đầu vào cho model LipSync.

LipSync vẫn tự resolve các mã `001`–`048` trong image storage của chính service;
orchestrator không gửi đường dẫn filesystem của ảnh qua API.

Khi chạy backend trực tiếp trên host thay vì Docker, dùng:

```dotenv
CHARACTER_IMAGE_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/001.jpg
VO_THI_SAU_IMAGE_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/002.jpg
KIM_DONG_IMAGE_PATH=/home/cbrain/ai_digital_hero/LipSync_CB/images/003.jpg
# ... tiếp tục tới LE_LOI_IMAGE_PATH trỏ tới 014.jpg
```

### Tài nguyên bắt buộc ở TTS và LipSync

Việc thêm mapping trong orchestrator không tự tạo mẫu giọng hoặc chân dung thật.
Trước khi chạy end-to-end, hai upstream phải có đủ tài nguyên tương ứng:

```text
tts_omnivoice_with_redis/voice_data/003/ref.txt
tts_omnivoice_with_redis/voice_data/003/ref_audio.mp3 (hoặc .wav)
...
tts_omnivoice_with_redis/voice_data/014/ref.txt
tts_omnivoice_with_redis/voice_data/014/ref_audio.mp3 (hoặc .wav)
...
tts_omnivoice_with_redis/voice_data/047/ref.txt
tts_omnivoice_with_redis/voice_data/047/ref_audio.mp3 (hoặc .wav)

lipsync_cb_api/images/003.jpg (hoặc .jpeg/.png)
...
lipsync_cb_api/images/014.jpg (hoặc .jpeg/.png)
...
lipsync_cb_api/images/047.jpg (hoặc .jpeg/.png)
```

Hiện orchestrator sẽ gửi đúng `voice_id` và `image_id`; TTS/LipSync chịu trách
nhiệm kiểm tra và dùng các file media thật trên.

Các biến `LLM_BASE_URL`, `TTS_BASE_URL` và `LIPSYNC_BASE_URL` dành cho lúc chạy
orchestrator trực tiếp trên host. Docker Compose cố ý dùng nhóm `DOCKER_*_BASE_URL`
để tránh đưa `127.0.0.1` vào container. Mặc định container kết nối các service
trên host qua `host.docker.internal`.

Nếu LipSync được publish bằng `API_PORT` khác `8990`, cấu hình cổng host thực tế
cho orchestrator, ví dụ `DOCKER_LIPSYNC_BASE_URL=http://host.docker.internal:8990`.

Build và chạy:

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8991/health
curl http://127.0.0.1:8991/api/health/upstreams
```

`host.docker.internal:host-gateway` được cấu hình để container orchestrator gọi các API đã expose trên host SSH. Không dùng `127.0.0.1` cho upstream bên trong container vì địa chỉ đó sẽ trỏ về chính container orchestrator.

## API của orchestrator

### Danh sách nhân vật

```bash
curl http://127.0.0.1:8991/api/v1/characters
```

Response chứa metadata hiển thị, `voice_id`, `image_id` và `image_url`. Frontend
lấy danh sách này từ orchestrator thay vì tự suy luận mapping giữa các service.

### Tạo cuộc trò chuyện

```bash
curl -X POST http://127.0.0.1:8991/api/v1/talk \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo-session-vo-thi-sau-001",
    "character_id": "vo_thi_sau",
    "message": "Chị sinh năm bao nhiêu?"
  }'
```

Response `202`:

```json
{
  "job_id": "...",
  "character_id": "vo_thi_sau",
  "status": "queued",
  "status_url": "/api/v1/jobs/..."
}
```

### Polling job

```bash
curl http://127.0.0.1:8991/api/v1/jobs/JOB_ID
```

Các stage:

- `asking_llm`
- `generating_voice`
- `generating_video`
- `downloading_video`
- `completed` hoặc `failed`

Trường `answer` và `video_url` chỉ xuất hiện khi stage là `completed`.

## Kiểm tra

```bash
python -m pytest -q
cd frontend && npm run build
docker compose config
```

## Giới hạn của bản demo

- Job store đang nằm trong RAM, phù hợp một instance demo. Restart orchestrator sẽ mất metadata của job đang chạy.
- Video đã tải được lưu tại `storage/jobs/` và chưa có lịch cleanup tự động.
- Mỗi lần chỉ nên gửi một câu hỏi từ frontend; giao diện khóa composer trong lúc pipeline đang chạy.
- Danh sách session và tin nhắn hiển thị được lưu trong `localStorage` của từng
  trình duyệt. Memory phía LLM vẫn theo cơ chế riêng của LLM và có thể mất khi
  service LLM restart.
- Ba service upstream vẫn chịu trách nhiệm cho model, Redis/Celery và thư mục dùng chung `/dev/shm/audio` giữa TTS với LipSync.
