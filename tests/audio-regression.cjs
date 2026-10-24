const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { test } = require("node:test");

function environment() {
  const events = [], requests = [], audio = [];
  let fetchImpl = async () => ({ ok: true, json: async () => ({ url: "/retry.mp3" }) });
  class Audio extends EventTarget {
    constructor() { super(); audio.push(this); }
    play() { this.dispatchEvent(new Event("playing")); return Promise.resolve(); }
    pause() {}
    load() {}
    removeAttribute() {}
  }
  const window = {
    userBuddyVoice: "selected-voice",
    dispatchEvent: (event) => events.push(event.type),
    speechSynthesis: { speak() { throw new Error("System voice must never be used"); } }
  };
  const context = vm.createContext({
    window, Audio, URL, Blob, ArrayBuffer, DataView, URLSearchParams,
    CustomEvent: class { constructor(type) { this.type = type; } },
    fetch: (...args) => { requests.push(args); return fetchImpl(...args); }
  });
  vm.runInContext(fs.readFileSync("app/static/js/recorder.js", "utf8"), context);
  return { context, window, audio, events, requests, setFetch: (value) => { fetchImpl = value; } };
}
const tick = () => new Promise(setImmediate);

test("interrupting playback returns false without fallback or retry", async () => {
  const e = environment();
  const pending = e.window.speakBuddy.speak("First");
  await tick();
  e.window.speakBuddy.stopSpeaking();
  assert.equal(await pending, false);
  assert.equal(e.requests.length, 0);
});

test("five turns use the selected voice and finish complete audio", async () => {
  const e = environment();
  for (let index = 0; index < 5; index++) {
    const pending = e.window.speakBuddy.speak(`Turn ${index}`);
    await tick();
    assert.match(e.audio[0].src, /voice=selected-voice/);
    e.audio[0].dispatchEvent(new Event("ended"));
    assert.equal(await pending, true);
  }
});

test("media failure retries buffered audio using identical voice", async () => {
  const e = environment();
  const pending = e.window.speakBuddy.speak("Hello", "slow", { voice: "pinned-voice" });
  await tick();
  e.audio[0].dispatchEvent(new Event("error"));
  await tick();
  assert.deepEqual(JSON.parse(e.requests[0][1].body), {
    text: "Hello", speed: "slow", voice: "pinned-voice"
  });
  assert.equal(e.audio[0].src, "/retry.mp3");
  e.audio[0].dispatchEvent(new Event("ended"));
  assert.equal(await pending, true);
});

test("stale buffered response cannot overwrite a newer utterance", async () => {
  const e = environment();
  let resolve;
  e.setFetch(() => new Promise((r) => { resolve = r; }));
  const old = e.window.speakBuddy.speak("Old");
  await tick();
  e.audio[0].dispatchEvent(new Event("error"));
  await tick();
  const current = e.window.speakBuddy.speak("New");
  await tick();
  resolve({ ok: true, json: async () => ({ url: "/old.mp3" }) });
  assert.equal(await old, false);
  assert.match(e.audio[0].src, /text=New/);
  e.audio[0].dispatchEvent(new Event("ended"));
  assert.equal(await current, true);
});

test("autoplay denial is shown without system speech", async () => {
  const e = environment();
  e.audio[0].play = () => Promise.reject(Object.assign(new Error("Gesture required"), { name: "NotAllowedError" }));
  assert.equal(await e.window.speakBuddy.speak("Hello"), false);
  assert.deepEqual(e.events, ["speakbuddy:autoplay-blocked"]);
  assert.equal(e.requests.length, 0);
});

test("navigation unlock completes before the first prompt is assigned", async () => {
  const e = environment();
  let release;
  e.audio[0].play = () => new Promise((resolve) => { release = resolve; });
  e.window.speakBuddy.unlockAudio();
  const silent = e.audio[0].src;
  const pending = e.window.speakBuddy.speak("First");
  await tick();
  assert.equal(e.audio[0].src, silent);
  e.audio[0].play = () => Promise.resolve();
  release();
  await tick();
  assert.match(e.audio[0].src, /text=First/);
  e.audio[0].dispatchEvent(new Event("ended"));
  assert.equal(await pending, true);
});

test("quest plays without waiting for microphone permission and listens after ended for five turns", async () => {
  const e = environment();
  const order = [];
  e.window.i18n = { buddy_speaking: "Speaking", listening: "Listening" };
  e.window.speakBuddyPage = {
    recordableState: () => ({}), registerPageRecorder() {}, scrollToCurrentQuestion() {}
  };
  e.window.speakBuddy.StreamingVoiceRecognizer = class {
    constructor(callbacks) { this.callbacks = callbacks; }
    async cancel() { order.push("cancel"); }
    async prepare() { throw new Error("Permission must not delay the prompt"); }
    async start() { order.push("listen"); this.callbacks.onReady(); return "seed"; }
    async shutdown() {}
  };
  e.context.location = e.window.location = { search: "" };
  vm.runInContext(fs.readFileSync("app/static/js/practice.js", "utf8"), e.context);
  const quest = e.window.practiceApp(1, ["Question"], "normal", "quest-voice");
  quest.init();
  for (let index = 0; index < 5; index++) {
    order.length = 0;
    const pending = quest.speak(`Question ${index}`, { listen: true });
    await tick();
    assert.deepEqual(order, ["cancel"]);
    assert.match(e.audio[0].src, /voice=quest-voice/);
    assert.equal(quest.recording, false);
    e.audio[0].dispatchEvent(new Event("ended"));
    assert.equal(await pending, true);
    assert.deepEqual(order, ["cancel", "listen"]);
    assert.equal(quest.recording, true);
  }
});

test("recognizer reuses microphone/context across turns and ignores cancelled transcripts", async () => {
  const e = environment();
  let acquired = 0, contexts = 0, finals = 0, stopped = 0;
  const track = { readyState: "live", stop() { stopped++; } };
  const node = () => ({ connect() {}, disconnect() {}, gain: {} });
  class AudioContext {
    constructor() { contexts++; this.state = "suspended"; }
    async resume() { this.state = "running"; }
    async close() { this.state = "closed"; }
    createMediaStreamSource() { return node(); }
    createScriptProcessor() { return node(); }
    createGain() { return node(); }
  }
  e.context.AudioContext = AudioContext;
  e.window.AudioContext = AudioContext;
  const sockets = [];
  class WebSocket {
    static OPEN = 1;
    constructor() {
      sockets.push(this);
      this.readyState = 1;
      queueMicrotask(() => this.onmessage?.({ data: '{"type":"ready"}' }));
    }
    close() { this.readyState = 3; this.onclose?.(); }
  }
  e.context.WebSocket = e.window.WebSocket = WebSocket;
  e.context.location = { protocol: "https:", host: "example.test" };
  e.window.setTimeout = setTimeout;
  e.window.clearTimeout = clearTimeout;
  e.context.navigator = { mediaDevices: { async getUserMedia() {
    acquired++; return { getTracks: () => [track] };
  } } };
  vm.runInContext(fs.readFileSync("app/static/js/streaming-voice.js", "utf8"), e.context);
  const voice = new e.window.speakBuddy.StreamingVoiceRecognizer({ onFinal() { finals++; } });
  for (let index = 0; index < 5; index++) {
    assert.equal(await voice.start(), "seed");
    const socket = sockets.at(-1);
    socket.onmessage({ data: JSON.stringify({ type: "transcript", text: `Reply ${index}`, final: true }) });
    assert.equal(finals, index + 1);
    await voice.cancel();
    socket.onmessage({ data: '{"type":"transcript","text":"stale","final":true}' });
    assert.equal(finals, index + 1);
  }
  assert.equal(acquired, 1);
  assert.equal(contexts, 1);
  voice.handleTranscript({ type: "transcript", text: "stale", final: true });
  assert.equal(finals, 5);
  await voice.shutdown();
  assert.equal(stopped, 1);
  assert.equal(voice.audioContext, null);
});
