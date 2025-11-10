// Shim para entorno sin Electron o en modo privado.
// Proporciona stubs seguros para las APIs que el frontend espera.

const PRIVATE_MODE = String(process.env.REACT_APP_PRIVATE_MODE).toLowerCase() === 'true';

(function initElectronShim() {
  if (typeof window === 'undefined') return;
  if (!PRIVATE_MODE && window.electronAPI) return; // si hay electron real y no es privado, no tocar

  const listeners = {};
  const on = (event, cb) => { listeners[event] = cb; };
  const emit = (event, ...args) => { if (listeners[event]) listeners[event](...args); };

  const store = new Map();

  window.electronAPI = {
    // Auth tokens
    async getToken() { return store.get('token') ?? null; },
    setToken(token) { store.set('token', token); },
    async getRefreshToken() { return store.get('refresh_token') ?? null; },
    setRefreshToken(token) { store.set('refresh_token', token); },
    deleteToken() { store.delete('token'); },
    deleteRefreshToken() { store.delete('refresh_token'); },
    clearTokens() { store.delete('token'); store.delete('refresh_token'); },

    // Background mode flags
    async getLastBackgroundModeValue() { return store.get('last_bg') ?? 'false'; },
    setLastBackgroundModeValue(v) { store.set('last_bg', v); },
    async getLastThinkingModeValue() { return store.get('last_thinking') ?? 'false'; },
    setLastThinkingModeValue(v) { store.set('last_thinking', v); },

    // Background setup
    isBackgroundModeReady: async () => false,
    startBackgroundSetup: () => { setTimeout(() => emit('setup-complete', { ok: true }), 0); },
    onSetupStatus: (cb) => on('setup-status', cb),
    onSetupProgress: (cb) => on('setup-progress', cb),
    onSetupComplete: (cb) => on('setup-complete', cb),

    // Agent lifecycle
    launchAIAgent: () => {},
    stopAIAgent: () => {},
    onAIAgentLaunch: (cb) => on('agent-launch', cb),
    onAIAgentExit: (cb) => on('agent-exit', cb),

    // Session management
    onLogout: (cb) => on('logout', cb),
    onCancelAllTasksTrigger: (cb) => on('cancel-all', cb),
    cancelAllTasksDone: () => {},

    // OAuth
    loginWithGoogle: async () => ({ code: 'dummy', codeVerifier: 'dummy' }),
  };
})();

