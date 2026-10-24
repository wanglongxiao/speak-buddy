(() => {
const {
  StreamingVoiceRecognizer,
  isSpeaking,
  postJSON,
  speak,
  stopSpeaking,
  unlockAudio
} = window.speakBuddy;
const { recordableState, registerPageRecorder, scrollToCurrentQuestion } =
  window.speakBuddyPage;
const I = window.i18n;

window.practiceApp = (topicId, questions, speed, buddyVoice) => ({
  ...recordableState(I.microphone_error, "turn"),
  topicId,
  questions,
  speed,
  buddyVoice,
  playbackTurn: 0,
  destroyed: false,
  turn: 1,
  total: questions.length > 1 ? questions.length : 5,
  question: questions[0],
  transcript: "",
  result: null,
  finalEvaluation: null,
  busy: false,
  complete: false,
  xp: 0,
  history: [],
  voiceMode: false,
  voiceStatus: "",
  audioBlocked: false,
  async speak(text, options = {}) {
    const turn = ++this.playbackTurn;
    const listen = options.listen ?? this.voiceMode;
    stopSpeaking();
    await this.voice.cancel();
    this.recording = false;
    this.level = 0;
    // Never delay the first prompt for microphone permission.
    // Later turns retain the microphone and AudioContext created after that prompt.
    if (this.destroyed || turn !== this.playbackTurn) return false;
    this.voiceStatus = I.buddy_speaking;
    const played = await speak(text, this.speed, { ...options, voice: this.buddyVoice });
    if (this.destroyed || turn !== this.playbackTurn) return false;
    this.audioBlocked = !played;
    this.voiceStatus = "";
    // Open recognition only after the entire prompt, avoiding speaker echo.
    if (played && listen) await this.listenForReply();
    return played;
  },
  init() {
    registerPageRecorder(this);
    this.voice = new StreamingVoiceRecognizer({
      onReady: () => {
        this.recording = true;
        this.voiceStatus = I.listening;
      },
      onLevel: (value) => {
        this.level = value;
      },
      onTranscript: (text) => {
        if (isSpeaking() || this.destroyed) return;
        this.transcript = text;
      },
      onFinal: (text) => {
        if (this.destroyed || isSpeaking()) return;
        this.recording = false;
        this.level = 0;
        if (text) this.processTranscript(text, 0.86);
      },
      onUnavailable: () => {
        this.voiceMode = false;
        this.recording = false;
        this.voiceStatus = I.streaming_unavailable;
      }
    });
    if (new URLSearchParams(window.location.search).get("autoplay") === "1") {
      this.askQuestion(false);
    }
  },
  async listenForReply() {
    if (this.complete) return false;
    const provider = await this.voice.start();
    this.voiceMode = Boolean(provider);
    return this.voiceMode;
  },
  async askQuestion(unlock = true) {
    if (unlock) unlockAudio();
    this.audioBlocked = false;
    return await this.speak(this.question, { listen: true });
  },
  async start() {
    if (this.busy || this.complete) return false;
    if (this.recording) return true;
    stopSpeaking();
    this.playbackTurn += 1;
    this.result = null;
    await this.voice.cancel();
    if (this.voiceMode) {
      if (this.recording) return true;
      return await this.listenForReply();
    }
    return await this.beginRecording();
  },
  async stop() {
    if (!this.recording) return;
    if (this.voiceMode) {
      await this.voice.stop();
      return;
    }
    this.busy = true;
    try {
      const saved = await this.finishRecording();
      if (!saved) {
        this.busy = false;
        return;
      }
      const asr = await postJSON("/api/asr", {
        audio_key: saved.upload.audio_key,
        lang: "en"
      });
      this.busy = false;
      await this.processTranscript(asr.transcript, asr.confidence);
    } catch (_) {
      this.status = I.try_again;
      this.busy = false;
    }
  },
  async processTranscript(transcript, confidence) {
    if (this.busy || this.complete || !transcript) return;
    this.busy = true;
    this.result = null;
    this.transcript = transcript;
    this.voiceStatus = I.thinking;
    try {
      this.result = await postJSON("/api/coach", {
        topic_id: this.topicId,
        question: this.question,
        transcript: this.transcript,
        history: this.history,
        user_profile: {},
        asr_confidence: confidence
      });
      this.xp += this.result.xp_earned;
      this.history.push({ role: "user", content: this.transcript });
      this.history.push({ role: "assistant", content: this.result.follow_up_question });
      this.busy = false;
      await this.continueConversation();
    } catch (_) {
      this.status = I.try_again;
      this.voiceStatus = "";
    } finally {
      this.busy = false;
      lucide.createIcons();
    }
  },
  async continueConversation() {
    if (this.turn >= this.total) {
      this.voiceStatus = I.buddy_speaking;
      await this.speak(this.result.praise, { listen: false });
      await this.completeQuest();
      return;
    }
    this.turn += 1;
    this.question = this.questions.length > 1
      ? this.questions[this.turn - 1]
      : this.result.follow_up_question;
    scrollToCurrentQuestion();
    this.voiceStatus = I.buddy_speaking;
    await this.speak(`${this.result.praise} ${this.question}`, { listen: true });
  },
  echo() {
    this.speak(this.result.ideal_rephrase);
  },
  async next() {
    if (this.turn >= this.total) {
      await this.completeQuest();
      return;
    }
    this.turn += 1;
    this.question = this.questions.length > 1
      ? this.questions[this.turn - 1]
      : this.result.follow_up_question;
    this.result = null;
    this.transcript = "";
    scrollToCurrentQuestion();
    this.speak(this.question);
  },
  async completeQuest() {
    await this.voice.shutdown();
    const reward = await postJSON("/api/quest/complete", {
      topic_id: this.topicId
    });
    this.xp += reward.xp;
    this.finalEvaluation = reward.evaluation;
    this.complete = true;
    this.recording = false;
    this.voiceStatus = "";
    if (navigator.vibrate) navigator.vibrate(150);
  },
  async endEarly() {
    this.destroyed = true;
    this.playbackTurn += 1;
    stopSpeaking();
    await this.voice.shutdown();
    await postJSON("/api/quest/end", { topic_id: this.topicId });
    location.href = "/";
  },
  destroy() {
    this.destroyed = true;
    this.playbackTurn += 1;
    stopSpeaking();
    this.voice.shutdown();
  }
});
})();
