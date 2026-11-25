import { describe, expect, it } from 'vitest';
import { VoiceActivity } from './voice-activity';

describe('detecção de fala', () => {
  it('não envia silêncio e encerra após fala seguida por uma pausa', () => {
    const vad = new VoiceActivity(0.02, 1200, 250);
    expect(vad.update(0.001, 0)).toBe(false);
    expect(vad.update(0.001, 5000)).toBe(false);
    expect(vad.update(0.08, 5100)).toBe(false);
    expect(vad.update(0.08, 5400)).toBe(false);
    expect(vad.update(0.001, 6000)).toBe(false);
    expect(vad.update(0.001, 6600)).toBe(true);
  });
  it('ignora um ruído breve', () => {
    const vad = new VoiceActivity(0.02, 1200, 250);
    vad.update(0.08, 0);
    expect(vad.update(0.001, 1400)).toBe(false);
  });
});
