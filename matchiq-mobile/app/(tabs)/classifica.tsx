/**
 * Classifica - Identica alla sezione #classifica della webapp (pageClassifica).
 * Colori bordo-left: UCL verde, UEL giallo, Conference viola, Retrocessione rosso.
 * Nomi campo API: Squadra, G, V, N, P, DR, Punti (maiuscoli come nella webapp).
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getClassifica } from '../../services/api';
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

/**
 * Colore bordo-left in base all'indice (0-based), identico alla webapp:
 * i<4 verde (UCL), i<6 giallo (UEL), i===6 viola (Conference), i>=total-3 rosso (Retrocessione)
 */
function zoneColor(idx: number, total: number): string | undefined {
  if (idx < 4) return Colors.green;    // UCL
  if (idx < 6) return Colors.yellow;   // UEL
  if (idx === 6) return '#9b59b6';     // Conference League
  if (idx >= total - 3) return Colors.red; // Retrocessione (ultimi 3)
  return undefined;
}

export default function ClassificaScreen() {
  const router = useRouter();
  const [leagueIdx, setLeagueIdx] = useState(0);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const league = LEAGUES[leagueIdx];

  useEffect(() => {
    loadClassifica();
  }, [leagueIdx]);

  const loadClassifica = async () => {
    setLoading(true);
    setData([]);
    try {
      const res = await getClassifica(league.key);
      // La risposta ha la struttura { classifica: [...] }
      setData(res.data?.classifica || res.data || []);
    } catch (_) {}
    setLoading(false);
  };

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="classifica" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Classifiche</Text>

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

          {!loading && data.length > 0 && (
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {/* Header tabella - identico alla webapp: #, Squadra, PG, V, N, P, DR, PT */}
              <View style={[styles.tableRow, styles.tableHeader]}>
                <Text style={[styles.thCell, { width: 26 }]}>#</Text>
                <View style={{ width: 22 }} />{/* spazio badge */}
                <Text style={[styles.thCell, { flex: 1, textAlign: 'left' }]}>Squadra</Text>
                <Text style={styles.thCell}>PG</Text>
                <Text style={[styles.thCell, { color: Colors.green }]}>V</Text>
                <Text style={styles.thCell}>N</Text>
                <Text style={[styles.thCell, { color: Colors.red }]}>P</Text>
                <Text style={styles.thCell}>DR</Text>
                <Text style={[styles.thCell, { color: Colors.text, fontWeight: '700' }]}>PT</Text>
              </View>

              {data.map((team: any, idx: number) => {
                const squadra = team.Squadra || team.squadra || team.name || '';
                const punti   = team.Punti   ?? team.punti   ?? team.points ?? '—';
                const giocate = team.G       ?? team.giocate ?? team.played ?? '—';
                const vinte   = team.V       ?? team.vinte   ?? team.won    ?? '—';
                const pareggi = team.N       ?? team.pareggiate ?? team.drawn ?? '—';
                const perse   = team.P       ?? team.perse   ?? team.lost   ?? '—';
                const dr      = team.DR      ?? '';
                const zc      = zoneColor(idx, data.length);
                const badgeUrl = getTeamBadgeUrl(squadra);

                return (
                  <TouchableOpacity
                    key={idx}
                    style={[
                      styles.tableRow,
                      idx % 2 === 0 && { backgroundColor: 'rgba(255,255,255,0.02)' },
                      zc ? { borderLeftWidth: 3, borderLeftColor: zc } : { borderLeftWidth: 3, borderLeftColor: 'transparent' },
                    ]}
                    onPress={() => router.push(`/team/${encodeURIComponent(squadra)}` as any)}
                  >
                    {/* Posizione */}
                    <Text style={[styles.tdCell, { width: 26, color: Colors.muted }]}>{idx + 1}</Text>
                    {/* Badge logo squadra */}
                    <View style={{ width: 22, alignItems: 'center' }}>
                      {badgeUrl ? (
                        <Image source={{ uri: badgeUrl }} style={{ width: 18, height: 18, resizeMode: 'contain' }} />
                      ) : null}
                    </View>
                    {/* Nome squadra */}
                    <Text style={[styles.tdCell, { flex: 1, textAlign: 'left', color: Colors.text, fontWeight: '700' }]} numberOfLines={1}>
                      {squadra}
                    </Text>
                    {/* Statistiche */}
                    <Text style={styles.tdCell}>{giocate}</Text>
                    <Text style={[styles.tdCell, { color: Colors.green }]}>{vinte}</Text>
                    <Text style={styles.tdCell}>{pareggi}</Text>
                    <Text style={[styles.tdCell, { color: Colors.red }]}>{perse}</Text>
                    <Text style={[styles.tdCell, {
                      color: typeof dr === 'number' && dr > 0 ? Colors.green
                        : typeof dr === 'number' && dr < 0 ? Colors.red : Colors.muted,
                    }]}>
                      {typeof dr === 'number' && dr > 0 ? `+${dr}` : dr}
                    </Text>
                    <Text style={[styles.tdCell, { fontWeight: '800', color: Colors.text }]}>{punti}</Text>
                  </TouchableOpacity>
                );
              })}
            </Card>
          )}

          {!loading && data.length === 0 && (
            <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 32 }}>
              Impossibile caricare la classifica. Riprova.
            </Text>
          )}

          {/* LEGENDA ZONE - identica alla webapp */}
          {data.length > 0 && (
            <Card style={{ marginTop: 8 }}>
              <Text style={{ color: Colors.muted, fontSize: 12, marginBottom: 6 }}>Legenda zone</Text>
              {[
                { color: Colors.green, label: 'Champions League' },
                { color: Colors.yellow, label: 'Europa League' },
                { color: '#9b59b6', label: 'Conference League' },
                { color: Colors.red, label: 'Retrocessione' },
              ].map((z) => (
                <View key={z.label} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                  <View style={{ width: 12, height: 12, backgroundColor: z.color, borderRadius: 2, marginRight: 8 }} />
                  <Text style={{ color: Colors.muted, fontSize: 12 }}>{z.label}</Text>
                </View>
              ))}
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
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text, marginBottom: 16 },
  leagueTabs: { flexDirection: 'row' },
  leagueTab: { paddingHorizontal: 14, paddingVertical: 8, alignItems: 'center', minWidth: 52 },
  leagueTabText: { fontSize: 12, fontWeight: '700' },
  tableRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 6, paddingHorizontal: 8,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  tableHeader: { backgroundColor: Colors.surface },
  thCell: { width: 28, textAlign: 'center', color: Colors.muted, fontSize: 10, fontWeight: '700' },
  tdCell: { width: 28, textAlign: 'center', color: Colors.muted, fontSize: 12 },
});
