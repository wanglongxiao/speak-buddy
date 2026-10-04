(() => {
class StreamingVoiceRecognizer {
  constructor(callbacks = {}) {
    this.callbacks = callbacks;
    this.backendUnavailable = false;
    this.active = false;
    this.finalized = false;
    this.transcript = "";
  }

  async start() {
    await this.cancel();
    this.active = true;
    this.finalized = false;
    this.transcript = "";
    if (!this.backendUnavailable && window.WebSocket && window.AudioContext) {
      try {
        await this.startSeedStream();
        return "seed";
      } catch (_) {
        this.backendUnavailable = true;
        this.socket?.close();
        this.socket = null;
        await this.releaseMedia();
      }
    }
    if (this.startBrowserRecognition()) return "browser";
    this.active = false;
    this.callbacks.onUnavailable?.();
    return "";
  }

  async startSeedStream() {
    if (!this.mediaStream || this.mediaStream.getTracks().every((track) => track.readyState === "ended")) {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
    }
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${scheme}//${location.host}/api/asr/stream`);
    socket.binaryType = "arraybuffer";
    this.socket = socket;

    await new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error("ASR timeout")), 5000);
      socket.onerror = () => {
        window.clearTimeout(timeout);
        reject(new Error("ASR connection failed"));
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "ready") {
          window.clearTimeout(timeout);
          this.attachPCMStream();
          this.callbacks.onReady?.("seed");
          socket.onclose = () => {
            if (this.active && !this.finalized && !this.stopping) {
              this.active = false;
              this.callbacks.onUnavailable?.();
            }
          };
          resolve();
          return;
        }
        if (message.type === "unavailable" || message.type === "error") {
          window.clearTimeout(timeout);
          reject(new Error(message.detail || "ASR unavailable"));
          return;
        }
        this.handleTranscript(message);
      };
    });
  }

  attachPCMStream() {
    this.audioContext = new AudioContext();
    this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.silentGain = this.audioContext.createGain();
    this.silentGain.gain.value = 0;
    this.processor.onaudioprocess = (event) => {
      if (!this.active || this.socket?.readyState !== WebSocket.OPEN) return;
      const input = event.inputBuffer.getChannelData(0);
      const rms = Math.sqrt(
        input.reduce((sum, value) => sum + value * value, 0) / input.length
      );
      this.callbacks.onLevel?.(Math.min(100, Math.round(rms * 650)));
      if (rms > 0.022) {
        if (!this.heardSpeech) this.callbacks.onSpeechStart?.();
        this.heardSpeech = true;
        this.lastVoiceAt = performance.now();
      } else if (
        this.heardSpeech
        && performance.now() - this.lastVoiceAt > 700
        && !this.stopping
      ) {
        this.stop();
      }
      this.socket.send(this.toPCM16(input, this.audioContext.sampleRate));
    };
    this.heardSpeech = false;
    this.stopping = false;
    this.source.connect(this.processor);
    this.processor.connect(this.silentGain);
    this.silentGain.connect(this.audioContext.destination);
  }

  toPCM16(input, sourceRate) {
    const ratio = sourceRate / 16000;
    const output = new Int16Array(Math.floor(input.length / ratio));
    for (let index = 0; index < output.length; index += 1) {
      const start = Math.floor(index * ratio);
      const end = Math.max(start + 1, Math.floor((index + 1) * ratio));
      let sum = 0;
      for (let source = start; source < end && source < input.length; source += 1) {
        sum += input[source];
      }
      const sample = Math.max(-1, Math.min(1, sum / (end - start)));
      output[index] = sample < 0 ? sample * 32768 : sample * 32767;
    }
    return output.buffer;
  }

  startBrowserRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return false;
    const recognition = new Recognition();
    this.recognition = recognition;
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onstart = () => this.callbacks.onReady?.("browser");
    recognition.onspeechstart = () => this.callbacks.onSpeechStart?.();
    recognition.onresult = (event) => {
      let text = "";
      let final = false;
      for (let index = 0; index < event.results.length; index += 1) {
        text += event.results[index][0].transcript;
        final ||= event.results[index].isFinal;
      }
      this.handleTranscript({ type: "transcript", text: text.trim(), final });
    };
    recognition.onerror = () => this.callbacks.onUnavailable?.();
    recognition.onend = () => {
      if (this.active && this.transcript) this.finish(this.transcript);
    };
    try {
      recognition.start();
      return true;
    } catch (_) {
      return false;
    }
  }

  handleTranscript(message) {
    if (message.type !== "transcript" || !message.text) return;
    this.transcript = message.text.trim();
    this.callbacks.onTranscript?.(this.transcript, Boolean(message.final));
    if (message.final) this.finish(this.transcript);
  }

  finish(text) {
    if (this.finalized) return;
    this.finalized = true;
    this.active = false;
    this.disconnectCapture();
    this.callbacks.onFinal?.(text);
    this.socket?.close();
  }

  async stop() {
    if (!this.active || this.stopping) return;
    this.stopping = true;
    this.disconnectCapture();
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "stop" }));
      return;
    }
    this.recognition?.stop();
  }

  async cancel() {
    this.active = false;
    this.finalized = true;
    this.disconnectCapture();
    this.recognition?.abort();
    this.recognition = null;
    this.socket?.close();
    this.socket = null;
  }

  disconnectCapture() {
    if (this.processor) this.processor.onaudioprocess = null;
    this.source?.disconnect();
    this.processor?.disconnect();
    this.silentGain?.disconnect();
    this.audioContext?.close();
    this.source = null;
    this.processor = null;
    this.silentGain = null;
    this.audioContext = null;
  }

  async releaseMedia() {
    this.disconnectCapture();
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.mediaStream = null;
  }

  async shutdown() {
    await this.cancel();
    await this.releaseMedia();
  }
}

window.speakBuddy.StreamingVoiceRecognizer = StreamingVoiceRecognizer;
})();
