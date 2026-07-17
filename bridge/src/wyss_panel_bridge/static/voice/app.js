"use strict";

const elements = {
  hold: document.querySelector("#hold-button"),
  holdLabel: document.querySelector("#hold-label"),
  cancel: document.querySelector("#cancel-button"),
  clear: document.querySelector("#clear-button"),
  send: document.querySelector("#send-button"),
  transcript: document.querySelector("#transcript"),
  status: document.querySelector("#live-status"),
  voiceState: document.querySelector("#voice-state"),
  clientId: document.querySelector("#client-id"),
  token: document.querySelector("#client-token"),
};

const state = {
  enabled: false,
  pressed: false,
  recording: false,
  cancelled: false,
  recorder: null,
  stream: null,
  chunks: [],
  request: null,
  requestPurpose: null,
  transcribed: false,
};

function setStatus(message, error = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle("is-error", error);
}

function credentials() {
  return {
    "X-Wyss-Client": elements.clientId.value.trim(),
    Authorization: `Bearer ${elements.token.value}`,
  };
}

function updateActions() {
  const hasText = elements.transcript.value.trim().length > 0;
  elements.send.disabled = !hasText || state.recording || Boolean(state.request);
  elements.cancel.disabled = !state.recording && state.requestPurpose !== "transcribe";
}

function stopTracks() {
  if (state.stream) {
    for (const track of state.stream.getTracks()) track.stop();
  }
  state.stream = null;
}

function resetCapture() {
  state.recording = false;
  state.recorder = null;
  state.chunks = [];
  elements.hold.classList.remove("is-recording");
  elements.hold.setAttribute("aria-pressed", "false");
  elements.holdLabel.textContent = "Mantené para hablar";
  stopTracks();
  updateActions();
}

function preferredMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg", "audio/mp4"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

async function startCapture() {
  if (!state.enabled || state.recording || state.request) return;
  state.cancelled = false;
  setStatus("Esperando permiso del micrófono.");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
    if (!state.pressed) {
      for (const track of stream.getTracks()) track.stop();
      setStatus("Captura cancelada antes de comenzar.");
      return;
    }
    state.stream = stream;
    state.chunks = [];
    const mimeType = preferredMimeType();
    state.recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    state.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) state.chunks.push(event.data);
    });
    state.recorder.addEventListener("stop", finishCapture, { once: true });
    for (const track of stream.getTracks()) {
      track.addEventListener("ended", () => cancelCapture("El micrófono se interrumpió."), {
        once: true,
      });
    }
    state.recorder.start();
    state.recording = true;
    elements.hold.classList.add("is-recording");
    elements.hold.setAttribute("aria-pressed", "true");
    elements.holdLabel.textContent = "Escuchando mientras sostenés";
    setStatus("Escuchando. Soltá para transcribir.");
    if (navigator.vibrate) navigator.vibrate(10);
    updateActions();
  } catch (error) {
    resetCapture();
    const denied = error && (error.name === "NotAllowedError" || error.name === "SecurityError");
    setStatus(
      denied
        ? "Permiso denegado. Habilitá el micrófono o seguí escribiendo."
        : "No pude iniciar el micrófono. Podés seguir escribiendo.",
      true,
    );
  }
}

function stopCapture() {
  if (state.recording && state.recorder?.state === "recording") state.recorder.stop();
}

function cancelCapture(message = "Captura cancelada. No se envió audio ni texto.") {
  state.cancelled = true;
  state.pressed = false;
  if (state.requestPurpose === "transcribe") state.request?.abort();
  if (state.recording && state.recorder?.state === "recording") {
    state.recorder.stop();
  } else {
    resetCapture();
  }
  setStatus(message);
}

async function finishCapture() {
  const chunks = state.chunks;
  const mimeType = state.recorder?.mimeType || "audio/webm";
  stopTracks();
  state.recording = false;
  if (state.cancelled || chunks.length === 0) {
    resetCapture();
    if (!state.cancelled) setStatus("No se registró audio. Intentá de nuevo.", true);
    return;
  }

  const audio = new Blob(chunks, { type: mimeType });
  state.chunks = [];
  state.request = new AbortController();
  state.requestPurpose = "transcribe";
  elements.holdLabel.textContent = "Transcribiendo";
  setStatus("Transcribiendo en el motor configurado.");
  updateActions();
  try {
    const response = await fetch("/v2/voice/transcribe", {
      method: "POST",
      headers: { ...credentials(), "Content-Type": audio.type },
      body: audio,
      cache: "no-store",
      signal: state.request.signal,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "La transcripción falló");
    elements.transcript.value = result.transcript;
    state.transcribed = true;
    setStatus("Transcripción lista. Revisala antes de enviar.");
    elements.transcript.focus();
  } catch (error) {
    if (error.name !== "AbortError") {
      setStatus(`${error.message}. El texto manual sigue disponible.`, true);
    }
  } finally {
    state.request = null;
    state.requestPurpose = null;
    resetCapture();
  }
}

async function sendIntent() {
  const text = elements.transcript.value.trim();
  if (!text) return;
  const source = elements.clientId.value.trim();
  const requestId = `voice:${crypto.randomUUID()}`;
  const envelope = {
    v: 2,
    type: "assistant.intent",
    message_id: `message:${crypto.randomUUID()}`,
    source,
    payload: {
      request_id: requestId,
      text,
      input: state.transcribed ? "voice" : "text",
    },
  };
  state.request = new AbortController();
  state.requestPurpose = "intent";
  setStatus("Enviando el texto revisado a la sesión compartida.");
  updateActions();
  try {
    const response = await fetch("/v2/voice/intent", {
      method: "POST",
      headers: { ...credentials(), "Content-Type": "application/json" },
      body: JSON.stringify(envelope),
      cache: "no-store",
      signal: state.request.signal,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Wyss rechazó la intención");
    setStatus("Texto enviado. Wyss lo procesa por el mismo funnel de confirmación.");
  } catch (error) {
    if (error.name !== "AbortError") setStatus(error.message, true);
  } finally {
    state.request = null;
    state.requestPurpose = null;
    updateActions();
  }
}

function pressStart(event) {
  if (event.type === "keydown" && !["Enter", " "].includes(event.key)) return;
  if (event.type === "keydown" && event.repeat) return;
  if (event.cancelable) event.preventDefault();
  state.pressed = true;
  void startCapture();
}

function pressEnd(event) {
  if (event.type === "keyup" && !["Enter", " "].includes(event.key)) return;
  if (event.cancelable) event.preventDefault();
  state.pressed = false;
  stopCapture();
}

elements.hold.addEventListener("pointerdown", pressStart);
for (const name of ["pointerup", "lostpointercapture"]) {
  elements.hold.addEventListener(name, pressEnd);
}
elements.hold.addEventListener("pointercancel", () => cancelCapture("Captura interrumpida."));
elements.hold.addEventListener("keydown", pressStart);
elements.hold.addEventListener("keyup", pressEnd);
elements.cancel.addEventListener("click", () => cancelCapture());
elements.clear.addEventListener("click", () => {
  elements.transcript.value = "";
  state.transcribed = false;
  setStatus("Texto borrado. No se envió nada.");
  elements.transcript.focus();
  updateActions();
});
elements.send.addEventListener("click", () => void sendIntent());
elements.transcript.addEventListener("input", updateActions);
elements.clientId.addEventListener("input", (event) => {
  sessionStorage.setItem("wyss-client-id", event.target.value);
});
elements.token.addEventListener("input", (event) => {
  sessionStorage.setItem("wyss-client-token", event.target.value);
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden && (state.recording || state.requestPurpose === "transcribe")) {
    cancelCapture("La app perdió el foco. Captura cancelada.");
  }
});

async function initialize() {
  const defaultId = /Android/i.test(navigator.userAgent) ? "android:owner" : "pc:owner";
  elements.clientId.value = sessionStorage.getItem("wyss-client-id") || defaultId;
  elements.token.value = sessionStorage.getItem("wyss-client-token") || "";
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    elements.voiceState.textContent = "No compatible";
    setStatus("Este navegador no ofrece captura segura. El texto manual sigue disponible.", true);
    updateActions();
    return;
  }
  try {
    const response = await fetch("/v2/voice/config", { cache: "no-store" });
    const config = await response.json();
    state.enabled = Boolean(config.enabled);
    elements.hold.disabled = !state.enabled;
    elements.voiceState.textContent = state.enabled ? "Disponible" : "Desactivada";
    setStatus(
      state.enabled
        ? "Listo. Mantené el control sólo durante el dictado."
        : "Voz desactivada por configuración. El texto manual sigue disponible.",
    );
  } catch {
    elements.voiceState.textContent = "Sin conexión";
    setStatus("No pude comprobar voz. El texto manual sigue disponible.", true);
  }
  updateActions();
}

void initialize();
