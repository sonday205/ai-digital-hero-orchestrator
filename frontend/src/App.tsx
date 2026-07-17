import {
  AlertCircle,
  ArrowUp,
  Check,
  CircleStop,
  LoaderCircle,
  Mic,
  ShieldCheck,
  Sparkles,
  Volume2,
} from "lucide-react";
import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type JobStage =
  | "queued"
  | "asking_llm"
  | "generating_voice"
  | "generating_video"
  | "downloading_video"
  | "completed"
  | "failed";

type JobResponse = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: JobStage;
  stage_label: string;
  message: string;
  answer: string | null;
  video_url: string | null;
  error: string | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

type VoiceState = "idle" | "connecting" | "listening" | "transcribing";
type ServiceState = "checking" | "ready" | "degraded" | "offline";

const stageOrder: JobStage[] = [
  "asking_llm",
  "generating_voice",
  "generating_video",
  "downloading_video",
];

const stageShortLabels: Record<JobStage, string> = {
  queued: "Tiếp nhận",
  asking_llm: "Suy nghĩ",
  generating_voice: "Tạo giọng",
  generating_video: "Tạo video",
  downloading_video: "Hoàn thiện",
  completed: "Hoàn thành",
  failed: "Có lỗi",
};

const sleep = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function getSessionId() {
  const saved = window.localStorage.getItem("digital-hero-session");
  if (saved) return saved;
  const generated = `demo-${crypto.randomUUID?.() ?? Date.now().toString(36)}`;
  window.localStorage.setItem("digital-hero-session", generated);
  return generated;
}

function floatToPcm16(input: Float32Array, inputRate: number) {
  const ratio = inputRate / 24_000;
  const length = Math.round(input.length / ratio);
  const output = new Int16Array(length);
  for (let index = 0; index < length; index += 1) {
    const source = Math.min(input.length - 1, Math.round(index * ratio));
    const value = Math.max(-1, Math.min(1, input[source]));
    output[index] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }
  return output.buffer;
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Chào cháu. Chú là Tô Vĩnh Diện. Cháu muốn cùng chú tìm hiểu điều gì về lịch sử?",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [serviceState, setServiceState] = useState<ServiceState>("checking");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const sessionId = useMemo(getSessionId, []);
  const isProcessing =
    isSubmitting || job?.status === "queued" || job?.status === "processing";
  const canSend = draft.trim().length > 0 && !isProcessing && voiceState === "idle";

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const voiceBaseRef = useRef("");
  const transcriptRef = useRef("");

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, job?.stage]);

  useEffect(() => {
    let active = true;

    async function checkServices() {
      try {
        const orchestrator = await fetch("/health", { cache: "no-store" });
        if (!orchestrator.ok) throw new Error("orchestrator unavailable");
        const upstreams = await fetch("/api/health/upstreams", { cache: "no-store" });
        const health = (await upstreams.json()) as { status?: "ok" | "degraded" };
        if (active) setServiceState(upstreams.ok && health.status === "ok" ? "ready" : "degraded");
      } catch {
        if (active) setServiceState("offline");
      }
    }

    void checkServices();
    const timer = window.setInterval(() => void checkServices(), 10_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    return () => {
      void releaseAudio();
      socketRef.current?.close();
    };
  }, []);

  async function submitMessage(event?: FormEvent) {
    event?.preventDefault();
    const message = draft.trim();
    if (!message || isProcessing) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: message,
    };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setError(null);
    setVideoUrl(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/talk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message }),
      });
      const accepted = await response.json();
      if (!response.ok) throw new Error(accepted.detail || `HTTP ${response.status}`);
      setJob({
        job_id: accepted.job_id,
        status: "queued",
        stage: "queued",
        stage_label: "Đang xếp yêu cầu vào hàng đợi",
        message,
        answer: null,
        video_url: null,
        error: null,
      });
      setIsSubmitting(false);

      let current: JobResponse;
      do {
        await sleep(1_500);
        const statusResponse = await fetch(accepted.status_url, { cache: "no-store" });
        current = await statusResponse.json();
        if (!statusResponse.ok) {
          throw new Error((current as unknown as { detail?: string }).detail || "Không đọc được trạng thái.");
        }
        setJob(current);
      } while (current.status === "queued" || current.status === "processing");

      if (current.status === "failed") {
        throw new Error(current.error || "Không thể hoàn thành video.");
      }
      if (!current.answer || !current.video_url) {
        throw new Error("Kết quả hoàn thành nhưng thiếu câu trả lời hoặc video.");
      }

      setMessages((existing) => [
        ...existing,
        { id: `${current.job_id}-answer`, role: "assistant", text: current.answer! },
      ]);
      setVideoUrl(`${current.video_url}?v=${Date.now()}`);
    } catch (caught) {
      const messageText = caught instanceof Error ? caught.message : "Đã xảy ra lỗi.";
      setIsSubmitting(false);
      setError(messageText);
      setJob((current) =>
        current
          ? { ...current, status: "failed", stage: "failed", stage_label: "Không thể hoàn thành", error: messageText }
          : current,
      );
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) void submitMessage();
    }
  }

  async function toggleVoice() {
    setError(null);
    if (voiceState === "listening") {
      await stopVoiceAndCommit();
      return;
    }
    if (voiceState !== "idle" || isProcessing) return;
    await startVoice();
  }

  async function startVoice() {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError("Microphone cần HTTPS, localhost hoặc 127.0.0.1 để hoạt động.");
      return;
    }
    setVoiceState("connecting");
    voiceBaseRef.current = draft.trim();
    transcriptRef.current = "";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(
        `${scheme}://${location.host}/api/v1/voice/to_vinh_dien`,
      );
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(
          JSON.stringify({ type: "session.start", session_id: sessionId, debug: false }),
        );
        startAudioCapture(stream, socket);
        setVoiceState("listening");
      };

      socket.onmessage = (messageEvent) => {
        const event = JSON.parse(messageEvent.data) as {
          type: string;
          delta?: string;
          transcript?: string;
          message?: string;
        };
        if (event.type === "transcript.delta") {
          transcriptRef.current += event.delta ?? "";
          setDraft(joinVoiceText(voiceBaseRef.current, transcriptRef.current));
        }
        if (event.type === "transcript.final") {
          transcriptRef.current = event.transcript ?? transcriptRef.current;
          setDraft(joinVoiceText(voiceBaseRef.current, transcriptRef.current));
          setVoiceState("idle");
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "session.close" }));
            socket.close();
          }
        }
        if (event.type === "error") {
          setError(event.message || "Không thể nhận diện giọng nói.");
          setVoiceState("idle");
          void releaseAudio();
        }
      };
      socket.onerror = () => {
        setError("Không kết nối được WebSocket voice của LLM.");
        setVoiceState("idle");
        void releaseAudio();
      };
    } catch (caught) {
      const message =
        caught instanceof DOMException && caught.name === "NotAllowedError"
          ? "Microphone đang bị chặn. Hãy cấp quyền rồi thử lại."
          : "Không thể mở microphone trên thiết bị này.";
      setError(message);
      setVoiceState("idle");
      await releaseAudio();
    }
  }

  function startAudioCapture(stream: MediaStream, socket: WebSocket) {
    const audioContext = new AudioContext({ sampleRate: 24_000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4_096, 1, 1);
    processor.onaudioprocess = (event) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(floatToPcm16(event.inputBuffer.getChannelData(0), audioContext.sampleRate));
      }
    };
    source.connect(processor);
    processor.connect(audioContext.destination);
    audioContextRef.current = audioContext;
    sourceRef.current = source;
    processorRef.current = processor;
  }

  async function stopVoiceAndCommit() {
    setVoiceState("transcribing");
    await releaseAudio();
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "input_audio.commit" }));
    } else {
      setError("Kết nối voice đã đóng trước khi nhận transcript.");
      setVoiceState("idle");
    }
  }

  async function releaseAudio() {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      await audioContextRef.current.close();
    }
    audioContextRef.current = null;
  }

  function resetVideo() {
    videoRef.current?.pause();
    setVideoUrl(null);
  }

  const activeStageIndex = job ? stageOrder.indexOf(job.stage) : -1;

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand-lockup">
          <div className="brand-seal" aria-hidden="true">VN</div>
          <div>
            <p className="brand-eyebrow">AI DIGITAL HERO</p>
            <p className="brand-name">Gặp gỡ lịch sử</p>
          </div>
        </div>
        <div className="service-status" aria-live="polite">
          <span className={`status-dot ${serviceState}`} />
          {serviceState === "checking" && "Đang kiểm tra dịch vụ"}
          {serviceState === "ready" && "Hệ thống sẵn sàng"}
          {serviceState === "degraded" && "Một dịch vụ chưa sẵn sàng"}
          {serviceState === "offline" && "Mất kết nối orchestrator"}
        </div>
      </header>

      <main className="main-grid">
        <section className="character-panel" aria-labelledby="character-title">
          <div className="portrait-frame">
            {videoUrl ? (
              <video
                ref={videoRef}
                className="character-media"
                src={videoUrl}
                autoPlay
                controls
                playsInline
                onEnded={resetVideo}
                aria-label="Video Tô Vĩnh Diện trả lời"
              />
            ) : (
              imageError ? (
                <div className="character-image-error" role="alert">
                  <AlertCircle aria-hidden="true" />
                  <span>Không tải được ảnh nhân vật. Hãy kiểm tra đường dẫn ảnh trên orchestrator.</span>
                </div>
              ) : (
                <img
                  className="character-media"
                  src="/api/v1/character/image"
                  alt="Nhân vật lịch sử Tô Vĩnh Diện"
                  onLoad={() => setImageError(false)}
                  onError={() => setImageError(true)}
                />
              )
            )}

            <div className="portrait-vignette" aria-hidden="true" />
            <div className="era-badge">ĐIỆN BIÊN PHỦ · 1954</div>

            {isProcessing && (
              <div className="processing-scrim" role="status" aria-live="polite">
                <div className="processing-mark"><LoaderCircle aria-hidden="true" /></div>
                <p className="processing-kicker">ĐANG DỰNG LẠI KÝ ỨC</p>
                <p className="processing-title">{job?.stage_label}</p>
                <p className="processing-note">Vui lòng chờ, câu trả lời sẽ xuất hiện cùng video.</p>
              </div>
            )}
          </div>

          <div className="character-caption">
            <div>
              <p className="caption-label">ANH HÙNG LIỆT SĨ</p>
              <h1 id="character-title">Tô Vĩnh Diện</h1>
              <p className="life-years">1924 — 1954</p>
            </div>
            <div className="voice-chip"><Volume2 aria-hidden="true" /> Giọng 001</div>
          </div>

          <blockquote>
            “Sống bám cầu, bám đường; chết kiên cường, dũng cảm.”
          </blockquote>
        </section>

        <section id="conversation" className="conversation-panel" aria-labelledby="conversation-title">
          <div className="conversation-header">
            <div>
              <p className="section-kicker">CUỘC TRÒ CHUYỆN</p>
              <h2 id="conversation-title">Hỏi chuyện người anh hùng</h2>
            </div>
            <div className="verified-chip"><ShieldCheck aria-hidden="true" /> Dữ liệu lịch sử</div>
          </div>

          <div className="message-list" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={`message-row ${message.role}`}>
                <p className="message-author">{message.role === "assistant" ? "TÔ VĨNH DIỆN" : "BẠN"}</p>
                <div className="message-bubble">{message.text}</div>
              </article>
            ))}

            {isProcessing && (
              <article className="message-row assistant pending-message">
                <p className="message-author">TÔ VĨNH DIỆN</p>
                <div className="message-bubble">
                  <LoaderCircle className="inline-loader" aria-hidden="true" />
                  {job?.stage_label ?? "Đang tiếp nhận câu hỏi"}
                </div>
              </article>
            )}
            <div ref={messagesEndRef} />
          </div>

          {job && isProcessing && (
            <div className="pipeline-progress" aria-label="Tiến trình tạo câu trả lời">
              {stageOrder.map((stage, index) => {
                const active = stage === job.stage;
                const done = activeStageIndex > index;
                return (
                  <div className={`pipeline-step ${active ? "active" : ""} ${done ? "done" : ""}`} key={stage}>
                    <span>{done ? <Check aria-hidden="true" /> : index + 1}</span>
                    <small>{stageShortLabels[stage]}</small>
                  </div>
                );
              })}
            </div>
          )}

          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle aria-hidden="true" />
              <span>{error}</span>
              <button type="button" onClick={() => setError(null)} aria-label="Đóng thông báo lỗi">×</button>
            </div>
          )}

          <form className="composer" onSubmit={submitMessage}>
            <label className="sr-only" htmlFor="message-input">Nhập câu hỏi cho Tô Vĩnh Diện</label>
            <textarea
              id="message-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder={voiceState === "listening" ? "Đang nghe, hãy nói câu hỏi…" : "Hỏi điều bạn muốn biết…"}
              maxLength={2000}
              rows={1}
              disabled={Boolean(isProcessing)}
            />
            <div className="composer-actions">
              <div className="voice-hint" aria-live="polite">
                {voiceState === "connecting" && "Đang mở micro…"}
                {voiceState === "listening" && "Đang nghe · chữ sẽ hiện ở ô nhập"}
                {voiceState === "transcribing" && "Đang hoàn thiện transcript…"}
                {voiceState === "idle" && "Enter để gửi · Shift + Enter xuống dòng"}
              </div>
              <div className="action-buttons">
                <button
                  className={`icon-button mic-button ${voiceState === "listening" ? "recording" : ""}`}
                  type="button"
                  onClick={() => void toggleVoice()}
                  disabled={Boolean(isProcessing) || voiceState === "connecting" || voiceState === "transcribing"}
                  aria-label={voiceState === "listening" ? "Dừng thu âm" : "Nhập câu hỏi bằng giọng nói"}
                >
                  {voiceState === "listening" ? <CircleStop aria-hidden="true" /> : <Mic aria-hidden="true" />}
                </button>
                <button className="send-button" type="submit" disabled={!canSend} aria-label="Gửi câu hỏi">
                  <ArrowUp aria-hidden="true" />
                </button>
              </div>
            </div>
          </form>

          <p className="learning-note"><Sparkles aria-hidden="true" /> Nội dung phục vụ học tập và được đối chiếu với kho tư liệu lịch sử.</p>
        </section>
      </main>

      <footer>
        <span>TRẢI NGHIỆM LỊCH SỬ TƯƠNG TÁC</span>
        <span className="footer-rule" />
        <span>LLM · OMNIVOICE · SOULX</span>
      </footer>
    </div>
  );
}

function joinVoiceText(base: string, transcript: string) {
  const normalizedTranscript = transcript.trimStart();
  if (!base) return normalizedTranscript;
  if (!normalizedTranscript) return base;
  return `${base} ${normalizedTranscript}`;
}

export default App;
