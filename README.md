# AI Digital Hero Orchestrator

Orchestrator độc lập kết nối ba API đang chạy sẵn:

```text
Browser
  ├── text ───────────────────────────────┐
  └── microphone → WebSocket proxy → LLM │
                                           ▼
LLM :8005 → OmniVoice TTS :8989 → SoulX LipSync :8990
                                           │
                                           ▼
                           Orchestrator + frontend :8991
```

Phiên bản demo cố định:

- Nhân vật: Tô Vĩnh Diện (`to_vinh_dien`).
- Giọng đọc: `001`.
- Ảnh LipSync: `001` (`images/001.jpg` trên SSH).
- Frontend: React + Vite + Tailwind CSS.
- Backend: FastAPI.
- Không sửa hoặc import code từ ba service upstream.

## Luồng xử lý

1. Frontend gửi câu hỏi tới `POST /api/v1/talk`.
2. Orchestrator tạo job riêng và trả HTTP `202`.
3. Job gọi LLM lấy câu trả lời nhưng chưa công bố ra frontend.
4. Job gọi TTS, polling tới khi nhận `audio_path`.
5. Job chuyển `image_id=001` và `audio_path` cho LipSync.
6. Job polling LipSync, xin URL có chữ ký và tải MP4 về storage của orchestrator.
7. Chỉ khi MP4 tải xong, API mới trả cả `answer` và `video_url`.
8. Frontend thay ảnh tĩnh bằng video; video phát xong tự quay lại ảnh.

Voice không gọi LLM chat tự động. WebSocket voice chỉ stream transcript vào ô nhập theo từng `transcript.delta`. Khi nhận `transcript.final`, người dùng vẫn có thể sửa câu hỏi rồi bấm gửi.

## Cổng và endpoint

| Service | Cổng | Endpoint dùng bởi orchestrator |
| --- | ---: | --- |
| LLM | `8005` | `POST /v1/characters/to_vinh_dien/chat` |
| LLM voice | `8005` | `WS /v1/characters/to_vinh_dien/voice` |
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

Trong `.env`, thêm đường dẫn thật tới ảnh đang có trên SSH:

```dotenv
CHARACTER_IMAGE_HOST_PATH=/duong-dan-tuyet-doi/AI_DIGITAL_HERO/LipSync_CB/images/001.jpg
```

Nếu đã có `CHARACTER_IMAGE_PATH` là đường dẫn tuyệt đối thì Docker Compose cũng
dùng trực tiếp giá trị đó; không bắt buộc khai báo thêm `CHARACTER_IMAGE_HOST_PATH`.

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

### Tạo cuộc trò chuyện

```bash
curl -X POST http://127.0.0.1:8991/api/v1/talk \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo-session-001",
    "message": "Chú sinh năm bao nhiêu?"
  }'
```

Response `202`:

```json
{
  "job_id": "...",
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
- Ba service upstream vẫn chịu trách nhiệm cho model, Redis/Celery và thư mục dùng chung `/dev/shm/audio` giữa TTS với LipSync.
