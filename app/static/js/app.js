(() => {
const { VoiceRecorder, postJSON, speak, uploadRecording } = window.speakBuddy;
const I = window.i18n;
function registerPageRecorder(component) {
  window.pageRecorder = {
    start: () => component.start(),
    stop: () => component.stop()
  };
}

function scrollToCurrentQuestion() {
  requestAnimationFrame(() => {
    document.querySelector("[data-current-question]")?.scrollIntoView({
      behavior: "smooth",
      block: "center"
    });
  });
}

function recordableState(target, context) {
  return {
    recording: false,
    level: 0,
    status: "",
    async beginRecording() {
      this.recorder = new VoiceRecorder((value) => {
        this.level = value;
        window.dispatchEvent(new CustomEvent("record-level", { detail: value }));
      });
      try {
        await this.recorder.start();
        this.recording = true;
        return true;
      } catch (_) {
        this.status = target;
        return false;
      }
    },
    async finishRecording() {
      if (!this.recording) return null;
      this.recording = false;
      const recording = await this.recorder.stop();
      if (!recording) return null;
      const upload = await uploadRecording(recording);
      await postJSON("/api/loud/record", {
        audio_key: upload.audio_key,
        context: typeof context === "function" ? context() : context,
        rms: upload.rms,
        duration_ms: upload.duration_ms
      }).then((result) => {
        const meter = document.getElementById("global-loud");
        if (meter) meter.textContent = `${result.total_seconds}s`;
        if (result.total_seconds >= 300) {
          document.getElementById("loud-legend")?.classList.remove("hidden");
          if (navigator.vibrate) navigator.vibrate(150);
        }
      });
      return { recording, upload };
    }
  };
}
window.speakBuddyPage = { recordableState, registerPageRecorder, scrollToCurrentQuestion };

window.warmupApp = () => ({
  ...recordableState(
    I.microphone_error,
    () => new URLSearchParams(location.search).has("quest") ? "warmup" : "shoutout"
  ),
  lines: [
    "Hi Buddy, let's practice English together."
  ],
  readAloudLines: I.read_aloud_lines_by_difficulty?.[window.userDifficulty]
    || I.read_aloud_lines,
  index: 0,
  count: 0,
  quiet: false,
  completed: false,
  questMode: new URLSearchParams(location.search).has("quest"),
  init() {
    registerPageRecorder(this);
    if (!this.questMode) this.lines = this.readAloudLines;
    speak(this.lines[0]);
  },
  speak,
  async start() {
    this.quiet = false;
    this.status = "";
    return await this.beginRecording();
  },
  async stop() {
    try {
      const result = await this.finishRecording();
      if (!result) return;
      this.quiet = result.upload.rms > 0 && result.upload.rms < 0.035;
      if (this.quiet) return;
      this.count += 1;
      this.status = I.voice_success;
      if (this.questMode && this.index === this.lines.length - 1) {
        this.completed = true;
        localStorage.setItem("speakbuddy.warmupDate", new Date().toDateString());
      } else {
        this.index = (this.index + 1) % this.lines.length;
        speak(this.lines[this.index]);
      }
    } catch (_) {
      this.status = I.try_again;
    }
  }
});

window.topicCreator = () => ({
  ...recordableState(I.microphone_error, "turn"),
  topic: null,
  init() {
    registerPageRecorder(this);
  },
  async start() {
    return await this.beginRecording();
  },
  async stop() {
    try {
      const saved = await this.finishRecording();
      if (!saved) return;
      const asr = await postJSON("/api/asr", {
        audio_key: saved.upload.audio_key,
        lang: "en"
      });
      this.topic = await postJSON("/api/topics/create-from-voice", {
        raw_text: asr.transcript
      });
      speak(this.topic.starter_question);
    } catch (_) {
      this.status = I.try_again;
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons({ attrs: { "stroke-width": 2.4 } });
  const refreshForm = document.getElementById("practice-refresh-form");
  const refreshOverlay = document.getElementById("practice-refresh-overlay");
  refreshForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (refreshForm.dataset.submitting === "true") return;
    refreshForm.dataset.submitting = "true";
    const refreshButton = refreshForm.querySelector("button");
    refreshButton?.setAttribute("disabled", "");
    if (refreshOverlay) {
      refreshOverlay.hidden = false;
      refreshOverlay.setAttribute("aria-hidden", "false");
    }
    try {
      const response = await fetch(refreshForm.action, {
        method: "POST",
        credentials: "same-origin"
      });
      if (!response.ok) throw new Error("Practice refresh failed");
      window.location.assign(response.url);
    } catch (_) {
      refreshForm.dataset.submitting = "false";
      refreshButton?.removeAttribute("disabled");
      if (refreshOverlay) {
        refreshOverlay.hidden = true;
        refreshOverlay.setAttribute("aria-hidden", "true");
      }
    }
  });
});

window.addEventListener("pageshow", () => {
  const refreshForm = document.getElementById("practice-refresh-form");
  const refreshOverlay = document.getElementById("practice-refresh-overlay");
  if (refreshForm) refreshForm.dataset.submitting = "false";
  refreshForm?.querySelector("button")?.removeAttribute("disabled");
  if (refreshOverlay) {
    refreshOverlay.hidden = true;
    refreshOverlay.setAttribute("aria-hidden", "true");
  }
});
})();
