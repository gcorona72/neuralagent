// Servicio de voz: Web Speech API (solo frontend)
// Permite iniciar/detener reconocimiento, configurable por idioma.

const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
};

export const isSupported = () => !!getSpeechRecognition();

let recognitionInstance = null;

export function start({
  lang = 'es-ES',
  interim = true,
  continuous = true,
  onInterim = () => {},
  onFinal = () => {},
  onEnd = () => {},
  onError = () => {},
} = {}) {
  const SpeechRecognition = getSpeechRecognition();
  if (!SpeechRecognition) {
    throw new Error('SpeechRecognition no soportado en este navegador.');
  }

  // Si ya hay una instancia corriendo, la detenemos antes de crear otra
  if (recognitionInstance) {
    try { recognitionInstance.stop(); } catch (_) {}
    recognitionInstance = null;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = lang;
  recognition.interimResults = interim;
  recognition.continuous = continuous;

  recognition.onresult = (event) => {
    let interimTranscript = '';
    let finalTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += text;
      } else {
        interimTranscript += text;
      }
    }
    if (interimTranscript) onInterim(interimTranscript);
    if (finalTranscript) onFinal(finalTranscript);
  };

  recognition.onerror = (e) => {
    onError(e);
  };

  recognition.onend = () => {
    onEnd();
    recognitionInstance = null;
  };

  recognition.start();
  recognitionInstance = recognition;

  return {
    stop: () => {
      try { recognition.stop(); } catch (_) {}
      recognitionInstance = null;
    },
    isActive: () => !!recognitionInstance,
  };
}

export function stop() {
  if (recognitionInstance) {
    try { recognitionInstance.stop(); } catch (_) {}
    recognitionInstance = null;
  }
}

export default { isSupported, start, stop };

