/**
 * Pronostici - Calcolatore con league tabs, dropdown squadre, risultato IA.
 * Identico alla sezione #pronostici della webapp.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { WebBtn } from '../../components/WebBtn';
import { Colors } from '../../constants/theme';
import { useAuth } from '../../contexts/AuthContext';
import { getPrediction, savePrediction } from '../../services/api';
import { getTeamBadgeUrl } from '../../constants/teamIds';

// ===== Dati squadre per lega =====
const LEAGUES: { key: string; label: string; color: string; teams: string[] }[] = [
  {
    key: 'serie-a', label: 'ITA', color: Colors.green,
    teams: ['Inter','Milan','Napoli','Como','Juventus','Roma','Atalanta','Lazio','Bologna','Sassuolo','Udinese','Parma','Genoa','Torino','Cagliari','Fiorentina','Cremonese','Lecce','Verona','Pisa'],
  },
  {
    key: 'premier-league', label: 'ENG', color: Colors.accent,
    teams: ['Arsenal','Aston Villa','Bournemouth','Brentford','Brighton','Burnley','Chelsea','Crystal Palace','Everton','Fulham','Leeds','Liverpool','Man City','Man United','Newcastle','Nott. Forest','Sunderland','Tottenham','West Ham','Wolves'],
  },
  {
    key: 'la-liga', label: 'ESP', color: Colors.yellow,
    teams: ['Alaves','Athletic Club','Atletico Madrid','Barcelona','Celta Vigo','Espanyol','Getafe','Girona','Mallorca','Osasuna','Rayo Vallecano','Real Betis','Real Madrid','Real Sociedad','Sevilla','Valencia','Villarreal'],
  },
  {
    key: 'bundesliga', label: 'GER', color: '#d50000',
    teams: ['Augsburg','Bayern Munich','Bayer Leverkusen','Borussia Dortmund','Eintracht Frankfurt','Freiburg','Heidenheim','Hoffenheim','Mainz','Monchengladbach','RB Leipzig','Stuttgart','Union Berlin','Werder Bremen','Wolfsburg'],
  },
  {
    key: 'ligue-1', label: 'FRA', color: '#003189',
    teams: ['Angers','Auxerre','Le Havre','Lens','Lille','Lyon','Marseille','Monaco','Nantes','Nice','Paris Saint Germain','Rennes','Stade Brestois 29','Strasbourg','Toulouse'],
  },
  {
    key: 'champions-league', label: 'UCL', color: '#1a237e',
    teams: ['Ajax','Arsenal','Atalanta','Barcelona','Bayer Leverkusen','Bayern Munchen','Benfica','Borussia Dortmund','Chelsea','Inter','Juventus','Liverpool','Manchester City','Napoli','Newcastle','PSV Eindhoven','Paris Saint Germain','Real Madrid','Sporting CP','Tottenham','Villarreal'],
  },
  {
    key: 'europa-league', label: 'UEL', color: '#ff6f00',
    teams: ['AS Roma','Aston Villa','Bologna','Celtic','FC Porto','Fenerbahce','Feyenoord','Lille','Lyon','Nice','Nottingham Forest','Real Betis','Rangers','VfB Stuttgart'],
  },
  {
    key: 'conference-league', label: 'UECL', color: '#4caf50',
    teams: ['AZ Alkmaar','Crystal Palace','Fiorentina','Jagiellonia','Lech Poznan','Rapid Vienna','Slovan Bratislava','Sparta Praha'],
  },
  {
    key: 'mondiali-2026', label: '🏆WC', color: Colors.yellow,
    teams: ['USA','Messico','Canada','Brasile','Argentina','Uruguay','Colombia','Francia','Inghilterra','Germania','Spagna','Portogallo','Olanda','Belgio','Croazia','Giappone','Corea del Sud','Marocco','Senegal','Tunisia'],
  },
];

export default function PronosticiScreen() {
  const { user, token } = useAuth();
  const router = useRouter();
  const isPro = user?.piano === 'pro';

  const [currentLeague, setCurrentLeague] = useState(0);
  const [homeIdx, setHomeIdx] = useState(0);
  const [awayIdx, setAwayIdx] = useState(1);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  const league = LEAGUES[currentLeague];
  const teams = league.teams;

  const calcola = async () => {
    const home = teams[homeIdx];
    const away = teams[awayIdx];
    if (home === away) {
      Alert.alert('Attenzione', 'Seleziona due squadre diverse.');
      return;
    }
    setLoading(true);
    setResult(null);
    setSaved(false);
    try {
      const res = await getPrediction(home, away, league.key);
      setResult(res.data);
    } catch (_) {
      Alert.alert('Errore', 'Impossibile calcolare il pronostico. Controlla la connessione.');
    }
    setLoading(false);
  };

  const salva = async () => {
    if (!token) { router.push('/auth/login'); return; }
    if (!result) return;
    try {
      await savePrediction({
        league: league.key,
        home: teams[homeIdx],
        away: teams[awayIdx],
        pronostico: result.result?.['1x2'] || '',
        prob: result.prob_1,
        confidence: result.confidence_label,
        over_under: result.result?.over,
        goal: result.result?.goal,
      });
      setSaved(true);
      Alert.alert('Salvato', 'Pronostico salvato nel tuo profilo!');
    } catch (_) {
      Alert.alert('Errore', 'Impossibile salvare il pronostico.');
    }
  };

  const prob1 = result ? Math.round((result.prob_1 || 0) * 100) : 0;
  const probX = result ? Math.round((result.prob_x || 0) * 100) : 0;
  const prob2 = result ? Math.round((result.prob_2 || 0) * 100) : 0;
  const best = prob1 >= probX && prob1 >= prob2 ? '1' : probX >= prob1 && probX >= prob2 ? 'X' : '2';
  const confLabel = result?.confidence_label;
  const confColor = confLabel === 'Alta' ? Colors.green : confLabel === 'Media' ? Colors.yellow : Colors.muted;

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="pronostici" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Calcola Pronostico IA</Text>
          <Text style={styles.pageSub}>Seleziona lega e squadre per il pronostico</Text>

          {/* LEAGUE TABS */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
            <View style={styles.leagueTabs}>
              {LEAGUES.map((l, i) => (
                <TouchableOpacity
                  key={l.key}
                  onPress={() => { setCurrentLeague(i); setHomeIdx(0); setAwayIdx(1); setResult(null); }}
                  style={[
                    styles.leagueTab,
                    { backgroundColor: currentLeague === i ? l.color : '#1f3460' },
                    i === 0 && { borderTopLeftRadius: 10, borderBottomLeftRadius: 10 },
                    i === LEAGUES.length - 1 && { borderTopRightRadius: 10, borderBottomRightRadius: 10 },
                  ]}
                >
                  <Text style={[styles.leagueTabText, { color: currentLeague === i ? '#000' : Colors.muted }]}>
                    {l.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          {/* SELEZIONE SQUADRE */}
          <Card>
            <Text style={styles.label}>Squadra Casa</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
              <View style={styles.teamPicker}>
                {teams.map((t, i) => (
                  <TouchableOpacity
                    key={t}
                    onPress={() => setHomeIdx(i)}
                    style={[styles.teamChip, homeIdx === i && styles.teamChipActive]}
                  >
                    <Text style={[styles.teamChipText, homeIdx === i && { color: '#000' }]}>{t}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            <Text style={styles.label}>Squadra Ospite</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
              <View style={styles.teamPicker}>
                {teams.map((t, i) => (
                  <TouchableOpacity
                    key={t}
                    onPress={() => setAwayIdx(i)}
                    style={[styles.teamChip, awayIdx === i && styles.teamChipActiveAway]}
                  >
                    <Text style={[styles.teamChipText, awayIdx === i && { color: '#fff' }]}>{t}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            {/* PREVIEW PARTITA con badge - come la webapp */}
            <View style={styles.matchPreview}>
              {(() => {
                const urlH = getTeamBadgeUrl(teams[homeIdx]);
                const urlA = getTeamBadgeUrl(teams[awayIdx]);
                return (
                  <>
                    {urlH ? <Image source={{ uri: urlH }} style={{ width: 24, height: 24, resizeMode: 'contain', marginRight: 6 }} /> : null}
                    <Text style={styles.matchTeam}>{teams[homeIdx]}</Text>
                    <Text style={{ color: Colors.muted, fontSize: 14 }}>vs</Text>
                    <Text style={styles.matchTeam}>{teams[awayIdx]}</Text>
                    {urlA ? <Image source={{ uri: urlA }} style={{ width: 24, height: 24, resizeMode: 'contain', marginLeft: 6 }} /> : null}
                  </>
                );
              })()}
            </View>

            <WebBtn
              label={loading ? 'Calcolo in corso...' : '⚡ Calcola Pronostico'}
              onPress={calcola}
              loading={loading}
              variant="green"
              size="lg"
              style={{ marginTop: 8 }}
            />
          </Card>

          {/* RISULTATO */}
          {result && (
            <Card style={{ borderColor: Colors.green, borderWidth: 2 }}>
              {/* Titolo risultato con badge - come la webapp */}
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 8 }}>
                {(() => {
                  const urlH = getTeamBadgeUrl(teams[homeIdx]);
                  const urlA = getTeamBadgeUrl(teams[awayIdx]);
                  return (
                    <>
                      {urlH ? <Image source={{ uri: urlH }} style={{ width: 22, height: 22, resizeMode: 'contain' }} /> : null}
                      <Text style={[styles.sectionTitle, { color: Colors.green }]}>
                        {teams[homeIdx]} vs {teams[awayIdx]}
                      </Text>
                      {urlA ? <Image source={{ uri: urlA }} style={{ width: 22, height: 22, resizeMode: 'contain' }} /> : null}
                    </>
                  );
                })()}
              </View>

              {/* BOX 1 X 2 */}
              <View style={styles.box1x2Row}>
                {[
                  { label: '1', prob: prob1, win: result.result?.['1x2'] === '1' },
                  { label: 'X', prob: probX, win: result.result?.['1x2'] === 'X' },
                  { label: '2', prob: prob2, win: result.result?.['1x2'] === '2' },
                ].map(({ label, prob, win }) => (
                  <View key={label} style={[styles.box1x2, win && styles.box1x2Best]}>
                    <Text style={styles.box1x2Label}>{label}</Text>
                    <Text style={[styles.box1x2Pct, win && { color: Colors.green }]}>{prob}%</Text>
                    {win && <Text style={styles.box1x2Quota}>Quota {result.quota_1x2 || '—'}</Text>}
                  </View>
                ))}
              </View>

              {/* TAG CONFIDENZA */}
              <View style={{ alignItems: 'center', marginVertical: 8 }}>
                <View style={[styles.confTag, { borderColor: confColor }]}>
                  <Text style={{ color: confColor, fontWeight: '700' }}>
                    Confidenza: {confLabel || '—'}
                  </Text>
                </View>
              </View>

              {/* DETTAGLI PRO */}
              {isPro ? (
                <View style={styles.dettagliPro}>
                  <View style={styles.dettaglioRow}>
                    <Text style={styles.dettaglioLabel}>Over/Under 2.5</Text>
                    <Text style={styles.dettaglioValore}>{result.result?.over || '—'}</Text>
                  </View>
                  <View style={styles.dettaglioRow}>
                    <Text style={styles.dettaglioLabel}>Goal/NoGoal</Text>
                    <Text style={styles.dettaglioValore}>{result.result?.goal || '—'}</Text>
                  </View>
                  {result.over_25 !== undefined && (
                    <View style={styles.dettaglioRow}>
                      <Text style={styles.dettaglioLabel}>P(Over 2.5)</Text>
                      <Text style={styles.dettaglioValore}>{Math.round(result.over_25 * 100)}%</Text>
                    </View>
                  )}
                  {result.goal_si !== undefined && (
                    <View style={styles.dettaglioRow}>
                      <Text style={styles.dettaglioLabel}>P(Goal Sì)</Text>
                      <Text style={styles.dettaglioValore}>{Math.round(result.goal_si * 100)}%</Text>
                    </View>
                  )}
                  {result.suggerimento && (
                    <View style={{ marginTop: 8, padding: 10, backgroundColor: Colors.surface, borderRadius: 8 }}>
                      <Text style={{ color: Colors.text, fontSize: 13, lineHeight: 20 }}>
                        💡 {result.suggerimento}
                      </Text>
                    </View>
                  )}
                </View>
              ) : (
                <View style={styles.lockMsg}>
                  <Text style={{ color: Colors.muted, marginBottom: 8, textAlign: 'center' }}>
                    🔒 Over/Under, Goal/NoGoal e analisi completa disponibili con Pro
                  </Text>
                  <WebBtn label="Abbonati a Pro - 9.99€/mese" onPress={() => router.push('/(tabs)/pricing')} variant="green" />
                </View>
              )}

              {/* SALVA */}
              {token && !saved && (
                <WebBtn
                  label="Salva Pronostico"
                  onPress={salva}
                  variant="blue"
                  style={{ marginTop: 12 }}
                />
              )}
              {saved && (
                <Text style={{ color: Colors.green, textAlign: 'center', marginTop: 8, fontWeight: '700' }}>
                  ✓ Pronostico salvato!
                </Text>
              )}
            </Card>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text, marginBottom: 4 },
  pageSub: { color: Colors.muted, fontSize: 13, marginBottom: 16 },
  leagueTabs: { flexDirection: 'row' },
  leagueTab: { paddingHorizontal: 12, paddingVertical: 8, minWidth: 52, alignItems: 'center' },
  leagueTabText: { fontSize: 12, fontWeight: '700' },
  label: { color: Colors.muted, fontSize: 12, fontWeight: '600', marginBottom: 8 },
  teamPicker: { flexDirection: 'row', gap: 6, paddingVertical: 4 },
  teamChip: {
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20,
    backgroundColor: '#1f3460', borderWidth: 1, borderColor: Colors.border,
  },
  teamChipActive: { backgroundColor: Colors.green, borderColor: Colors.green },
  teamChipActiveAway: { backgroundColor: Colors.accent, borderColor: Colors.accent },
  teamChipText: { color: Colors.muted, fontSize: 13, fontWeight: '500' },
  matchPreview: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around',
    paddingVertical: 12, borderTopWidth: 1, borderTopColor: Colors.border,
  },
  matchTeam: { color: Colors.text, fontWeight: '700', fontSize: 15, flex: 1, textAlign: 'center' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 12, textAlign: 'center' },
  box1x2Row: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  box1x2: {
    flex: 1, alignItems: 'center', padding: 14,
    borderRadius: 12, backgroundColor: '#0d1b2a', borderWidth: 2, borderColor: Colors.border,
  },
  box1x2Best: { borderColor: Colors.green, shadowColor: Colors.green, shadowOpacity: 0.2, shadowRadius: 8, elevation: 4 },
  box1x2Label: { color: Colors.muted, fontSize: 13, fontWeight: '700', marginBottom: 4 },
  box1x2Pct: { fontSize: 28, fontWeight: '800', color: Colors.text },
  box1x2Quota: { color: Colors.muted, fontSize: 11, marginTop: 4 },
  confTag: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 6 },
  dettagliPro: { marginTop: 8 },
  dettaglioRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  dettaglioLabel: { color: Colors.muted, fontSize: 14 },
  dettaglioValore: { color: Colors.text, fontWeight: '700', fontSize: 14 },
  lockMsg: { padding: 16, alignItems: 'center' },
});
