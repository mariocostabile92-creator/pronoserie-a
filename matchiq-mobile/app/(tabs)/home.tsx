/**
 * Home screen - Identica alla webapp: hero section, statistiche, fonti dati, Pro card.
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Linking,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { WebBtn } from '../../components/WebBtn';
import { Colors } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';
import { getDailyTips, getAccuratezza, createCheckout } from '../../services/api';
import { getTeamBadgeUrl } from '../../constants/teamIds';

const API_BASE = process.env.EXPO_PUBLIC_API_URL?.replace('/api', '') || 'https://matchiq.it.com';

export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const isPro = user?.piano === 'pro';

  const [schedina, setSchedina] = useState<any>(null);
  const [accuratezza, setAccuratezza] = useState<any>(null);
  const [loadingSchedina, setLoadingSchedina] = useState(true);

  useEffect(() => {
    loadSchedina();
    loadAcc();
  }, []);

  const loadSchedina = async () => {
    try {
      const res = await getDailyTips('serie-a');
      setSchedina(res.data);
    } catch (_) {}
    setLoadingSchedina(false);
  };

  const loadAcc = async () => {
    try {
      const res = await getAccuratezza();
      setAccuratezza(res.data);
    } catch (_) {}
  };

  const handleAbbonati = async () => {
    if (!token) {
      router.push('/auth/login');
      return;
    }
    try {
      // Usa GET /payments/checkout-direct?email=... (come la webapp)
      const res = await createCheckout(user?.email || '');
      if (res.data.checkout_url) {
        Linking.openURL(res.data.checkout_url);
      }
    } catch (_) {
      router.push('/(tabs)/pricing');
    }
  };

  const accTotale = accuratezza?.totale;

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="home" />
      <ScrollView showsVerticalScrollIndicator={false}>

        {/* HERO SECTION */}
        <View style={styles.hero}>
          <Text style={styles.heroLogo}>⚽</Text>
          <Text style={styles.heroTitle}>MatchIQ</Text>
          <Text style={styles.heroSubtitle}>Simulatore Pronostici Calcistici</Text>
          <Text style={styles.heroDesc}>
            L'intelligenza artificiale che analizza ogni partita per te.{'\n'}
            Serie A · Premier League · La Liga · Bundesliga · Ligue 1{'\n'}
            UCL · UEL · UECL · Mondiali 2026
          </Text>
          <WebBtn
            label="Prova Gratis - Calcola Pronostico"
            onPress={() => router.push('/(tabs)/pronostici')}
            variant="green"
            size="lg"
            style={{ marginTop: 16, alignSelf: 'stretch' }}
          />
          {/* App install box */}
          <View style={styles.installBox}>
            <Text style={styles.installTitle}>Installa l'app sul tuo smartphone</Text>
            <Text style={styles.installText}>
              <Text style={styles.installBold}>iPhone: </Text>
              Safari › Condividi › "Aggiungi alla schermata Home"{'\n'}
              <Text style={styles.installBold}>Android: </Text>
              Chrome › 3 puntini › "Aggiungi a schermata Home"
            </Text>
            <Text style={[styles.installText, { marginTop: 6, color: Colors.muted }]}>
              Presto disponibile su App Store e Google Play
            </Text>
          </View>
        </View>

        <View style={styles.body}>

          {/* COME FUNZIONA */}
          <Card highlight="blue" style={{ borderWidth: 1 }}>
            <Text style={styles.sectionTitle}>Come funziona? Semplicissimo.</Text>
            <View style={styles.stepsRow}>
              {[
                { n: '1', t: 'Scegli le squadre', s: 'Seleziona la partita che ti interessa dal menu' },
                { n: '2', t: "L'IA calcola tutto", s: 'Analizza 8 fonti dati e 15 anni di storico in 2 secondi' },
                { n: '3', t: 'Ricevi il pronostico', s: "Ti dice il risultato più probabile con la % di successo" },
              ].map((step) => (
                <View key={step.n} style={styles.stepBox}>
                  <Text style={styles.stepNum}>{step.n}</Text>
                  <Text style={styles.stepTitle}>{step.t}</Text>
                  <Text style={styles.stepDesc}>{step.s}</Text>
                </View>
              ))}
            </View>
          </Card>

          {/* NON SERVE ESSERE ESPERTI */}
          <Card style={{ backgroundColor: '#0d3b1e', borderColor: Colors.green, borderWidth: 1 }}>
            <Text style={[styles.sectionTitle, { color: Colors.green }]}>Non serve essere esperti!</Text>
            <Text style={styles.expertText}>
              <Text style={{ color: Colors.green, fontWeight: '700' }}>MatchIQ </Text>
              fa tutto il lavoro per te. L'intelligenza artificiale analizza{' '}
              <Text style={{ fontWeight: '700' }}>36.659 partite storiche</Text> di 8 competizioni,
              gli <Text style={{ fontWeight: '700' }}>scontri diretti</Text>, la{' '}
              <Text style={{ fontWeight: '700' }}>forma delle squadre</Text>, gli{' '}
              <Text style={{ fontWeight: '700' }}>infortunati</Text>, le{' '}
              <Text style={{ fontWeight: '700' }}>formazioni</Text> e le{' '}
              <Text style={{ fontWeight: '700' }}>quote dei bookmaker</Text>.
            </Text>
          </Card>

          {/* STATISTICHE */}
          <Text style={styles.h2}>I nostri numeri parlano chiaro</Text>
          <View style={styles.statsRow}>
            <Card highlight="green" style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.green }]}>36.659</Text>
              <Text style={styles.statLbl}>Partite analizzate</Text>
            </Card>
            <Card highlight="blue" style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.accent }]}>9</Text>
              <Text style={styles.statLbl}>Competizioni{'\n'}coperte</Text>
            </Card>
            <Card highlight="yellow" style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.yellow }]}>8</Text>
              <Text style={styles.statLbl}>Fonti dati{'\n'}combinate</Text>
            </Card>
          </View>

          {/* 8 FONTI DATI */}
          <Text style={styles.h2}>Le nostre 8 fonti dati</Text>
          <View style={styles.fontiGrid}>
            {[
              { e: '📊', t: '15 anni di storico', s: 'Forza attacco/difesa calcolata su migliaia di partite' },
              { e: '📈', t: 'xG 2025-2026', s: 'Expected Goals della stagione corrente' },
              { e: '⚔️', t: 'Testa a testa H2H', s: '332 coppie di scontri diretti analizzati' },
              { e: '🔥', t: 'Forma pesata', s: 'Ultime 15 partite con decay esponenziale' },
              { e: '🧮', t: 'Dixon-Coles + Ensemble', s: '3 modelli combinati per massima precisione' },
              { e: '🏥', t: 'Infortunati + Formazioni', s: 'Aggiornamenti live ogni 30 minuti' },
              { e: '🏆', t: 'Classifica + Marcatori', s: 'Posizione in classifica e top scorer' },
              { e: '💰', t: 'Quote Bookmaker Live', s: 'Media di 10+ bookmaker europei in tempo reale' },
            ].map((f) => (
              <Card key={f.t} style={styles.fonteCard}>
                <Text style={styles.fonteEmoji}>{f.e}</Text>
                <Text style={styles.fonteTitolo}>{f.t}</Text>
                <Text style={styles.fonteDesc}>{f.s}</Text>
              </Card>
            ))}
          </View>

          {/* BACKTESTING */}
          <View style={styles.statsRow}>
            <Card style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.accent }]}>
                {accTotale ? `${accTotale.acc_1x2.toFixed(1)}%` : '54.8%'}
              </Text>
              <Text style={styles.statLbl}>1X2{'\n'}({accTotale?.partite || 299} partite)</Text>
            </Card>
            <Card style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.accent }]}>
                {accTotale ? `${accTotale.acc_goal.toFixed(1)}%` : '57.5%'}
              </Text>
              <Text style={styles.statLbl}>Goal/{'\n'}NoGoal</Text>
            </Card>
            <Card highlight="green" style={styles.statCard}>
              <Text style={[styles.statNum, { color: Colors.green }]}>
                {accTotale ? `${accTotale.acc_alta.toFixed(1)}%` : '67.3%'}
              </Text>
              <Text style={styles.statLbl}>Confidenza{'\n'}ALTA</Text>
            </Card>
          </View>

          <Card style={{ backgroundColor: '#0d1b2a', borderColor: Colors.accent }}>
            <Text style={styles.backtestText}>
              Questi numeri sono il risultato di un{' '}
              <Text style={{ fontWeight: '700' }}>backtesting su 299 partite reali</Text> della stagione
              2025-2026. Quando l'IA ha confidenza Alta, centra il risultato 1X2{' '}
              <Text style={{ color: Colors.green, fontWeight: '700' }}>2 volte su 3</Text>.
            </Text>
          </Card>

          {/* SCHEDINA DEL GIORNO */}
          {loadingSchedina ? (
            <ActivityIndicator color={Colors.green} style={{ marginVertical: 16 }} />
          ) : schedina?.giocate?.length > 0 ? (
            <Card highlight="green" style={{ borderWidth: 2 }}>
              <Text style={[styles.sectionTitle, { color: Colors.green, textAlign: 'center' }]}>
                Pronostico del Giorno - G.{schedina.giornata}
              </Text>
              <Text style={[styles.statLbl, { textAlign: 'center', marginBottom: 12 }]}>{schedina.tipo}</Text>
              {(isPro ? schedina.giocate : schedina.giocate.slice(0, 2)).map((g: any, i: number) => {
                // Badge squadre - identico alla funzione badge() in index.html
                const badgeHome = getTeamBadgeUrl(g.home);
                const badgeAway = getTeamBadgeUrl(g.away);
                return (
                <View key={i} style={styles.schedinaTip}>
                  <View style={{ flex: 1 }}>
                    {/* Riga squadre con badge - come la webapp */}
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                      {badgeHome ? <Image source={{ uri: badgeHome }} style={{ width: 16, height: 16, resizeMode: 'contain' }} /> : null}
                      <Text style={{ color: Colors.text, fontSize: 14, fontWeight: '600' }}>
                        {g.home}
                      </Text>
                      <Text style={{ color: Colors.muted }}> vs </Text>
                      <Text style={{ color: Colors.text, fontSize: 14, fontWeight: '600' }}>
                        {g.away}
                      </Text>
                      {badgeAway ? <Image source={{ uri: badgeAway }} style={{ width: 16, height: 16, resizeMode: 'contain' }} /> : null}
                    </View>
                    <Text style={{ color: Colors.muted, fontSize: 11, marginTop: 2 }}>
                      Conf. {g.confidence}% | {g.over_under} | {g.goal}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <View style={styles.tagGreen}><Text style={{ fontWeight: '700', color: '#000' }}>{g.tip}</Text></View>
                    <Text style={{ color: Colors.muted, fontSize: 11, marginTop: 4 }}>Quota {g.quota}</Text>
                  </View>
                </View>
                );
              })}
              {!isPro && schedina.giocate.length > 2 && (
                <View style={{ alignItems: 'center', paddingTop: 12 }}>
                  <Text style={{ color: Colors.muted, marginBottom: 8 }}>
                    + {schedina.giocate.length - 2} altri pronostici SICURI
                  </Text>
                  <WebBtn label="Sblocca tutto con Pro - 9.99€/mese" onPress={handleAbbonati} variant="green" />
                </View>
              )}
              {isPro && schedina.quota_totale && (
                <View style={styles.quotaTotale}>
                  <Text style={{ color: Colors.muted, fontSize: 13 }}>Quota totale:</Text>
                  <Text style={{ fontSize: 22, fontWeight: '800', color: Colors.green, marginTop: 4 }}>
                    {schedina.quota_totale}
                  </Text>
                </View>
              )}
            </Card>
          ) : null}

          {/* VANTAGGI PRO */}
          <Card highlight="green">
            {isPro && (
              <View style={{ alignItems: 'center', marginBottom: 12 }}>
                <Text style={{ fontSize: 28 }}>⭐</Text>
                <Text style={{ color: Colors.green, fontWeight: '800', fontSize: 16 }}>Sei già abbonato Pro!</Text>
                <Text style={{ color: Colors.muted, fontSize: 13 }}>Hai accesso completo a tutte le funzionalità</Text>
              </View>
            )}
            <Text style={[styles.sectionTitle, { color: Colors.green }]}>
              {isPro ? 'Le tue funzionalità Pro' : 'Perché abbonarsi a Pro?'}
            </Text>
            {[
              'Il Pronostico del Giorno seleziona SOLO i pronostici con confidenza Alta',
              'Accesso a TUTTE le 8 giornate rimanenti con pronostici completi',
              'Classifica, marcatori e rose aggiornate in tempo reale',
              'Probabili formazioni e infortunati live aggiornati ogni 30 min',
              'Over/Under, Goal/NoGoal e Risultato Esatto per ogni partita',
              'Marcatori consigliati dall\'IA basati su xG e storico',
              'Badge SICURA sui pronostici con massima affidabilità',
              'Notizie dal Calcio live',
            ].map((item, i) => (
              <View key={i} style={styles.proFeatureRow}>
                <Text style={{ color: Colors.green, fontWeight: '700', marginRight: 8 }}>{i + 1}.</Text>
                <Text style={{ color: Colors.text, fontSize: 14, flex: 1 }}>{item}</Text>
              </View>
            ))}
            {!isPro && (
              <WebBtn
                label="Abbonati a Pro - Solo 9.99€/mese"
                onPress={handleAbbonati}
                variant="green"
                size="lg"
                style={{ marginTop: 16 }}
              />
            )}
          </Card>

          {/* MONDIALI 2026 */}
          <Card style={{ backgroundColor: '#1a237e', borderColor: Colors.accent, borderWidth: 2 }}>
            <View style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: 36, marginBottom: 8 }}>🏆🌍</Text>
              <Text style={{ color: Colors.accent, fontSize: 18, fontWeight: '700', marginBottom: 6 }}>
                Mondiali 2026 - LIVE
              </Text>
              <Text style={{ color: Colors.text, fontSize: 14, textAlign: 'center', lineHeight: 22 }}>
                L'IA di MatchIQ analizza i{' '}
                <Text style={{ color: Colors.green, fontWeight: '700' }}>Mondiali FIFA 2026</Text>
                {' '}(USA, Canada, Messico).{'\n'}48 nazionali, gironi live, pronostici per ogni partita.
              </Text>
              <Text style={{ color: Colors.muted, fontSize: 12, marginTop: 8 }}>11 Giugno - 19 Luglio 2026</Text>
              <WebBtn
                label="Vedi Gironi e Calendario 🏆"
                onPress={() => router.push('/mondiali')}
                variant="green"
                style={{ marginTop: 12, alignSelf: 'stretch' }}
              />
            </View>
          </Card>

          {/* FOOTER */}
          <View style={styles.footer}>
            <View style={styles.footerWarn}>
              <Text style={styles.footerWarnTitle}>⚠ GIOCA RESPONSABILMENTE</Text>
              <Text style={styles.footerWarnText}>
                Il gioco è vietato ai minori di 18 anni. Numero verde:{' '}
                <Text style={{ color: Colors.green, fontWeight: '700' }}>800-558822</Text>
              </Text>
            </View>
            <Text style={styles.footerText}>
              MatchIQ fornisce analisi statistiche a scopo informativo. I pronostici{' '}
              <Text style={{ fontWeight: '700' }}>non garantiscono vincite</Text>.
            </Text>
            <Text style={styles.footerText}>© 2026 MatchIQ. Tutti i diritti riservati.</Text>
          </View>

        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  hero: {
    backgroundColor: '#162447',
    padding: 24,
    paddingTop: 32,
    alignItems: 'center',
  },
  heroLogo: { fontSize: 60, marginBottom: 8 },
  heroTitle: { fontSize: 28, fontWeight: '800', color: Colors.text, marginBottom: 4 },
  heroSubtitle: { fontSize: 16, fontWeight: '700', color: Colors.green, marginBottom: 10 },
  heroDesc: { fontSize: 13, color: Colors.muted, textAlign: 'center', lineHeight: 20 },
  installBox: {
    marginTop: 16,
    padding: 14,
    backgroundColor: 'rgba(31,52,96,0.5)',
    borderRadius: 12,
    alignSelf: 'stretch',
  },
  installTitle: { color: Colors.accent, fontWeight: '700', fontSize: 13, marginBottom: 6 },
  installText: { color: Colors.muted, fontSize: 12, lineHeight: 18 },
  installBold: { color: Colors.text, fontWeight: '700' },
  body: { padding: 12 },
  h2: { fontSize: 18, fontWeight: '700', color: Colors.text, textAlign: 'center', marginVertical: 12 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 12, textAlign: 'center' },
  stepsRow: { flexDirection: 'row', gap: 8 },
  stepBox: { flex: 1, alignItems: 'center' },
  stepNum: { fontSize: 32, fontWeight: '800', color: Colors.text, marginBottom: 4 },
  stepTitle: { fontWeight: '700', color: Colors.text, fontSize: 13, textAlign: 'center', marginBottom: 4 },
  stepDesc: { color: Colors.muted, fontSize: 11, textAlign: 'center' },
  expertText: { color: Colors.text, fontSize: 14, lineHeight: 22, textAlign: 'center' },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 4 },
  statCard: { flex: 1, alignItems: 'center', padding: 12 },
  statNum: { fontSize: 24, fontWeight: '800', color: Colors.accent },
  statLbl: { color: Colors.muted, fontSize: 11, textAlign: 'center', marginTop: 4 },
  fontiGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  fonteCard: { width: '47%', alignItems: 'center', padding: 12, margin: 0 },
  fonteEmoji: { fontSize: 24, marginBottom: 6 },
  fonteTitolo: { fontWeight: '700', color: Colors.text, fontSize: 13, textAlign: 'center', marginBottom: 4 },
  fonteDesc: { color: Colors.muted, fontSize: 11, textAlign: 'center' },
  backtestText: { color: Colors.text, fontSize: 14, lineHeight: 22, textAlign: 'center' },
  schedinaTip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  tagGreen: {
    backgroundColor: Colors.green,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  quotaTotale: { alignItems: 'center', marginTop: 10, padding: 10, backgroundColor: '#0d1b2a', borderRadius: 8 },
  proFeatureRow: { flexDirection: 'row', marginBottom: 6, alignItems: 'flex-start' },
  footer: { padding: 16, marginTop: 8, borderTopWidth: 1, borderTopColor: Colors.border },
  footerWarn: {
    backgroundColor: '#1a0a0a',
    borderWidth: 1,
    borderColor: Colors.red,
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  footerWarnTitle: { color: Colors.red, fontWeight: '700', fontSize: 12, marginBottom: 4 },
  footerWarnText: { color: '#ccc', fontSize: 11 },
  footerText: { color: Colors.muted, fontSize: 11, textAlign: 'center', marginBottom: 4 },
});
