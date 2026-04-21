import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Colors } from '../constants/theme';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { registerForPushNotifications } from '../services/notifications';

// Componente interno che gestisce il redirect in base allo stato di autenticazione
function RootLayoutNav() {
  const { token, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (loading) return;
    const inAuthGroup = segments[0] === 'auth';
    // Se l'utente è già loggato e si trova nelle schermate auth, mandalo alle tabs
    if (token && inAuthGroup) {
      router.replace('/(tabs)/home');
    }
    // NON forzare il login: l'utente può navigare liberamente senza autenticazione
  }, [token, loading, segments]);

  // Registra le push notifications quando l'utente è autenticato
  useEffect(() => {
    if (token && !loading) {
      registerForPushNotifications().catch((e) =>
        console.error('[Layout] Errore registrazione notifiche:', e)
      );
    }
  }, [token, loading]);

  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: Colors.surface,
          },
          headerTintColor: Colors.text,
          headerTitleStyle: {
            fontWeight: 'bold',
          },
          contentStyle: {
            backgroundColor: Colors.background,
          },
        }}
      >
        {/* Schermate principali con tabs */}
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        {/* Schermate di autenticazione (senza header) */}
        <Stack.Screen name="auth/login" options={{ headerShown: false }} />
        <Stack.Screen name="auth/register" options={{ headerShown: false }} />
        {/* Dettaglio partita */}
        <Stack.Screen
          name="match/[id]"
          options={{
            title: 'Dettaglio Partita',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
          }}
        />
        {/* Dettaglio squadra */}
        <Stack.Screen
          name="team/[nome]"
          options={{
            title: 'Squadra',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        />
        {/* Storico pronostici utente */}
        <Stack.Screen
          name="profilo/pronostici"
          options={{
            title: 'I Miei Pronostici',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        />
        {/* Gestione abbonamento */}
        <Stack.Screen
          name="profilo/abbonamento"
          options={{
            title: 'Abbonamento',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        />
        {/* Consigli fantacalcio */}
        <Stack.Screen
          name="fantacalcio"
          options={{
            title: 'Fantacalcio IA',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        />
        {/* Mondiali 2026 */}
        <Stack.Screen
          name="mondiali"
          options={{
            title: 'Mondiali 2026',
            headerStyle: { backgroundColor: Colors.surface },
            headerTintColor: Colors.text,
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        />
        <Stack.Screen name="+not-found" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootLayoutNav />
    </AuthProvider>
  );
}
