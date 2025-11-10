// Servicio de autenticación unificado.
// En modo privado (REACT_APP_PRIVATE_MODE=true) se ignora la autenticación real y
// se devuelve siempre un token local y un usuario ficticio.

const PRIVATE_MODE = String(process.env.REACT_APP_PRIVATE_MODE).toLowerCase() === 'true';

// Intentamos detectar el contexto Electron para usar almacenamiento real si existe.
const hasElectronAPI = typeof window !== 'undefined' && window.electronAPI;

const privateAuth = {
  getToken: async () => 'LOCAL_PRIVATE_MODE_TOKEN',
  setToken: async (_t) => {},
  getRefreshToken: async () => null,
  setRefreshToken: async (_t) => {},
  clearTokens: async () => {},
  isAuthenticated: () => true,
  login: async () => ({ ok: true }),
  logout: async () => ({ ok: true }),
  getUser: () => ({ id: 'local', name: 'Local User' }),
};

const electronAuth = {
  getToken: async () => {
    try {
      if (!hasElectronAPI || !window.electronAPI.getToken) return null;
      return await window.electronAPI.getToken();
    } catch (e) { return null; }
  },
  setToken: async (token) => {
    try { if (hasElectronAPI && window.electronAPI.setToken) window.electronAPI.setToken(token); } catch (e) {}
  },
  getRefreshToken: async () => {
    try { if (!hasElectronAPI || !window.electronAPI.getRefreshToken) return null; return await window.electronAPI.getRefreshToken(); } catch (e) { return null; }
  },
  setRefreshToken: async (token) => {
    try { if (hasElectronAPI && window.electronAPI.setRefreshToken) window.electronAPI.setRefreshToken(token); } catch (e) {}
  },
  clearTokens: async () => {
    try { if (hasElectronAPI && window.electronAPI.clearTokens) window.electronAPI.clearTokens(); } catch (e) {}
  },
  isAuthenticated: async () => {
    const t = await electronAuth.getToken();
    return !!t;
  },
  login: async () => ({ ok: false, message: 'Not implemented here' }),
  logout: async () => {
    await electronAuth.clearTokens();
    return { ok: true };
  },
  getUser: () => null,
};

const auth = PRIVATE_MODE ? privateAuth : electronAuth;

export default auth;
export const getToken = auth.getToken;
export const setToken = auth.setToken;
export const getRefreshToken = auth.getRefreshToken;
export const setRefreshToken = auth.setRefreshToken;
export const clearTokens = auth.clearTokens;
export const isAuthenticated = auth.isAuthenticated;
export const login = auth.login;
export const logout = auth.logout;
export const getUser = auth.getUser;

