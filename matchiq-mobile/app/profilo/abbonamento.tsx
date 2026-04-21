/**
 * app/profilo/abbonamento.tsx
 * Schermata abbonamento Pro.
 * Mostra il piano attuale, il confronto Free vs Pro e il bottone per upgrade.
 * Usa expo-web-browser per aprire il checkout Stripe.
 * Endpoint: GET /api/payments/check-plan, POST /api/payments/checkout
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { ThemedText } from '../../components/ThemedText';
import { ThemedView } from '../../components/ThemedView';
import { Colors, Spacing, BorderRadius } from '../../constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { checkPlan, createCheckout } from '../../services/api';

// Feature incluse nel piano Free
const FEATURE_FREE = [
  '2 pronostici al giorno',
  'Risultato base 1X2',
  'Schedina: 2 partite',
  'Classifica campionati',
];

// Feature esclusive del piano Pro
const FEATURE_PRO = [
  'Pronostici illimitati',
  'Analisi completa (O/U, Goal, Confidenza)',
  'Probabilità e quote dettagliate',
  'Schedina completa (tutte le partite)',
  'Marcatori e formazioni live',
  'Notifiche gol in tempo reale',
  'Storico pronostici con accuratezza',
];

export default function AbbonamentoScreen() {
  const { user, refreshUser } = useAuth();

  const [piano, setPiano] = useState<string>(user?.piano || 'free');
  const [caricamento, setCaricamento] = useState(true);
  const [checkout, setCheckout] = useState(false);

  // Carica il piano aggiornato dal backend
  const caricaPiano = useCallback(async () => {
    try {
      const res = await checkPlan();
      setPiano(res.data.piano);
    } catch (err) {
      console.error('Errore caricamento piano:', err);
      setPiano(user?.piano || 'free');
    } finally {
      setCaricamento(false);
    }
  }, [user]);

  useEffect(() => {
    caricaPiano();
  }, [caricaPiano]);

  // Avvia il flusso di checkout Stripe tramite browser esterno
  const handleCheckout = async () => {
    if (piano === 'pro') {
      Alert.alert('Sei già Pro!', 'Il tuo piano Pro è già attivo.');
      return;
    }

    setCheckout(true);
    try {
      // Crea sessione checkout Stripe (richiede JWT)
      const res = await createCheckout();
      const checkoutUrl = res.data.checkout_url;

      if (!checkoutUrl) {
        throw new Error('URL checkout non disponibile');
      }

      // Apri Stripe nel browser di sistema
      const risultato = await WebBrowser.openBrowserAsync(checkoutUrl, {
        presentationStyle: WebBrowser.WebBrowserPresentationStyle.FORM_SHEET,
      });

      // Dopo la chiusura del browser, ricarica il piano
      if (risultato.type === 'cancel' || risultato.type === 'dismiss') {
        // Attende 1 secondo poi controlla se il pagamento è andato a buon fine
        setTimeout(async () => {
          await caricaPiano();
          await refreshUser();
        }, 1000);
      }
    } catch (err: any) {
      const messaggio = err?.response?.data?.detail || 'Impossibile avviare il pagamento. Riprova più tardi.';
      Alert.alert('Errore pagamento', messaggio);
    } finally {
      setCheckout(false);
    }
  };

  // Ricarica manuale del piano dopo il pagamento
  const handleRicaricaPiano = async () => {
    setCaricamento(true);
    await caricaPiano();
    await refreshUser();
  };

  if (caricamento) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <ThemedText color="muted" style={{ marginTop: Spacing.md }}>
          Caricamento piano...
        </ThemedText>
      </View>
    );
  }

  const isPro = piano === 'pro';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      {/* Piano attuale */}
      <ThemedView style={[styles.pianoCard, isPro && styles.pianoCardPro]}>
        <View style={styles.pianoHeader}>
          <Ionicons
            name={isPro ? 'star' : 'person-outline'}
            size={32}
            color={isPro ? Colors.accent : Colors.textSecondary}
          />
          <View style={{ marginLeft: Spacing.md }}>
            <ThemedText type="h2" style={isPro ? styles.testoPro : undefined}>
              {isPro ? 'Piano Pro' : 'Piano Gratuito'}
            </ThemedText>
            <ThemedText type="caption" color="muted">
              {isPro ? 'Accesso completo a tutte le funzioni' : 'Accesso limitato'}
            </ThemedText>
          </View>
        </View>

        {isPro && (
          <View style={styles.proBadge}>
            <Ionicons name="checkmark-circle" size={16} color={Colors.accent} />
            <ThemedText type="small" style={{ color: Colors.accent, marginLeft: 4 }}>
              Abbonamento attivo
            </ThemedText>
          </View>
        )}
      </ThemedView>

      {/* Confronto piani */}
      <ThemedText type="h3" style={styles.sezioneTitle}>Confronto Piani</ThemedText>

      <View style={styles.confrontoGrid}>
        {/* Colonna Free */}
        <ThemedView style={[styles.pianoColonna, !isPro && styles.pianoColonnaAttivo]}>
          <View style={styles.colonnaHeader}>
            <ThemedText type="h3" color="muted">Free</ThemedText>
            <ThemedText type="h2" style={{ color: Colors.textSecondary }}>€0</ThemedText>
            <ThemedText type="small" color="muted">/mese</ThemedText>
          </View>
          {FEATURE_FREE.map((f, i) => (
            <View key={i} style={styles.featureRiga}>
              <Ionicons name="checkmark" size={16} color={Colors.textSecondary} />
              <ThemedText type="small" style={styles.featureTesto}>{f}</ThemedText>
            </View>
          ))}
        </ThemedView>

        {/* Colonna Pro */}
        <ThemedView style={[styles.pianoColonna, styles.pianoColonnaPro]}>
          <View style={styles.colonnaHeader}>
            <ThemedText type="h3" style={{ color: Colors.accent }}>Pro</ThemedText>
            <ThemedText type="h2" style={{ color: Colors.accent }}>€4,99</ThemedText>
            <ThemedText type="small" color="muted">/mese</ThemedText>
          </View>
          {FEATURE_PRO.map((f, i) => (
            <View key={i} style={styles.featureRiga}>
              <Ionicons name="star" size={14} color={Colors.accent} />
              <ThemedText type="small" style={[styles.featureTesto, { color: Colors.text }]}>{f}</ThemedText>
            </View>
          ))}
        </ThemedView>
      </View>

      {/* Bottone upgrade o stato Pro */}
      {!isPro ? (
        <TouchableOpacity
          style={styles.bottoneUpgrade}
          onPress={handleCheckout}
          disabled={checkout}
        >
          <View style={[styles.bottoneContent, checkout && styles.bottoneDisabilitato]}>
            {checkout ? (
              <ActivityIndicator size="small" color={Colors.background} />
            ) : (
              <Ionicons name="star" size={20} color={Colors.background} />
            )}
            <ThemedText style={styles.bottoneTestoUpgrade}>
              {checkout ? 'Apertura pagamento...' : 'Passa a Pro — €4,99/mese'}
            </ThemedText>
          </View>
        </TouchableOpacity>
      ) : (
        <ThemedView style={styles.proAttivoCard}>
          <Ionicons name="checkmark-circle" size={24} color={Colors.primary} />
          <ThemedText type="body" style={{ marginLeft: Spacing.sm, color: Colors.primary }}>
            Piano Pro attivo. Grazie per il supporto!
          </ThemedText>
        </ThemedView>
      )}

      {/* Bottone ricarica manuale (utile dopo il pagamento) */}
      {!isPro && (
        <TouchableOpacity style={styles.bottoneRicarica} onPress={handleRicaricaPiano}>
          <Ionicons name="refresh-outline" size={16} color={Colors.textSecondary} />
          <ThemedText type="small" color="muted" style={{ marginLeft: Spacing.xs }}>
            Hai già pagato? Aggiorna stato piano
          </ThemedText>
        </TouchableOpacity>
      )}

      {/* Note */}
      <ThemedText type="small" color="muted" style={styles.nota}>
        Il pagamento viene gestito in modo sicuro da Stripe. Puoi annullare in qualsiasi momento.
        Nessun addebito automatico senza conferma.
      </ThemedText>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxl,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pianoCard: {
    padding: Spacing.lg,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: Spacing.lg,
  },
  pianoCardPro: {
    borderColor: Colors.accent,
    backgroundColor: Colors.surface,
  },
  pianoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  testoPro: {
    color: Colors.accent,
  },
  proBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.sm,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.full,
    alignSelf: 'flex-start',
  },
  sezioneTitle: {
    marginBottom: Spacing.md,
  },
  confrontoGrid: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  pianoColonna: {
    flex: 1,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.xs,
  },
  pianoColonnaAttivo: {
    borderColor: Colors.border,
  },
  pianoColonnaPro: {
    borderColor: Colors.accent,
    backgroundColor: Colors.surface,
  },
  colonnaHeader: {
    alignItems: 'center',
    marginBottom: Spacing.sm,
    paddingBottom: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  featureRiga: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginVertical: 2,
  },
  featureTesto: {
    flex: 1,
    lineHeight: 18,
    color: Colors.textSecondary,
  },
  bottoneUpgrade: {
    marginBottom: Spacing.sm,
  },
  bottoneContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.accent,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
  },
  bottoneDisabilitato: {
    opacity: 0.6,
  },
  bottoneTestoUpgrade: {
    color: Colors.background,
    fontWeight: '700',
    fontSize: 16,
  },
  proAttivoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.primary,
    marginBottom: Spacing.md,
  },
  bottoneRicarica: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.sm,
    marginBottom: Spacing.md,
  },
  nota: {
    textAlign: 'center',
    lineHeight: 18,
    marginTop: Spacing.md,
  },
});
