/**
 * Risultati Live - Storico giornate con colori vittoria/sconfitta/pareggio.
 * Aggiunge badge (logo) delle squadre come nella webapp.
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getCalendario } from '../../services/api';
import { getTeamBadgeUrl } from '../../constants/teamIds';

const LEAGUES = [
  { key: 'serie-a',           label: 'ITA',  color: Colors.green },
  { key: 'premier-league',    label: 'ENG',  color: Colors.accent },
  { key: 'la-liga',           label: 'ESP',  color: Colors.yellow },
  { key: 'bundesliga',        label: 'GER',  color: '#d50000' },
  { key: 'ligue-1',           label: 'FRA',  color: '#003189' },
  { key: 'champions-league',  label: 'UCL',  color: '#1a237e' },
  { key: 'europa-league',     label: 'UEL',  color: '#ff6f00' },
  { key: 'conference-league', label: 'UECL', color: '#4caf50' },
];

/** Badge logo squadra inline */
function TeamBadgeInline({ name, size = 18 }: { name: string; size?: number }) {
  const url = getTeamBadgeUrl(name);
  if (!url) return null;
  return <Image source={{ uri: url }} style={{ width: size, height: size, resizeMode: 'contain', marginHorizontal: 3 }} />;
}

export default function RisultatiScreen() {
  const router = useRouter();
  const [leagueIdx, setLeagueIdx] = useState(0);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [giornataSel, setGiornataSel] = useState<number | null>(null);

  const league = LEAGUES[leagueIdx];

  useEffect(() => {
    loadRisultati();
  }, [leagueIdx]);

  const loadRisultati = async () => {
    setLoading(true);
    setData(null);
    setGiornataSel(null);
    try {
      const res = await getCalendario(league.key);
      const d = res.data;
      setData(d);
      // Seleziona l'ultima giornata con risultati
      const gc = d.giornata_corrente;
      const giornateConRisultati = (d.giornate || []).filter((g: any) =>
        g.partite?.some((p: any) => p.gol_h !== null && p.gol_h !== undefined)
      );
      const ultima = giornateConRisultati[giornateConRisultati.length - 1];
      setGiornataSel(ultima?.giornata || gc);
    } catch (_) {}
    setLoading(false);
  };

  const giornate: any[] = data?.giornate || [];
  const giornateConRis = giornate.filter((g: any) =>
    g.partite?.some((p: any) => p.gol_h !== null && p.gol_h !== undefined)
  );
  const giornataData = giornateConRis.find((g: any) => g.giornata === giornataSel)
    || giornate.find((g: any) => g.giornata === giornataSel);

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="risultati" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <View style={styles.titleRow}>
            <Text style={styles.pageTitle}>Risultati</Text>
            {data?.giornate?.some((g: any) => g.live) && (
              <View style={styles.livePill}>
                <Text style={styles.livePillText}>● LIVE</Text>
              </View>
            )}
          </View>

          {/* LEAGUE TABS */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
            <View style={styles.leagueTabs}>
              {LEAGUES.map((l, i) => (
                <TouchableOpacity
                  key={l.key}
                  onPress={() => setLeagueIdx(i)}
                  style={[styles.leagueTab, { backgroundColor: leagueIdx === i ? l.color : '#1f3460' }]}
                >
                  <Text style={[styles.leagueTabText, { color: leagueIdx === i ? '#000' : Colors.muted }]}>
                    {l.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          {loading && <ActivityIndicator color={Colors.accent} style={{ marginTop: 32 }} />}

          {!loading && data && (
            <>
              {/* SELECTOR GIORNATA */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
                <View style={{ flexDirection: 'row', gap: 6 }}>
                  {giornateConRis.map((g: any) => (
                    <TouchableOpacity
                      key={g.giornata}
                      onPress={() => setGiornataSel(g.giornata)}
                      style={[
                        styles.giornataPill,
                        giornataSel === g.giornata && { backgroundColor: league.color },
                      ]}
                    >
                      <Text style={[styles.giornataPillText, giornataSel === g.giornata && { color: '#000' }]}>
                        G.{g.giornata}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>

              {giornataData ? (
                <Card>
                  <View style={styles.cardHeader}>
                    <Text style={styles.cardTitle}>Giornata {giornataData.giornata}</Text>
                    {giornataData.live && (
                      <View style={styles.liveBadge}><Text style={styles.liveBadgeText}>LIVE</Text></View>
                    )}
                  </View>
                  {giornataData.partite?.map((p: any, i: number) => {
                    const hasResult = p.gol_h !== null && p.gol_h !== undefined;
                    if (!hasResult && !p.live) return null;
                    const cH = p.gol_h > p.gol_a ? Colors.green : p.gol_h < p.gol_a ? Colors.red : Colors.yellow;
                    const cA = p.gol_a > p.gol_h ? Colors.green : p.gol_a < p.gol_h ? Colors.red : Colors.yellow;
                    const status = p.status === 'FT' ? 'FT'
                      : p.live ? `${p.minuto || ''}'`
                      : p.status === 'HT' ? 'INT'
                      : p.ora || 'vs';
                    return (
                      <TouchableOpacity
                        key={i}
                        style={[styles.partitaRow, p.live && { backgroundColor: 'rgba(231,76,60,0.08)', borderRadius: 6 }]}
                        onPress={() => p.fixture_id && router.push(`/match/${p.fixture_id}` as any)}
                      >
                        {/* Squadra casa: nome (allineato destra) + badge */}
                        <View style={styles.teamSide}>
                          <Text style={[styles.teamName, { textAlign: 'right' }]} numberOfLines={1}>{p.home}</Text>
                          <TeamBadgeInline name={p.home} />
                        </View>
                        {/* Score */}
                        <View style={styles.scoreBox}>
                          <Text style={styles.score}>
                            <Text style={{ color: cH }}>{p.gol_h}</Text>
                            <Text style={{ color: Colors.muted }}> - </Text>
                            <Text style={{ color: cA }}>{p.gol_a}</Text>
                          </Text>
                          <Text style={[styles.statusText, p.live && { color: Colors.red }]}>{status}</Text>
                        </View>
                        {/* Squadra ospite: badge + nome */}
                        <View style={[styles.teamSide, { justifyContent: 'flex-start' }]}>
                          <TeamBadgeInline name={p.away} />
                          <Text style={styles.teamName} numberOfLines={1}>{p.away}</Text>
                        </View>
                      </TouchableOpacity>
                    );
                  })}
                </Card>
              ) : (
                <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 24 }}>
                  Nessun risultato disponibile per questa giornata
                </Text>
              )}
            </>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text },
  livePill: { backgroundColor: Colors.red, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  livePillText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  leagueTabs: { flexDirection: 'row' },
  leagueTab: { paddingHorizontal: 14, paddingVertical: 8, alignItems: 'center', minWidth: 52 },
  leagueTabText: { fontSize: 12, fontWeight: '700' },
  giornataPill: {
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 20,
    backgroundColor: '#1f3460', borderWidth: 1, borderColor: Colors.border,
  },
  giornataPillText: { color: Colors.muted, fontSize: 12, fontWeight: '600' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text },
  liveBadge: { backgroundColor: Colors.red, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10 },
  liveBadgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  partitaRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  teamSide: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 3 },
  teamName: { color: Colors.text, fontSize: 12, fontWeight: '600', flex: 1 },
  scoreBox: { minWidth: 70, alignItems: 'center' },
  score: { fontSize: 18, fontWeight: '800' },
  statusText: { color: Colors.muted, fontSize: 11, marginTop: 2, textAlign: 'center' },
});
