(() => {
const { postJSON, speak } = window.speakBuddy;
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
  speak(text) {
    return speak(text, this.speed);
  },
  init() {
    registerPageRecorder(this);
  },
  async start() {
    if (this.busy || this.complete) return false;
    this.result = null;
    return await this.beginRecording();
  },
  async stop() {
    if (!this.recording) return;
    this.busy = true;
    try {
      const saved = await this.finishRecording();
      if (!saved) return;
      const asr = await postJSON("/api/asr", {
        audio_key: saved.upload.audio_key,
        lang: "en"
      });
      this.transcript = asr.transcript;
      this.result = await postJSON("/api/coach", {
        topic_id: this.topicId,
        question: this.question,
        transcript: this.transcript,
        history: this.history,
        user_profile: {},
        asr_confidence: asr.confidence
      });
      this.xp += this.result.xp_earned;
      this.history.push({ role: "user", content: this.transcript });
      this.history.push({ role: "assistant", content: this.result.follow_up_question });
      this.speak(this.result.praise);
    } catch (_) {
      this.status = I.try_again;
    } finally {
      this.busy = false;
      lucide.createIcons();
    }
  },
  echo() {
    this.speak(this.result.ideal_rephrase);
  },
  async next() {
    if (this.turn >= this.total) {
      const reward = await postJSON("/api/quest/complete", {
        topic_id: this.topicId
      });
      this.xp += reward.xp;
      this.finalEvaluation = reward.evaluation;
      this.complete = true;
      if (navigator.vibrate) navigator.vibrate(150);
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
  async endEarly() {
    await postJSON("/api/quest/end", { topic_id: this.topicId });
    location.href = "/";
  }
});
})();
