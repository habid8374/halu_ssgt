"use client";

/**
 * Aviso sonoro corto para "nuevo paciente en sala", sin archivos de audio:
 * se sintetiza un tono suave con Web Audio. El navegador exige un gesto previo
 * del usuario para reproducir; como el personal ya interactúa con la app
 * (login, clics), normalmente está permitido. Si está bloqueado, falla en
 * silencio sin romper nada.
 */
let ctx: AudioContext | null = null;

function contexto(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    if (!ctx) ctx = new AC();
    return ctx;
  } catch {
    return null;
  }
}

export function beep() {
  const ac = contexto();
  if (!ac) return;
  try {
    if (ac.state === "suspended") void ac.resume();
    const t = ac.currentTime;
    // Dos notas ascendentes (bitono "din-don"), volumen discreto.
    [880, 1174.66].forEach((freq, i) => {
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const inicio = t + i * 0.16;
      gain.gain.setValueAtTime(0, inicio);
      gain.gain.linearRampToValueAtTime(0.14, inicio + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.22);
      osc.connect(gain).connect(ac.destination);
      osc.start(inicio);
      osc.stop(inicio + 0.24);
    });
  } catch {
    /* silencioso */
  }
}

/** Campanilla de llamado (tres notas), para la pantalla de sala de espera. */
export function campanilla() {
  const ac = contexto();
  if (!ac) return;
  try {
    if (ac.state === "suspended") void ac.resume();
    const t = ac.currentTime;
    [659.25, 783.99, 1046.5].forEach((freq, i) => {
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = "triangle";
      osc.frequency.value = freq;
      const inicio = t + i * 0.18;
      gain.gain.setValueAtTime(0, inicio);
      gain.gain.linearRampToValueAtTime(0.18, inicio + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.5);
      osc.connect(gain).connect(ac.destination);
      osc.start(inicio);
      osc.stop(inicio + 0.55);
    });
  } catch {
    /* silencioso */
  }
}

/** Anuncia por voz (Web Speech API) el turno llamado. Falla en silencio. */
export function anunciar(texto: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  try {
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "es-CO";
    u.rate = 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } catch {
    /* silencioso */
  }
}

/** Reanuda el contexto de audio tras un gesto del usuario (kiosco/TV). */
export function activarAudio() {
  const ac = contexto();
  if (ac && ac.state === "suspended") void ac.resume();
}

const CLAVE = "halu_sonido";
export function sonidoActivo(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(CLAVE) !== "0";
}
export function setSonidoActivo(v: boolean) {
  if (typeof window !== "undefined") localStorage.setItem(CLAVE, v ? "1" : "0");
}
