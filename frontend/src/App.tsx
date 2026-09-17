import {
  AlertCircle,
  ArrowUp,
  CircleStop,
  Clock3,
  MessageSquareText,
  Mic,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldCheck,
  Sparkles,
  SquarePen,
  Trash2,
  Volume2,
  X,
} from "lucide-react";
import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import headPositionsData from "./head_position.json";

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
  character_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: JobStage;
  stage_label: string;
  message: string;
  answer: string | null;
  video_url: string | null;
  error: string | null;
};

type CharacterProfile = {
  id: string;
  display_name: string;
  self_pronoun: string;
  student_pronoun: string;
  short_description: string;
  title: string;
  life_years: string;
  era_label: string;
  quote: string;
  greeting: string;
  voice_id: string;
  image_id: string;
  image_url: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

type ChatSession = {
  id: string;
  character_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
};

type StoredConversationState = {
  active_session_id: string;
  sessions: ChatSession[];
};

type VoiceState = "idle" | "connecting" | "listening" | "transcribing";
type ServiceState = "checking" | "ready" | "degraded" | "offline";

type HeadPosition = {
  width: number;
  height: number;
  x: number;
  y: number;
};

const SESSION_STORAGE_KEY = "digital-hero-conversations-v1";
const LEGACY_SESSION_KEY = "digital-hero-session";
const SIDEBAR_STORAGE_KEY = "digital-hero-sidebar";
const SIDEBAR_DRAWER_QUERY = "(max-width: 1100px)";
const NEW_SESSION_TITLE = "Cuộc trò chuyện mới";
// head_position.json dùng hệ tọa độ của ảnh chân dung gốc 2048 × 2048.
const CHARACTER_IMAGE_SIZE = 2048;
const HEAD_POSITIONS = headPositionsData as Record<string, HeadPosition>;

function coordinateToPercent(value: number) {
  return `${(value / CHARACTER_IMAGE_SIZE) * 100}%`;
}

const FALLBACK_CHARACTERS: CharacterProfile[] = [
  {
    id: "to_vinh_dien",
    display_name: "Tô Vĩnh Diện",
    self_pronoun: "chú",
    student_pronoun: "cháu",
    short_description: "Anh hùng pháo binh trong Chiến dịch Điện Biên Phủ.",
    title: "ANH HÙNG LIỆT SĨ",
    life_years: "1924 — 1954",
    era_label: "ĐIỆN BIÊN PHỦ · 1954",
    quote: "Thà hy sinh, quyết bảo vệ pháo",
    greeting:
      "Chào cháu. Chú là Tô Vĩnh Diện. Cháu muốn cùng chú tìm hiểu điều gì về lịch sử?",
    voice_id: "001",
    image_id: "001",
    image_url: "/api/v1/characters/to_vinh_dien/image",
  },
  {
    id: "vo_thi_sau",
    display_name: "Võ Thị Sáu",
    self_pronoun: "chị",
    student_pronoun: "em",
    short_description: "Người con gái Đất Đỏ kiên cường trong kháng chiến chống Pháp.",
    title: "NỮ ANH HÙNG LIỆT SĨ",
    life_years: "1933 — 1952",
    era_label: "ĐẤT ĐỎ · CÔN ĐẢO",
    quote: "Tinh thần kiên định, không khuất phục",
    greeting:
      "Chào em. Chị là Võ Thị Sáu. Em muốn cùng chị tìm hiểu điều gì về lịch sử?",
    voice_id: "002",
    image_id: "002",
    image_url: "/api/v1/characters/vo_thi_sau/image",
  },
];

const sleep = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function createClientId() {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }

  if (typeof cryptoApi?.getRandomValues === "function") {
    const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10, 16).join(""),
    ].join("-");
  }

  return `fallback-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function createSession(character: CharacterProfile, preferredId?: string): ChatSession {
  const now = new Date().toISOString();
  return {
    id: preferredId || `session-${createClientId()}`,
    character_id: character.id,
    title: NEW_SESSION_TITLE,
    messages: [
      {
        id: `welcome-${createClientId()}`,
        role: "assistant",
        text: character.greeting,
      },
    ],
    created_at: now,
    updated_at: now,
  };
}

function loadConversationState(): StoredConversationState {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<StoredConversationState>;
      const sessions = Array.isArray(parsed.sessions)
        ? parsed.sessions.filter(isStoredSession)
        : [];
      const activeSessionExists = sessions.some(
        (session) => session.id === parsed.active_session_id,
      );
      if (sessions.length > 0) {
        return {
          sessions,
          active_session_id: activeSessionExists
            ? parsed.active_session_id!
            : sessions[0].id,
        };
      }
    }
  } catch {
    // Dữ liệu localStorage hỏng không được làm giao diện mất khả năng khởi động.
  }

  const legacySessionId = window.localStorage.getItem(LEGACY_SESSION_KEY) || undefined;
  const firstSession = createSession(FALLBACK_CHARACTERS[0], legacySessionId);
  return { sessions: [firstSession], active_session_id: firstSession.id };
}

function isStoredSession(value: unknown): value is ChatSession {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ChatSession>;
  return (
    typeof candidate.id === "string" &&
    candidate.id.length >= 8 &&
    typeof candidate.character_id === "string" &&
    typeof candidate.title === "string" &&
    Array.isArray(candidate.messages) &&
    candidate.messages.every(
      (message) =>
        Boolean(message) &&
        typeof message.id === "string" &&
        (message.role === "user" || message.role === "assistant") &&
        typeof message.text === "string",
    ) &&
    typeof candidate.created_at === "string" &&
    typeof candidate.updated_at === "string"
  );
}

function getInitialSidebarOpen() {
  const isDrawerViewport = window.matchMedia(SIDEBAR_DRAWER_QUERY).matches;
  if (isDrawerViewport) return false;
  return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) !== "closed";
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
  const initialConversationState = useMemo(loadConversationState, []);
  const [characters, setCharacters] = useState<CharacterProfile[]>(FALLBACK_CHARACTERS);
  const [sessions, setSessions] = useState<ChatSession[]>(
    initialConversationState.sessions,
  );
  const [activeSessionId, setActiveSessionId] = useState(
    initialConversationState.active_session_id,
  );
  const [draft, setDraft] = useState("");
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [serviceState, setServiceState] = useState<ServiceState>("checking");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(getInitialSidebarOpen);
  const [isDrawerViewport, setIsDrawerViewport] = useState(
    () => window.matchMedia(SIDEBAR_DRAWER_QUERY).matches,
  );
  const [sessionPendingDelete, setSessionPendingDelete] =
    useState<ChatSession | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) || sessions[0];
  const activeCharacter =
    characters.find((character) => character.id === activeSession?.character_id) ||
    FALLBACK_CHARACTERS[0];
  const activeHeadPosition = HEAD_POSITIONS[activeCharacter.image_id];
  const faceVideoStyle = activeHeadPosition
    ? {
        left: coordinateToPercent(activeHeadPosition.x),
        top: coordinateToPercent(activeHeadPosition.y),
        width: coordinateToPercent(activeHeadPosition.width),
        height: coordinateToPercent(activeHeadPosition.height),
      }
    : undefined;
  const messages = activeSession?.messages || [];
  const characterSessions = sessions
    .filter((session) => session.character_id === activeCharacter.id)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  const isProcessing =
    isSubmitting || job?.status === "queued" || job?.status === "processing";
  const navigationLocked = isProcessing || voiceState !== "idle";
  const canSend = draft.trim().length > 0 && !isProcessing && voiceState === "idle";

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const deleteDialogRef = useRef<HTMLDialogElement | null>(null);
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
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({ active_session_id: activeSessionId, sessions }),
    );
    window.localStorage.setItem(LEGACY_SESSION_KEY, activeSessionId);
  }, [activeSessionId, sessions]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(SIDEBAR_DRAWER_QUERY);
    const handleViewportChange = (event: MediaQueryListEvent | MediaQueryList) => {
      setIsDrawerViewport(event.matches);
      if (event.matches) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(
          window.localStorage.getItem(SIDEBAR_STORAGE_KEY) !== "closed",
        );
      }
    };

    handleViewportChange(mediaQuery);
    mediaQuery.addEventListener("change", handleViewportChange);
    return () => mediaQuery.removeEventListener("change", handleViewportChange);
  }, []);

  useEffect(() => {
    if (!isDrawerViewport) {
      window.localStorage.setItem(
        SIDEBAR_STORAGE_KEY,
        isSidebarOpen ? "open" : "closed",
      );
    }
  }, [isDrawerViewport, isSidebarOpen]);

  useEffect(() => {
    const dialog = deleteDialogRef.current;
    if (!dialog) return;
    if (sessionPendingDelete && !dialog.open) dialog.showModal();
    if (!sessionPendingDelete && dialog.open) dialog.close();
  }, [sessionPendingDelete]);

  useEffect(() => {
    function closeDrawerWithEscape(event: globalThis.KeyboardEvent) {
      if (
        event.key === "Escape" &&
        isDrawerViewport &&
        isSidebarOpen &&
        !deleteDialogRef.current?.open
      ) {
        setIsSidebarOpen(false);
      }
    }

    window.addEventListener("keydown", closeDrawerWithEscape);
    return () => window.removeEventListener("keydown", closeDrawerWithEscape);
  }, [isDrawerViewport, isSidebarOpen]);

  useEffect(() => {
    document.title = `Gặp gỡ lịch sử — ${activeCharacter.display_name}`;
  }, [activeCharacter.display_name]);

  useEffect(() => {
    let active = true;

    async function loadCharacters() {
      try {
        const response = await fetch("/api/v1/characters", { cache: "no-store" });
        const payload = (await response.json()) as CharacterProfile[];
        if (active && response.ok && Array.isArray(payload) && payload.length > 0) {
          setCharacters(payload);
        }
      } catch {
        // Fallback local giữ UI sử dụng được khi backend đang khởi động.
      }
    }

    void loadCharacters();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function checkServices() {
      try {
        const orchestrator = await fetch("/health", { cache: "no-store" });
        if (!orchestrator.ok) throw new Error("orchestrator unavailable");
        const upstreams = await fetch("/api/health/upstreams", { cache: "no-store" });
        const health = (await upstreams.json()) as { status?: "ok" | "degraded" };
        if (active) {
          setServiceState(
            upstreams.ok && health.status === "ok" ? "ready" : "degraded",
          );
        }
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
    if (!message || isProcessing || !activeSession) return;

    const requestSessionId = activeSession.id;
    const requestCharacterId = activeCharacter.id;
    appendMessage(requestSessionId, {
      id: createClientId(),
      role: "user",
      text: message,
    });
    setDraft("");
    setError(null);
    setVideoUrl(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/talk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: requestSessionId,
          character_id: requestCharacterId,
          message,
        }),
      });
      const accepted = await response.json();
      if (!response.ok) throw new Error(accepted.detail || `HTTP ${response.status}`);
      setJob({
        job_id: accepted.job_id,
        character_id: accepted.character_id || requestCharacterId,
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
          throw new Error(
            (current as unknown as { detail?: string }).detail ||
              "Không đọc được trạng thái.",
          );
        }
        setJob(current);
      } while (current.status === "queued" || current.status === "processing");

      if (current.status === "failed") {
        throw new Error(current.error || "Không thể hoàn thành video.");
      }
      if (!current.answer || !current.video_url) {
        throw new Error("Kết quả hoàn thành nhưng thiếu câu trả lời hoặc video.");
      }

      appendMessage(requestSessionId, {
        id: `${current.job_id}-answer`,
        role: "assistant",
        text: current.answer,
      });
      setVideoUrl(`${current.video_url}?v=${Date.now()}`);
    } catch (caught) {
      const messageText = caught instanceof Error ? caught.message : "Đã xảy ra lỗi.";
      setIsSubmitting(false);
      setError(messageText);
      setJob((current) =>
        current
          ? {
              ...current,
              status: "failed",
              stage: "failed",
              stage_label: "Không thể hoàn thành",
              error: messageText,
            }
          : current,
      );
    }
  }

  function appendMessage(sessionId: string, message: ChatMessage) {
    setSessions((current) =>
      current.map((session) => {
        if (session.id !== sessionId) return session;
        const title =
          message.role === "user" && session.title === NEW_SESSION_TITLE
            ? createSessionTitle(message.text)
            : session.title;
        return {
          ...session,
          title,
          messages: [...session.messages, message],
          updated_at: new Date().toISOString(),
        };
      }),
    );
  }

  function selectCharacter(characterId: string) {
    if (navigationLocked || characterId === activeCharacter.id) return;
    const existing = sessions
      .filter((session) => session.character_id === characterId)
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];
    if (existing) {
      setActiveSessionId(existing.id);
    } else {
      const character =
        characters.find((item) => item.id === characterId) || FALLBACK_CHARACTERS[0];
      const created = createSession(character);
      setSessions((current) => [created, ...current]);
      setActiveSessionId(created.id);
    }
    resetConversationView();
    closeSidebarOnDrawer();
  }

  function selectSession(sessionId: string) {
    if (navigationLocked || sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    resetConversationView();
    closeSidebarOnDrawer();
  }

  function startNewSession() {
    if (navigationLocked) return;
    const created = createSession(activeCharacter);
    setSessions((current) => [created, ...current]);
    setActiveSessionId(created.id);
    resetConversationView();
    closeSidebarOnDrawer();
  }

  function closeSidebarOnDrawer() {
    if (isDrawerViewport) setIsSidebarOpen(false);
  }

  function requestSessionDelete(session: ChatSession) {
    if (navigationLocked || deletingSessionId) return;
    setSessionPendingDelete(session);
  }

  async function confirmSessionDelete() {
    const session = sessionPendingDelete;
    if (!session || navigationLocked || deletingSessionId) return;
    setDeletingSessionId(session.id);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/characters/${encodeURIComponent(session.character_id)}/sessions/${encodeURIComponent(session.id)}`,
        { method: "DELETE" },
      );
      const payload = (await response.json().catch(() => ({}))) as { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Không thể xóa cuộc trò chuyện.");
      }

      const remainingSessions = sessions.filter((item) => item.id !== session.id);
      if (session.id === activeSessionId) {
        const nextSession = remainingSessions
          .filter((item) => item.character_id === session.character_id)
          .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];

        if (nextSession) {
          setActiveSessionId(nextSession.id);
          setSessions(remainingSessions);
        } else {
          const character =
            characters.find((item) => item.id === session.character_id) ||
            FALLBACK_CHARACTERS[0];
          const replacement = createSession(character);
          setSessions([replacement, ...remainingSessions]);
          setActiveSessionId(replacement.id);
        }
        resetConversationView();
      } else {
        setSessions(remainingSessions);
      }
      setSessionPendingDelete(null);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Không thể xóa cuộc trò chuyện.",
      );
      setSessionPendingDelete(null);
    } finally {
      setDeletingSessionId(null);
    }
  }

  function resetConversationView() {
    resetVideo();
    setDraft("");
    setJob(null);
    setError(null);
    setImageError(false);
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
    if (!activeSession) {
      setError("Không tìm thấy phiên trò chuyện đang hoạt động.");
      return;
    }
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
        `${scheme}://${location.host}/api/v1/voice/${activeCharacter.id}`,
      );
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(
          JSON.stringify({
            type: "session.start",
            session_id: activeSession.id,
            debug: false,
          }),
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
        socket.send(
          floatToPcm16(event.inputBuffer.getChannelData(0), audioContext.sampleRate),
        );
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

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-left">
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setIsSidebarOpen((current) => !current)}
            aria-label={isSidebarOpen ? "Đóng thanh bên" : "Mở thanh bên"}
            aria-expanded={isSidebarOpen}
            aria-controls="conversation-sidebar"
          >
            {isSidebarOpen ? (
              <PanelLeftClose aria-hidden="true" />
            ) : (
              <PanelLeftOpen aria-hidden="true" />
            )}
          </button>
          <div className="brand-lockup">
            <div className="brand-seal" aria-hidden="true">VN</div>
            <div>
              <p className="brand-eyebrow">AI DIGITAL HERO</p>
              <p className="brand-name">Gặp gỡ lịch sử</p>
            </div>
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

      {isDrawerViewport && isSidebarOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Đóng thanh bên"
        />
      )}

      <div
        className={`workspace-layout ${isSidebarOpen ? "sidebar-open" : "sidebar-closed"}`}
      >
        <aside
          id="conversation-sidebar"
          className={`history-sidebar ${isSidebarOpen ? "is-open" : "is-closed"}`}
          aria-label="Nhân vật và phiên trò chuyện"
          aria-hidden={!isSidebarOpen}
        >
          <div className="sidebar-topbar">
            <div className="sidebar-brand">
              <div className="sidebar-brand-mark" aria-hidden="true">VN</div>
              <div>
                <strong>Gặp gỡ lịch sử</strong>
                <small>Trò chuyện cùng nhân vật</small>
              </div>
            </div>
            <button
              className="sidebar-close-button"
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              aria-label="Đóng thanh bên"
            >
              <PanelLeftClose aria-hidden="true" />
            </button>
          </div>

          <button
            className="sidebar-new-chat"
            type="button"
            onClick={startNewSession}
            disabled={navigationLocked}
          >
            <SquarePen aria-hidden="true" />
            <span>Cuộc trò chuyện mới</span>
          </button>

          <p className="sidebar-section-label">NHÂN VẬT</p>
          <div className="character-selector" role="list" aria-label="Danh sách nhân vật">
            {characters.map((character) => {
              const isActive = character.id === activeCharacter.id;
              return (
                <button
                  key={character.id}
                  className={`character-option ${isActive ? "active" : ""}`}
                  type="button"
                  onClick={() => selectCharacter(character.id)}
                  disabled={navigationLocked}
                  aria-pressed={isActive}
                >
                  <img src={character.image_url} alt="" aria-hidden="true" />
                  <span>
                    <strong>{character.display_name}</strong>
                    <small>Giọng {character.voice_id}</small>
                  </span>
                </button>
              );
            })}
          </div>

          <div className="session-heading">
            <div>
              <p className="sidebar-section-label">GẦN ĐÂY</p>
              <p>{characterSessions.length} phiên với {activeCharacter.display_name}</p>
            </div>
          </div>

          <nav className="session-list" aria-label="Các phiên trò chuyện đã lưu">
            {characterSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <div
                  key={session.id}
                  className={`session-row ${isActive ? "active" : ""}`}
                >
                  <button
                    className="session-option"
                    type="button"
                    onClick={() => selectSession(session.id)}
                    disabled={navigationLocked}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <MessageSquareText aria-hidden="true" />
                    <span>
                      <strong>{session.title}</strong>
                      <small>
                        <Clock3 aria-hidden="true" /> {formatSessionTime(session.updated_at)}
                      </small>
                    </span>
                  </button>
                  <button
                    className="session-delete-button"
                    type="button"
                    onClick={() => requestSessionDelete(session)}
                    disabled={navigationLocked || deletingSessionId === session.id}
                    aria-label={`Xóa cuộc trò chuyện ${session.title}`}
                  >
                    <Trash2 aria-hidden="true" />
                  </button>
                </div>
              );
            })}
          </nav>

          <p className="sidebar-note">
            Lịch sử phiên được lưu trên trình duyệt này.
          </p>
        </aside>

        <main className="main-grid">
          <section className="character-panel" aria-labelledby="character-title">
            <div className="portrait-frame">
              {imageError ? (
                <div className="character-image-error" role="alert">
                  <AlertCircle aria-hidden="true" />
                  <span>
                    Không tải được ảnh nhân vật. Hãy kiểm tra đường dẫn ảnh trên orchestrator.
                  </span>
                </div>
              ) : (
                <div className="character-media-canvas">
                  <img
                    key={activeCharacter.id}
                    className="character-media"
                    src={activeCharacter.image_url}
                    alt={`Nhân vật lịch sử ${activeCharacter.display_name}`}
                    onLoad={() => setImageError(false)}
                    onError={() => setImageError(true)}
                  />

                  {videoUrl ? (
                    <video
                      ref={videoRef}
                      className={
                        activeHeadPosition
                          ? "character-face-video"
                          : "character-media character-video-fallback"
                      }
                      style={faceVideoStyle}
                      src={videoUrl}
                      autoPlay
                      controls={false}
                      playsInline
                      controlsList="nodownload noplaybackrate noremoteplayback"
                      disablePictureInPicture
                      disableRemotePlayback
                      tabIndex={-1}
                      onContextMenu={(event) => event.preventDefault()}
                      onError={resetVideo}
                      onEnded={resetVideo}
                      aria-hidden="true"
                    />
                  ) : null}
                </div>
              )}

              <div className="portrait-vignette" aria-hidden="true" />
              <div className="era-badge">{activeCharacter.era_label}</div>
            </div>

            <div className="character-caption">
              <div>
                <p className="caption-label">{activeCharacter.title}</p>
                <h1 id="character-title">{activeCharacter.display_name}</h1>
                <p className="life-years">{activeCharacter.life_years}</p>
              </div>
              <div className="voice-chip">
                <Volume2 aria-hidden="true" /> Giọng {activeCharacter.voice_id}
              </div>
            </div>

            <blockquote>{activeCharacter.quote}</blockquote>
          </section>

          <section
            id="conversation"
            className="conversation-panel"
            aria-labelledby="conversation-title"
          >
            <div className="conversation-header">
              <div>
                <p className="section-kicker">CUỘC TRÒ CHUYỆN</p>
                <h2 id="conversation-title">Hỏi chuyện {activeCharacter.display_name}</h2>
              </div>
              <div className="verified-chip">
                <ShieldCheck aria-hidden="true" /> Dữ liệu lịch sử
              </div>
            </div>

            <div className="message-list" aria-live="polite">
              {messages.map((message) => (
                <article key={message.id} className={`message-row ${message.role}`}>
                  <p className="message-author">
                    {message.role === "assistant"
                      ? activeCharacter.display_name.toLocaleUpperCase("vi-VN")
                      : "BẠN"}
                  </p>
                  <div className="message-bubble">{message.text}</div>
                </article>
              ))}

              {isProcessing && (
                <article
                  className="message-row assistant pending-message"
                  role="status"
                  aria-label="Đang xử lý câu trả lời"
                >
                  <p className="message-author">
                    {activeCharacter.display_name.toLocaleUpperCase("vi-VN")}
                  </p>
                  <div className="message-bubble typing-bubble">
                    <span className="typing-dots" aria-hidden="true">
                      <span>.</span><span>.</span><span>.</span>
                    </span>
                  </div>
                </article>
              )}
              <div ref={messagesEndRef} />
            </div>

            {error && (
              <div className="error-banner" role="alert">
                <AlertCircle aria-hidden="true" />
                <span>{error}</span>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  aria-label="Đóng thông báo lỗi"
                >×</button>
              </div>
            )}

            <form className="composer" onSubmit={submitMessage}>
              <label className="sr-only" htmlFor="message-input">
                Nhập câu hỏi cho {activeCharacter.display_name}
              </label>
              <textarea
                id="message-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder={
                  voiceState === "listening"
                    ? "Đang nghe, hãy nói câu hỏi…"
                    : `Hỏi ${activeCharacter.self_pronoun} điều bạn muốn biết…`
                }
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
                    className={`icon-button mic-button ${
                      voiceState === "listening" ? "recording" : ""
                    }`}
                    type="button"
                    onClick={() => void toggleVoice()}
                    disabled={
                      Boolean(isProcessing) ||
                      voiceState === "connecting" ||
                      voiceState === "transcribing"
                    }
                    aria-label={
                      voiceState === "listening"
                        ? "Dừng thu âm"
                        : "Nhập câu hỏi bằng giọng nói"
                    }
                  >
                    {voiceState === "listening" ? (
                      <CircleStop aria-hidden="true" />
                    ) : (
                      <Mic aria-hidden="true" />
                    )}
                  </button>
                  <button
                    className="send-button"
                    type="submit"
                    disabled={!canSend}
                    aria-label="Gửi câu hỏi"
                  >
                    <ArrowUp aria-hidden="true" />
                  </button>
                </div>
              </div>
            </form>

            <p className="learning-note">
              <Sparkles aria-hidden="true" /> Nội dung phục vụ học tập và được đối chiếu
              với kho tư liệu lịch sử.
            </p>
          </section>
        </main>
      </div>

      <dialog
        ref={deleteDialogRef}
        className="session-delete-dialog"
        aria-labelledby="delete-dialog-title"
        onCancel={(event) => {
          event.preventDefault();
          if (!deletingSessionId) setSessionPendingDelete(null);
        }}
        onClose={() => {
          if (!deletingSessionId) setSessionPendingDelete(null);
        }}
      >
        <div className="dialog-heading">
          <div className="dialog-icon" aria-hidden="true">
            <Trash2 />
          </div>
          <button
            type="button"
            className="dialog-close"
            onClick={() => setSessionPendingDelete(null)}
            disabled={Boolean(deletingSessionId)}
            aria-label="Đóng hộp thoại"
          >
            <X aria-hidden="true" />
          </button>
        </div>
        <h2 id="delete-dialog-title">Xóa cuộc trò chuyện?</h2>
        <p>
          Cuộc trò chuyện “{sessionPendingDelete?.title}” sẽ bị xóa khỏi trình duyệt
          và bộ nhớ hội thoại của nhân vật. Thao tác này không thể hoàn tác.
        </p>
        <div className="dialog-actions">
          <button
            type="button"
            className="dialog-cancel"
            onClick={() => setSessionPendingDelete(null)}
            disabled={Boolean(deletingSessionId)}
          >
            Hủy
          </button>
          <button
            type="button"
            className="dialog-confirm"
            onClick={() => void confirmSessionDelete()}
            disabled={Boolean(deletingSessionId)}
          >
            {deletingSessionId ? "Đang xóa…" : "Xóa cuộc trò chuyện"}
          </button>
        </div>
      </dialog>
    </div>
  );
}

function createSessionTitle(message: string) {
  const normalized = message.replace(/\s+/g, " ").trim();
  return normalized.length > 34 ? `${normalized.slice(0, 34)}…` : normalized;
}

function formatSessionTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Vừa tạo";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function joinVoiceText(base: string, transcript: string) {
  const normalizedTranscript = transcript.trimStart();
  if (!base) return normalizedTranscript;
  if (!normalizedTranscript) return base;
  return `${base} ${normalizedTranscript}`;
}

export default App;
