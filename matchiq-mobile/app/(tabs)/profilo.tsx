/**
 * Profilo utente - Login opzionale (identico alla webapp: login è un bottone, non un obbligo).
 * Se l'utente non è loggato, mostra form login/register opzionale.
 * Se loggato, mostra info account, piano, storico pronostici.
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, TextInput, ActivityIndicator, Linking,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { WebBtn } from '../../components/WebBtn';
import { Colors } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';
import { getMe, getReferralCode, applyReferral, createCheckout } from '../../services/api';

export default function ProfiloScreen() {
  const router = useRouter();
  const { token, user, login, logout } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  const [referralCode, setReferralCode] = useState('');
  const [myCode, setMyCode] = useState('');
  const [referralInput, setReferralInput] = useState('');

  useEffect(() => {
    if (token) loadReferral();
  }, [token]);

  const loadReferral = async () => {
    try {
      const res = await getReferralCode();
      setMyCode(res.data?.code || '');
    } catch (_) {}
  };

  const handleLogin = async () => {
    if (!email || !password) { Alert.alert('Errore', 'Inserisci email e password.'); return; }
    setLoginLoading(true);
    try {
      await login(email, password);
    } catch (e: any) {
      Alert.alert('Errore', e?.message || 'Login fallito. Controlla email e password.');
    }
    setLoginLoading(false);
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Vuoi uscire dal tuo account?', [
      { text: 'Annulla', style: 'cancel' },
      { text: 'Esci', style: 'destructive', onPress: logout },
    ]);
  };

  const handleAbbonati = async () => {
    try {
      // Usa GET /payments/checkout-direct?email=... (come la webapp)
      const res = await createCheckout(user?.email || '');
      if (res.data?.checkout_url) Linking.openURL(res.data.checkout_url);
    } catch (_) {
      router.push('/(tabs)/pricing');
    }
  };

  const handleApplyReferral = async () => {
    if (!referralInput) return;
    try {
      await applyReferral(referralInput, user?.email || '');
      Alert.alert('Ottimo!', 'Codice referral applicato con successo!');
      setReferralInput('');
    } catch (_) {
      Alert.alert('Errore', 'Codice non valido o già utilizzato.');
    }
  };

  // === UTENTE NON LOGGATO ===
  if (!token) {
    return (
      <View style={styles.container}>
        <TopNavbar activeTab="profilo" />
        <ScrollView showsVerticalScrollIndicator={false}>
          <View style={styles.body}>
            <Card style={{ alignItems: 'center', paddingVertical: 32 }}>
              <Text style={{ fontSize: 48, marginBottom: 12 }}>👤</Text>
              <Text style={styles.pageTitle}>Area Personale</Text>
              <Text style={{ color: Colors.muted, textAlign: 'center', marginBottom: 24, fontSize: 14 }}>
                Accedi per salvare i tuoi pronostici, monitorare l'accuratezza e gestire l'abbonamento Pro.
              </Text>

              {/* Navigazione libera: l'utente può usare tutta l'app senza login */}
              <Text style={{ color: Colors.accent, fontSize: 13, marginBottom: 20 }}>
                💡 Puoi navigare tutta l'app senza account
              </Text>
            </Card>

            <Card>
              <Text style={styles.cardTitle}>{showRegister ? 'Crea Account' : 'Accedi'}</Text>
              <TextInput
                style={styles.input}
                placeholder="Email"
                placeholderTextColor={Colors.muted}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
              />
              <TextInput
                style={styles.input}
                placeholder="Password"
                placeholderTextColor={Colors.muted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
              <WebBtn
                label={loginLoading ? 'Accesso...' : (showRegister ? 'Crea Account' : 'Accedi')}
                onPress={handleLogin}
                variant="green"
                loading={loginLoading}
                style={{ marginTop: 8 }}
              />
              <TouchableOpacity onPress={() => setShowRegister(!showRegister)} style={{ marginTop: 12, alignItems: 'center' }}>
                <Text style={{ color: Colors.accent, fontSize: 13 }}>
                  {showRegister ? 'Hai già un account? Accedi' : 'Non hai un account? Registrati'}
                </Text>
              </TouchableOpacity>
            </Card>
          </View>
        </ScrollView>
      </View>
    );
  }

  // === UTENTE LOGGATO ===
  const isPro = user?.piano === 'pro';

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="profilo" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>

          {/* ACCOUNT INFO */}
          <Card>
            <View style={styles.accountHeader}>
              <Text style={{ fontSize: 40 }}>👤</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={styles.accountEmail}>{user?.email}</Text>
                <View style={[styles.pianoBadge, isPro && styles.pianoProBadge]}>
                  <Text style={[styles.pianoText, isPro && { color: '#000' }]}>
                    {isPro ? '⭐ Pro' : '🆓 Free'}
                  </Text>
                </View>
              </View>
            </View>
          </Card>

          {/* UPGRADE PRO */}
          {!isPro && (
            <Card highlight="green">
              <Text style={styles.cardTitle}>Abbonati a Pro</Text>
              <Text style={{ color: Colors.muted, fontSize: 14, marginBottom: 16 }}>
                Pronostici completi, Over/Under, Goal/NoGoal, analisi dettagliate e molto altro.
              </Text>
              <WebBtn label="Abbonati - Solo 9.99€/mese" onPress={handleAbbonati} variant="green" size="lg" />
            </Card>
          )}

          {/* STORICO PRONOSTICI */}
          <TouchableOpacity onPress={() => router.push('/profilo/pronostici' as any)}>
            <Card style={styles.menuItem}>
              <Text style={styles.menuItemText}>📋  I Miei Pronostici</Text>
              <Text style={styles.menuArrow}>→</Text>
            </Card>
          </TouchableOpacity>

          {/* ABBONAMENTO */}
          <TouchableOpacity onPress={() => router.push('/profilo/abbonamento' as any)}>
            <Card style={styles.menuItem}>
              <Text style={styles.menuItemText}>💳  Gestione Abbonamento</Text>
              <Text style={styles.menuArrow}>→</Text>
            </Card>
          </TouchableOpacity>

          {/* REFERRAL */}
          {myCode ? (
            <Card>
              <Text style={styles.cardTitle}>🎁 Il tuo codice referral</Text>
              <View style={styles.referralBox}>
                <Text style={styles.referralCode}>{myCode}</Text>
              </View>
              <Text style={{ color: Colors.muted, fontSize: 12, marginTop: 8 }}>
                Condividilo con i tuoi amici: entrambi ricevete un vantaggio!
              </Text>
            </Card>
          ) : null}

          {/* APPLICA REFERRAL */}
          <Card>
            <Text style={styles.cardTitle}>Hai un codice referral?</Text>
            <View style={styles.referralInputRow}>
              <TextInput
                style={[styles.input, { flex: 1, marginBottom: 0 }]}
                placeholder="Inserisci codice"
                placeholderTextColor={Colors.muted}
                value={referralInput}
                onChangeText={setReferralInput}
                autoCapitalize="characters"
              />
              <WebBtn label="Applica" onPress={handleApplyReferral} variant="blue" size="sm" style={{ marginLeft: 8 }} />
            </View>
          </Card>

          {/* LOGOUT */}
          <WebBtn
            label="Esci dall'account"
            onPress={handleLogout}
            variant="outline"
            style={{ marginBottom: 32 }}
          />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  pageTitle: { fontSize: 20, fontWeight: '700', color: Colors.text, marginBottom: 8 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 12 },
  input: {
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12,
    color: Colors.text, fontSize: 15, marginBottom: 12,
  },
  accountHeader: { flexDirection: 'row', alignItems: 'center' },
  accountEmail: { color: Colors.text, fontSize: 16, fontWeight: '600', marginBottom: 6 },
  pianoBadge: {
    alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 12, backgroundColor: '#1f3460',
  },
  pianoProBadge: { backgroundColor: Colors.green },
  pianoText: { color: Colors.muted, fontSize: 12, fontWeight: '700' },
  menuItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 14 },
  menuItemText: { color: Colors.text, fontSize: 15, fontWeight: '600' },
  menuArrow: { color: Colors.accent, fontSize: 18 },
  referralBox: {
    backgroundColor: Colors.surface, borderRadius: 10, padding: 14,
    alignItems: 'center', borderWidth: 1, borderColor: Colors.green,
  },
  referralCode: { color: Colors.green, fontSize: 24, fontWeight: '800', letterSpacing: 4 },
  referralInputRow: { flexDirection: 'row', alignItems: 'center' },
});
