(() => {
  const { VoiceRecorder, postJSON, uploadRecording } = window.speakBuddy;
  const I = window.i18n;

  async function saveFreeRecording(recording) {
    const upload = await uploadRecording(recording);
    const result = await postJSON("/api/loud/record", {
      audio_key: upload.audio_key,
      context: "shoutout",
      rms: upload.rms,
      duration_ms: upload.duration_ms
    });
    const meter = document.getElementById("global-loud");
    if (meter) meter.textContent = `${result.total_seconds}s`;
    return result;
  }

  window.globalRecorder = () => ({
    recording: false,
    starting: false,
    releasePending: false,
    level: 0,
    status: "",
    init() {
      window.addEventListener("record-level", (event) => {
        this.level = event.detail;
      });
    },
    async start() {
      if (this.recording || this.starting) return;
      this.starting = true;
      this.releasePending = false;
      this.status = "";
      if (window.pageRecorder) {
        const started = await window.pageRecorder.start();
        this.starting = false;
        this.recording = started !== false;
        if (this.releasePending && this.recording) await this.stop();
        return;
      }
      this.recorder = new VoiceRecorder((value) => {
        this.level = value;
      });
      try {
        await this.recorder.start();
        this.starting = false;
        this.recording = true;
        if (this.releasePending) await this.stop();
      } catch (_) {
        this.starting = false;
        this.status = I.microphone_error;
      }
    },
    async stop() {
      if (this.starting) {
        this.releasePending = true;
        return;
      }
      if (!this.recording) return;
      this.recording = false;
      this.level = 0;
      try {
        if (window.pageRecorder) {
          await window.pageRecorder.stop();
          return;
        }
        const recording = await this.recorder.stop();
        if (!recording) return;
        await saveFreeRecording(recording);
        this.status = I.voice_success;
      } catch (_) {
        this.status = I.try_again;
      }
    }
  });
})();
