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

async function speak(text, speed = "normal") {
  try {
    const result = await postJSON("/api/tts", {
      text,
      speed
    });
    if (result.url) {
      await new Audio(result.url).play();
      return;
    }
  } catch (_) {
    // Browser voice remains an explicit en-US fallback.
  }
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = { slow: 0.85, normal: 1, fast: 1.15 }[speed] || 1;
  const voice = speechSynthesis.getVoices().find((item) => item.lang === "en-US");
  if (voice) utterance.voice = voice;
  speechSynthesis.speak(utterance);
}

window.speakBuddy = { VoiceRecorder, postJSON, speak, uploadRecording };
