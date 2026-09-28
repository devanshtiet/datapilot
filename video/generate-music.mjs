import {mkdir, writeFile} from "node:fs/promises";
import {join} from "node:path";

// Original synthesized 8-second 120 BPM cue: bright chords, soft kick, claps and hats.
const rate = 44100;
const frames = rate * 8;
const left = new Float32Array(frames);
const right = new Float32Array(frames);
const beat = .5;
const chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]];
let seed = 37;
const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const hz = n => 440 * 2 ** ((n - 69) / 12);
function add(i, sample, pan = 0, gain = 1) {
  if (i < 0 || i >= frames) return;
  const fade = Math.min(1, (frames - i) / (rate * .45));
  left[i] += sample * Math.sqrt((1 - pan) / 2) * gain * fade;
  right[i] += sample * Math.sqrt((1 + pan) / 2) * gain * fade;
}
for (let i = 0; i < frames; i++) {
  const t = i / rate;
  let pad = 0;
  for (const note of chords[Math.min(3, Math.floor(t / 2))]) {
    const f = hz(note - 12);
    pad += Math.sin(2 * Math.PI * f * t) * .0032 + Math.sin(2 * Math.PI * f * 1.003 * t) * .0014;
  }
  add(i, pad, Math.sin(t * .7) * .12);
}
for (let b = 0; b < 16; b++) {
  const start = Math.round(b * beat * rate);
  for (let j = 0; j < rate * .2; j++) {
    const t = j / rate, env = Math.exp(-t * 22);
    add(start + j, Math.sin(2 * Math.PI * (68 * t + 37 * t * Math.exp(-t * 22))) * env * .34, 0, .75);
  }
  if (b % 4 === 1 || b % 4 === 3) {
    for (let j = 0; j < rate * .15; j++) {
      const t = j / rate;
      add(start + j, ((random() * 2 - 1) * .085 + Math.sin(2 * Math.PI * 185 * t) * .035) * Math.exp(-t * 32), .05, .72);
    }
  }
  for (const offset of [0, Math.round(beat * .5 * rate)]) {
    for (let j = 0; j < rate * .045; j++) {
      add(start + offset + j, (random() - random()) * Math.exp(-j / rate * 95) * .035, offset ? .2 : -.2);
    }
  }
  const note = chords[Math.floor(b / 4)][(b + 1) % 3] + 12;
  for (let j = 0; j < rate * .3; j++) {
    const t = j / rate, f = hz(note), env = Math.exp(-t * 10);
    add(start + j, (Math.sin(2 * Math.PI * f * t) + .24 * Math.sin(2 * Math.PI * f * 2.01 * t)) * env * .105, Math.sin(b * 1.1) * .42);
  }
}
const wav = Buffer.alloc(44 + frames * 4);
wav.write("RIFF", 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write("WAVE", 8);
wav.write("fmt ", 12); wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(2, 22);
wav.writeUInt32LE(rate, 24); wav.writeUInt32LE(rate * 4, 28); wav.writeUInt16LE(4, 32); wav.writeUInt16LE(16, 34);
wav.write("data", 36); wav.writeUInt32LE(frames * 4, 40);
for (let i = 0; i < frames; i++) {
  wav.writeInt16LE(Math.round(Math.max(-1, Math.min(1, left[i] * 1.65)) * 32767), 44 + i * 4);
  wav.writeInt16LE(Math.round(Math.max(-1, Math.min(1, right[i] * 1.65)) * 32767), 46 + i * 4);
}
const output = join(process.cwd(), "public");
await mkdir(output, {recursive: true});
await writeFile(join(output, "datapilot-intro.wav"), wav);
console.log("Generated the original 8-second DataPilot intro cue.");
