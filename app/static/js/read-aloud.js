(() => {
const { VoiceRecorder, postJSON, speak, uploadRecording } = window.speakBuddy;
const I = window.i18n;

async function recordLoud(upload, context) {
  const result = await postJSON("/api/loud/record", {
    audio_key: upload.audio_key,
    context,
    rms: upload.rms,
    duration_ms: upload.duration_ms
  });
  const meter = document.getElementById("global-loud");
  if (meter) meter.textContent = `${result.total_seconds}s`;
  return result;
}

window.warmupApp = () => ({
  recording: false,
  busy: false,
  level: 0,
  status: "",
  evaluation: null,
  quiet: false,
  index: 0,
  count: 0,
  attempts: [],
  completed: false,
  awaitingNext: false,
  questMode: new URLSearchParams(location.search).has("quest"),
  warmupLines: [
    "Hi Buddy!",
    "I'm ready to speak English today!",
    "Let's make today AWESOME!"
  ],
  get lines() {
    return this.questMode
      ? this.warmupLines
      : (window.dailyReadAloud?.length ? window.dailyReadAloud : I.read_aloud_lines);
  },
  init() {
    window.pageRecorder = {
      start: () => this.start(),
      stop: () => this.stop()
    };
    speak(this.lines[this.index]);
  },
  speak,
  async start() {
    if (this.busy || this.awaitingNext) return false;
    this.quiet = false;
    this.status = "";
    this.evaluation = null;
    this.recorder = new VoiceRecorder((value) => {
      this.level = value;
      window.dispatchEvent(new CustomEvent("record-level", { detail: value }));
    });
    try {
      await this.recorder.start();
      this.recording = true;
      return true;
    } catch (_) {
      this.status = I.microphone_error;
      return false;
    }
  },
  async stop() {
    if (!this.recording) return;
    this.recording = false;
    this.busy = true;
    try {
      const recording = await this.recorder.stop();
      if (!recording) return;
      const upload = await uploadRecording(recording);
      const context = this.questMode ? "warmup" : "shoutout";
      await recordLoud(upload, context);
      this.quiet = upload.rms > 0 && upload.rms < 0.035;
      if (this.quiet) return;
      const asr = await postJSON("/api/asr", {
        audio_key: upload.audio_key,
        lang: "en"
      });
      this.count += 1;
      if (this.questMode) {
        this.evaluation = await postJSON("/api/evaluate-task", {
          task_type: "warmup",
          reference_text: this.lines[this.index],
          transcript: asr.transcript,
          asr_confidence: asr.confidence
        });
        this.awaitingNext = true;
      } else {
        this.attempts.push({
          reference_text: this.lines[this.index],
          transcript: asr.transcript,
          asr_confidence: asr.confidence
        });
        if (this.attempts.length === 10) {
          this.evaluation = await postJSON("/api/evaluate-read-aloud-group", {
            attempts: this.attempts
          });
          this.awaitingNext = true;
        } else {
          this.index += 1;
          speak(this.lines[this.index]);
        }
      }
      this.status = I.voice_success;
    } catch (_) {
      this.status = I.try_again;
    } finally {
      this.busy = false;
      lucide.createIcons();
    }
  },
  nextLine() {
    this.awaitingNext = false;
    this.evaluation = null;
    this.status = "";
    this.attempts = [];
    if (this.index === this.lines.length - 1) {
      this.completed = true;
      localStorage.setItem("speakbuddy.warmupDate", new Date().toDateString());
      return;
    }
    this.index += 1;
    speak(this.lines[this.index]);
  }
});
})();
