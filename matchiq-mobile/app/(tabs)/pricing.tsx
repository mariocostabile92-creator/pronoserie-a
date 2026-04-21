/**
 * Pricing - Identica alla sezione #pricing della webapp.
 * Card Free e Card Pro con feature list e bottone abbonamento.
 */
import React from 'react';
import {
  View, Text, ScrollView, StyleSheet, Linking,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { WebBtn } from '../../components/WebBtn';
import { Colors } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';
import { createCheckout } from '../../services/api';

const FREE_FEATURES = [
  '2 pronostici gratuiti al giorno',
  'Classifiche aggiornate',
  'Calendario e risultati',
  'Notizie dal calcio',
  'Squadre e dettagli rosa',
  'Accesso alla webapp e all\'app mobile',
];

const PRO_FEATURES = [
  'Tutti i pronostici del giorno (nessun limite)',
  'Over/Under 2.5 e Goal/NoGoal per ogni partita',
  'Confidenza Alta: badge SICURA sui pronostici migliori',
  'Analisi completa con xG, H2H, forma pesata',
  'Probabili formazioni e infortunati live ogni 30 min',
  'Marcatori consigliati dall\'IA basati su xG',
  'Pronostico del Giorno per tutte le 9 competizioni',
  'Consigli Fantacalcio IA con motivazioni dettagliate',
  'Storico pronostici personali con verifica risultati',
  'Supporto prioritario',
];

export default function PricingScreen() {
  const router = useRouter();
  const { token, user } = useAuth();
  const isPro = user?.piano === 'pro';

  const handleAbbonati = async () => {
    if (!token) {
      router.push('/auth/login');
      return;
    }
    try {
      // Usa GET /payments/checkout-direct?email=... (come la webapp)
      const res = await createCheckout(user?.email || '');
      if (res.data?.checkout_url) Linking.openURL(res.data.checkout_url);
    } catch (_) {
      router.push('/(tabs)/profilo');
    }
  };

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="pricing" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Piani e Prezzi</Text>
          <Text style={styles.pageSub}>
            Scegli il piano più adatto alle tue esigenze
          </Text>

          {/* CARD FREE */}
          <Card style={styles.priceCard}>
            <Text style={styles.planName}>Free</Text>
            <View style={styles.priceRow}>
              <Text style={styles.price}>0€</Text>
              <Text style={styles.priceFreq}>/mese</Text>
            </View>
            <Text style={styles.planDesc}>Per iniziare a scoprire MatchIQ</Text>
            <View style={styles.divider} />
            {FREE_FEATURES.map((f) => (
              <View key={f} style={styles.featureRow}>
                <Text style={styles.checkIcon}>✓</Text>
                <Text style={styles.featureText}>{f}</Text>
              </View>
            ))}
            <WebBtn
              label="Piano attuale"
              onPress={() => {}}
              variant="outline"
              style={{ marginTop: 20 }}
              disabled={true}
            />
          </Card>

          {/* CARD PRO */}
          <Card highlight="green" style={[styles.priceCard, styles.priceCardPro]}>
            <View style={styles.popularBadge}>
              <Text style={styles.popularText}>⭐ CONSIGLIATO</Text>
            </View>
            <Text style={[styles.planName, { color: Colors.green }]}>Pro</Text>
            <View style={styles.priceRow}>
              <Text style={[styles.price, { color: Colors.green }]}>9.99€</Text>
              <Text style={styles.priceFreq}>/mese</Text>
            </View>
            <Text style={styles.planDesc}>Accesso completo a tutte le funzionalità</Text>
            <View style={styles.divider} />
            {PRO_FEATURES.map((f) => (
              <View key={f} style={styles.featureRow}>
                <Text style={[styles.checkIcon, { color: Colors.green }]}>✓</Text>
                <Text style={[styles.featureText, { color: Colors.text }]}>{f}</Text>
              </View>
            ))}

            {isPro ? (
              <View style={{ alignItems: 'center', marginTop: 20 }}>
                <Text style={{ color: Colors.green, fontWeight: '800', fontSize: 16 }}>
                  ⭐ Sei già abbonato Pro!
                </Text>
                <Text style={{ color: Colors.muted, fontSize: 13, marginTop: 4 }}>
                  Hai accesso completo a tutte le funzionalità
                </Text>
              </View>
            ) : (
              <WebBtn
                label="Abbonati a Pro - 9.99€/mese"
                onPress={handleAbbonati}
                variant="green"
                size="lg"
                style={{ marginTop: 20 }}
              />
            )}
          </Card>

          {/* GARANZIE */}
          <Card style={{ backgroundColor: '#0d1b2a', borderColor: Colors.accent }}>
            <Text style={[styles.cardTitle, { textAlign: 'center', color: Colors.accent }]}>
              🔒 Pagamento sicuro
            </Text>
            <Text style={{ color: Colors.muted, fontSize: 13, textAlign: 'center', lineHeight: 20 }}>
              Stripe protegge ogni transazione.{'\n'}
              Annulli in qualsiasi momento, senza penali.{'\n'}
              Prova gratuita disponibile per i nuovi iscritti.
            </Text>
          </Card>

          {/* FAQ */}
          <Card>
            <Text style={styles.cardTitle}>Domande frequenti</Text>
            {[
              { q: 'Posso cancellare in qualsiasi momento?', a: 'Sì, puoi disdire l\'abbonamento quando vuoi. Non ci sono costi nascosti o penali.' },
              { q: 'Come funziona il piano gratuito?', a: 'Il piano Free ti dà accesso a 2 pronostici al giorno e a tutte le sezioni informative (classifiche, calendario, notizie, squadre).' },
              { q: 'I pronostici sono garantiti?', a: 'No. MatchIQ fornisce analisi statistiche a scopo informativo. I pronostici non garantiscono vincite.' },
            ].map((item) => (
              <View key={item.q} style={styles.faqItem}>
                <Text style={styles.faqQ}>{item.q}</Text>
                <Text style={styles.faqA}>{item.a}</Text>
              </View>
            ))}
          </Card>

          {/* DISCLAIMER */}
          <View style={styles.disclaimer}>
            <View style={styles.warnBox}>
              <Text style={styles.warnTitle}>⚠ GIOCA RESPONSABILMENTE</Text>
              <Text style={styles.warnText}>
                Il gioco è vietato ai minori di 18 anni. Il gioco può causare dipendenza patologica.{'\n'}
                Numero verde: <Text style={{ color: Colors.green, fontWeight: '700' }}>800-558822</Text>
              </Text>
            </View>
            <Text style={styles.disclaimerText}>
              MatchIQ fornisce analisi statistiche a scopo informativo. I pronostici non garantiscono vincite
              e non costituiscono consulenza finanziaria né invito al gioco d'azzardo.
            </Text>
          </View>

        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text, marginBottom: 4 },
  pageSub: { color: Colors.muted, fontSize: 13, marginBottom: 20 },
  priceCard: { marginBottom: 16 },
  priceCardPro: { borderWidth: 2 },
  popularBadge: {
    alignSelf: 'center', backgroundColor: Colors.green,
    paddingHorizontal: 14, paddingVertical: 4, borderRadius: 12, marginBottom: 12,
  },
  popularText: { color: '#000', fontSize: 11, fontWeight: '800' },
  planName: { fontSize: 22, fontWeight: '800', color: Colors.text, textAlign: 'center', marginBottom: 4 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'center', marginBottom: 4 },
  price: { fontSize: 36, fontWeight: '800', color: Colors.text },
  priceFreq: { color: Colors.muted, fontSize: 14, marginLeft: 4 },
  planDesc: { color: Colors.muted, fontSize: 13, textAlign: 'center', marginBottom: 16 },
  divider: { height: 1, backgroundColor: Colors.border, marginBottom: 16 },
  featureRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 8 },
  checkIcon: { color: Colors.accent, fontWeight: '700', marginRight: 10, fontSize: 14, marginTop: 1 },
  featureText: { color: Colors.muted, fontSize: 14, flex: 1, lineHeight: 20 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 12 },
  faqItem: { marginBottom: 14, paddingBottom: 14, borderBottomWidth: 1, borderBottomColor: Colors.border },
  faqQ: { color: Colors.text, fontWeight: '700', fontSize: 14, marginBottom: 4 },
  faqA: { color: Colors.muted, fontSize: 13, lineHeight: 20 },
  disclaimer: { marginBottom: 24 },
  warnBox: { backgroundColor: '#1a0a0a', borderWidth: 1, borderColor: Colors.red, borderRadius: 8, padding: 12, marginBottom: 10 },
  warnTitle: { color: Colors.red, fontWeight: '700', fontSize: 12, marginBottom: 4 },
  warnText: { color: '#ccc', fontSize: 11, lineHeight: 18 },
  disclaimerText: { color: Colors.muted, fontSize: 11, textAlign: 'center', lineHeight: 18 },
});
