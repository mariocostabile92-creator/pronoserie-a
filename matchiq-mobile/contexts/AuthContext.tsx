import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import * as SecureStore from 'expo-secure-store';
import { loginUser, registerUser, setAuthToken, getMe } from '../services/api';

// Chiave usata per salvare il JWT in SecureStore
const TOKEN_KEY = 'matchiq_jwt_token';

// Struttura dei dati utente in memoria
interface User {
  email: string;
  piano: string;
}

// Interfaccia pubblica del Context
interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Ricarica i dati utente (email e piano) dal backend */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Provider che gestisce l'intero ciclo di vita dell'autenticazione
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // All'avvio recupera il token salvato e configura l'header axios
  useEffect(() => {
    const ripristinaSessione = async () => {
      try {
        const savedToken = await SecureStore.getItemAsync(TOKEN_KEY);
        if (savedToken) {
          setToken(savedToken);
          setAuthToken(savedToken);
          // L'email/piano verrà caricata dal componente Profilo tramite /api/payments/check-plan
        }
      } catch (e) {
        console.error('Errore caricamento sessione:', e);
      } finally {
        setLoading(false);
      }
    };
    ripristinaSessione();
  }, []);

  // Login: chiama l'API, salva il token e aggiorna lo stato
  const login = useCallback(async (email: string, password: string) => {
    const res = await loginUser(email, password);
    const { access_token, piano } = res.data;
    await SecureStore.setItemAsync(TOKEN_KEY, access_token);
    setAuthToken(access_token);
    setToken(access_token);
    setUser({ email: email.toLowerCase().trim(), piano });
  }, []);

  // Registrazione: chiama l'API, salva il token e aggiorna lo stato
  const register = useCallback(async (email: string, password: string) => {
    const res = await registerUser(email, password);
    const { access_token, piano } = res.data;
    await SecureStore.setItemAsync(TOKEN_KEY, access_token);
    setAuthToken(access_token);
    setToken(access_token);
    setUser({ email: email.toLowerCase().trim(), piano: piano || 'free' });
  }, []);

  // Logout: cancella token dallo store e resetta lo stato
  const logout = useCallback(async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  // Ricarica email e piano dal backend (utile dopo il pagamento Pro)
  const refreshUser = useCallback(async () => {
    try {
      const res = await getMe();
      setUser({ email: res.data.email, piano: res.data.piano });
    } catch (e) {
      console.error('Errore refresh utente:', e);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook per accedere al context in qualsiasi componente figlio
export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth deve essere usato all\'interno di AuthProvider');
  }
  return ctx;
}
