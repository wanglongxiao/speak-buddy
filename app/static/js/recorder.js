class VoiceRecorder {
  constructor(onLevel = () => {}) {
    this.onLevel = onLevel;
    this.chunks = [];
    this.rmsTotal = 0;
    this.rmsSamples = 0;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.context = new AudioContext();
    this.source = this.context.createMediaStreamSource(this.stream);
    this.analyser = this.context.createAnalyser();
    this.analyser.fftSize = 1024;
    this.source.connect(this.analyser);
    this.recorder = new MediaRecorder(this.stream);
    this.chunks = [];
    this.startedAt = performance.now();
    this.recorder.ondataavailable = (event) => {
      if (event.data.size) this.chunks.push(event.data);
    };
    this.recorder.start();
    this.sampleLevel();
  }

  sampleLevel() {
    if (!this.recorder || this.recorder.state !== "recording") return;
    const data = new Float32Array(this.analyser.fftSize);
    this.analyser.getFloatTimeDomainData(data);
    const rms = Math.sqrt(data.reduce((sum, value) => sum + value * value, 0) / data.length);
    this.rmsTotal += rms;
    this.rmsSamples += 1;
    this.onLevel(Math.min(100, Math.round(rms * 650)));
    this.animation = requestAnimationFrame(() => this.sampleLevel());
  }

  stop() {
    return new Promise((resolve) => {
      if (!this.recorder || this.recorder.state !== "recording") {
        resolve(null);
        return;
      }
      this.recorder.onstop = () => {
        cancelAnimationFrame(this.animation);
        const mime = this.recorder.mimeType || "audio/webm";
        const blob = new Blob(this.chunks, { type: mime });
        const result = {
          blob,
          rms: this.rmsSamples ? this.rmsTotal / this.rmsSamples : 0,
          durationMs: Math.round(performance.now() - this.startedAt)
        };
        this.stream.getTracks().forEach((track) => track.stop());
        this.context.close();
        resolve(result);
      };
      this.recorder.stop();
    });
  }
}

async function uploadRecording(recording) {
  const form = new FormData();
  const extension = recording.blob.type.includes("mp4") ? "m4a" : "webm";
  form.append("audio", recording.blob, `recording.${extension}`);
  form.append("rms", recording.rms.toString());
  form.append("duration_ms", recording.durationMs.toString());
  const response = await fetch("/api/upload-audio", { method: "POST", body: form });
  if (!response.ok) {
    const pending = JSON.parse(localStorage.getItem("speakbuddy.pendingUploads") || "[]");
    pending.push({ createdAt: Date.now(), durationMs: recording.durationMs });
    localStorage.setItem("speakbuddy.pendingUploads", JSON.stringify(pending.slice(-10)));
    throw new Error("upload failed");
  }
  return response.json();
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

let activeAudio = null;
let activeUtterance = null;
let finishPlayback = null;
const speechAudio = new Audio();
speechAudio.preload = "auto";
speechAudio.playsInline = true;

function silentWavUrl() {
  const sampleRate = 8000;
  const sampleCount = 400;
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);
  const write = (offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };
  write(0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  write(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, sampleCount * 2, true);
  return URL.createObjectURL(new Blob([buffer], { type: "audio/wav" }));
}

function unlockAudio() {
  stopSpeaking();
  const url = silentWavUrl();
  speechAudio.src = url;
  const playback = speechAudio.play();
  return Promise.resolve(playback)
    .then(() => true)
    .catch(() => false)
    .finally(() => URL.revokeObjectURL(url));
}

function stopSpeaking() {
  const audio = activeAudio;
  const utterance = activeUtterance;
  const finish = finishPlayback;
  if (finish) finish(false);
  if (audio) {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }
  if (utterance) {
    speechSynthesis.cancel();
    activeUtterance = null;
  }
}

function playAudio(audio, onStart) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = () => {
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
      audio.removeEventListener("playing", onPlaying);
    };
    const finish = (played) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (activeAudio === audio) activeAudio = null;
      finishPlayback = null;
      resolve(played);
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (activeAudio === audio) activeAudio = null;
      finishPlayback = null;
      reject(error);
    };
    const onEnded = () => finish(true);
    const onError = () => fail(new Error("audio playback failed"));
    const onPlaying = () => onStart?.();
    activeAudio = audio;
    finishPlayback = finish;
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);
    audio.addEventListener("playing", onPlaying, { once: true });
    audio.play().catch(fail);
  });
}

function speakInBrowser(text, speed, onStart) {
  return new Promise((resolve) => {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    activeUtterance = utterance;
    finishPlayback = resolve;
    utterance.lang = "en-US";
    utterance.rate = { slow: 0.85, normal: 1, fast: 1.15 }[speed] || 1;
    const voice = speechSynthesis.getVoices().find((item) => item.lang === "en-US");
    if (voice) utterance.voice = voice;
    const finish = (played) => {
      activeUtterance = null;
      finishPlayback = null;
      resolve(played);
    };
    utterance.onend = () => finish(true);
    utterance.onerror = () => finish(false);
    onStart?.();
    speechSynthesis.speak(utterance);
  });
}

function isAutoplayBlocked(error) {
  const detail = `${error?.name || ""} ${error?.message || ""}`;
  return error?.name === "NotAllowedError"
    || /user (gesture|interaction)|not allowed/i.test(detail);
}

async function speak(text, speed = "normal", options = {}) {
  stopSpeaking();
  try {
    const params = new URLSearchParams({ text, speed });
    if (options.voice) params.set("voice", options.voice);
    speechAudio.src = `/api/tts/stream?${params}`;
    const played = await playAudio(speechAudio, options.onStart);
    if (played) return true;
  } catch (error) {
    if (isAutoplayBlocked(error)) {
      window.dispatchEvent(new CustomEvent("speakbuddy:autoplay-blocked"));
      return false;
    }
    // Browser voice remains an explicit en-US fallback.
    stopSpeaking();
  }
  return speakInBrowser(text, speed, options.onStart);
}

function isSpeaking() {
  return Boolean(activeAudio || activeUtterance);
}

window.speakBuddy = {
  VoiceRecorder,
  isSpeaking,
  postJSON,
  speak,
  stopSpeaking,
  unlockAudio,
  uploadRecording
};
