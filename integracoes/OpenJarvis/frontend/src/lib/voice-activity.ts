export class VoiceActivity {
  private first: number | null = null;
  private last: number | null = null;
  private confirmed = false;
  constructor(private threshold = 0.02, private silenceMs = 1200, private minVoiceMs = 250) {}
  update(level: number, now: number): boolean {
    if (level >= this.threshold) {
      if (this.first === null) this.first = now;
      this.last = now;
      if (now - this.first >= this.minVoiceMs) this.confirmed = true;
    }
    if (this.last !== null && now - this.last >= this.silenceMs) {
      if (this.confirmed) return true;
      this.first = null;
      this.last = null;
    }
    return false;
  }
}

/** Captures one utterance, closing the microphone before processing begins. */
export async function listenOnce(signal: AbortSignal): Promise<Blob> {
  if (signal.aborted) throw new DOMException('Cancelled', 'AbortError');
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  if (signal.aborted) {
    stream.getTracks().forEach((track) => track.stop());
    throw new DOMException('Cancelled', 'AbortError');
  }
  let context: AudioContext;
  try { context = new AudioContext(); } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    throw error;
  }
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  context.createMediaStreamSource(stream).connect(analyser);
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];
  const samples = new Float32Array(analyser.fftSize);
  const vad = new VoiceActivity();
  return new Promise<Blob>((resolve, reject) => {
    let timer: ReturnType<typeof setInterval> | undefined;
    let settled = false;
    const cleanup = () => {
      if (timer) clearInterval(timer);
      signal.removeEventListener('abort', cancel);
      stream.getTracks().forEach((track) => track.stop());
      void context.close();
    };
    const cancel = () => {
      if (settled) return;
      settled = true;
      if (recorder.state !== 'inactive') recorder.stop();
      cleanup();
      reject(new DOMException('Cancelled', 'AbortError'));
    };
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => { if (!settled) { settled = true; cleanup(); reject(new Error('Falha na gravação')); } };
    recorder.onstop = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }));
    };
    signal.addEventListener('abort', cancel, { once: true });
    recorder.start();
    const startedAt = performance.now();
    timer = setInterval(() => {
      if (performance.now() - startedAt > 60000) {
        if (settled) return;
        settled = true;
        if (recorder.state !== 'inactive') recorder.stop();
        cleanup();
        reject(new Error('Nenhuma fala concluída em 60 segundos. Inicie a conversa novamente.'));
        return;
      }
      analyser.getFloatTimeDomainData(samples);
      const rms = Math.sqrt(samples.reduce((sum, sample) => sum + sample * sample, 0) / samples.length);
      if (vad.update(rms, performance.now()) && recorder.state === 'recording') recorder.stop();
    }, 100);
  });
}
