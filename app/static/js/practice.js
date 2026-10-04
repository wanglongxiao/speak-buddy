(() => {
const {
  StreamingVoiceRecognizer,
  isSpeaking,
  postJSON,
  speak,
  stopSpeaking
} = window.speakBuddy;
const { recordableState, registerPageRecorder, scrollToCurrentQuestion } =
  window.speakBuddyPage;
const I = window.i18n;

window.practiceApp = (topicId, questions, speed) => ({
  ...recordableState(I.microphone_error, "turn"),
  topicId,
  questions,
  speed,
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
  speak(text, options = {}) {
    return speak(text, this.speed, options);
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
      onSpeechStart: () => {
        if (isSpeaking()) stopSpeaking();
      },
      onTranscript: (text) => {
        this.transcript = text;
        if (text && isSpeaking()) stopSpeaking();
      },
      onFinal: (text) => {
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
      this.askQuestion();
    }
  },
  async listenForReply() {
    if (this.complete) return false;
    const provider = await this.voice.start();
    this.voiceMode = Boolean(provider);
    return this.voiceMode;
  },
  async askQuestion() {
    this.audioBlocked = false;
    this.voiceStatus = I.buddy_speaking;
    let listening = Promise.resolve(false);
    const played = await this.speak(this.question, {
      onStart: () => {
        listening = this.listenForReply();
      }
    });
    if (!played) {
      this.audioBlocked = true;
      this.voiceStatus = "";
      return false;
    }
    await listening;
    if (this.voiceMode && this.recording) this.voiceStatus = I.listening;
    return true;
  },
  async start() {
    if (this.busy || this.complete) return false;
    this.result = null;
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
      await this.speak(this.result.praise);
      await this.completeQuest();
      return;
    }
    this.turn += 1;
    this.question = this.questions.length > 1
      ? this.questions[this.turn - 1]
      : this.result.follow_up_question;
    scrollToCurrentQuestion();
    this.voiceStatus = I.buddy_speaking;
    const playback = this.speak(`${this.result.praise} ${this.question}`);
    const listening = this.listenForReply();
    await playback;
    await listening;
    if (this.voiceMode && this.recording) this.voiceStatus = I.listening;
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
    stopSpeaking();
    await this.voice.shutdown();
    await postJSON("/api/quest/end", { topic_id: this.topicId });
    location.href = "/";
  },
  destroy() {
    stopSpeaking();
    this.voice.shutdown();
  }
});
})();
