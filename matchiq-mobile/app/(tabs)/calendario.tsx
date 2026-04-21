/**
 * Calendario - Identico alla sezione #calendario della webapp.
 * Aggiunge: badge squadre + bottone "Simula Giornata" (come la webapp, riga 716).
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Image,
} from 'react-native';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getCalendario, getSchedina } from '../../services/api';
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

/** Badge logo squadra inline (come badge() in index.html) */
function TeamBadgeInline({ name, size = 18 }: { name: string; size?: number }) {
  const url = getTeamBadgeUrl(name);
  if (!url) return null;
  return <Image source={{ uri: url }} style={{ width: size, height: size, resizeMode: 'contain', marginHorizontal: 3 }} />;
}

export default function CalendarioScreen() {
  const [leagueIdx, setLeagueIdx]       = useState(0);
  const [data, setData]                 = useState<any>(null);
  const [loading, setLoading]           = useState(false);
  const [giornataSel, setGiornataSel]   = useState<number | null>(null);
  // Stato per la simulazione giornata
  const [simData, setSimData]           = useState<any>(null);
  const [simLoading, setSimLoading]     = useState(false);

  const league = LEAGUES[leagueIdx];

  useEffect(() => {
    loadCalendario();
  }, [leagueIdx]);

  const loadCalendario = async () => {
    setLoading(true);
    setData(null);
    setGiornataSel(null);
    setSimData(null);
    try {
      const res = await getCalendario(league.key);
      const d = res.data;
      setData(d);
      if (d.giornata_corrente) setGiornataSel(d.giornata_corrente);
    } catch (_) {}
    setLoading(false);
  };

  /**
   * Simula la giornata corrente chiamando l'endpoint /api/schedina (o equivalente).
   * Identico al bottone "Simula Pronostici Giornata" della webapp (riga 716 index.html).
   */
  const simulaGiornata = async () => {
    setSimLoading(true);
    setSimData(null);
    try {
      const res = await getSchedina(league.key);
      setSimData(res.data);
    } catch (_) {}
    setSimLoading(false);
  };

  const giornate: any[]   = data?.giornate || [];
  const giornataData      = giornate.find((g: any) => g.giornata === giornataSel);
  const isGiornataCorrente = giornataSel === data?.giornata_corrente;
  // Mostra il bottone "Simula" solo per la giornata corrente, non live e non completata
  const showSimulaBtn = isGiornataCorrente
    && giornataData
    && !giornataData.live
    && giornataData.stato !== 'completata';

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="calendario" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Calendario Partite</Text>

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
                  {giornate.map((g: any) => (
                    <TouchableOpacity
                      key={g.giornata}
                      onPress={() => { setGiornataSel(g.giornata); setSimData(null); }}
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
                <>
                  <Card style={giornataData.live ? { borderColor: Colors.red, borderWidth: 2 } : undefined}>
                    {/* Header giornata */}
                    <View style={styles.cardHeader}>
                      <Text style={[styles.cardTitle, { color: giornataData.live ? Colors.red : Colors.green }]}>
                        Giornata {giornataData.giornata}
                      </Text>
                      {giornataData.live && (
                        <View style={styles.liveBadge}><Text style={styles.liveBadgeText}>LIVE</Text></View>
                      )}
                    </View>
                    {giornataData.data ? (
                      <Text style={{ color: Colors.muted, fontSize: 13, marginBottom: 10 }}>{giornataData.data}</Text>
                    ) : null}

                    {/* BOTTONE SIMULA GIORNATA - identico alla webapp (riga 716) */}
                    {showSimulaBtn && (
                      <TouchableOpacity
                        style={styles.simulaBtn}
                        onPress={simulaGiornata}
                        disabled={simLoading}
                      >
                        <Text style={styles.simulaBtnText}>
                          {simLoading ? 'Simulazione in corso...' : 'Simula Pronostici Giornata'}
                        </Text>
                      </TouchableOpacity>
                    )}

                    {/* Lista partite con badge */}
                    {giornataData.partite?.map((p: any, i: number) => {
                      const hasResult = p.gol_h !== null && p.gol_h !== undefined;
                      const cH = hasResult
                        ? (p.gol_h > p.gol_a ? Colors.green : p.gol_h < p.gol_a ? Colors.red : Colors.yellow)
                        : Colors.text;
                      const cA = hasResult
                        ? (p.gol_a > p.gol_h ? Colors.green : p.gol_a < p.gol_h ? Colors.red : Colors.yellow)
                        : Colors.text;
                      const status = p.status === 'FT' ? 'FT'
                        : p.live ? `${p.minuto}'`
                        : p.status === 'HT' ? 'INT'
                        : p.ora || 'vs';
                      return (
                        <View key={i} style={[styles.partitaRow, p.live && { backgroundColor: 'rgba(231,76,60,0.08)', borderRadius: 6 }]}>
                          {/* Squadra casa: badge + nome (allineati a destra) */}
                          <View style={styles.teamSide}>
                            <Text style={[styles.teamName, { textAlign: 'right' }]} numberOfLines={1}>{p.home}</Text>
                            <TeamBadgeInline name={p.home} />
                          </View>
                          {/* Score / orario */}
                          <View style={styles.scoreBox}>
                            {hasResult ? (
                              <>
                                <Text style={styles.score}>
                                  <Text style={{ color: cH }}>{p.gol_h}</Text>
                                  <Text style={{ color: Colors.muted }}> - </Text>
                                  <Text style={{ color: cA }}>{p.gol_a}</Text>
                                </Text>
                                <Text style={[styles.statusText, p.live && { color: Colors.red }]}>{status}</Text>
                              </>
                            ) : (
                              <Text style={styles.statusText}>{status}</Text>
                            )}
                          </View>
                          {/* Squadra ospite: badge + nome */}
                          <View style={[styles.teamSide, { justifyContent: 'flex-start' }]}>
                            <TeamBadgeInline name={p.away} />
                            <Text style={styles.teamName} numberOfLines={1}>{p.away}</Text>
                          </View>
                        </View>
                      );
                    })}
                  </Card>

                  {/* RISULTATI SIMULAZIONE GIORNATA */}
                  {simLoading && (
                    <View style={{ alignItems: 'center', marginTop: 16 }}>
                      <ActivityIndicator color={Colors.green} />
                      <Text style={{ color: Colors.muted, marginTop: 8, fontSize: 13 }}>
                        Calcolo pronostici in corso...
                      </Text>
                    </View>
                  )}

                  {simData?.giocate?.length > 0 && (
                    <Card style={{ marginTop: 12, borderColor: Colors.green, borderWidth: 2 }}>
                      <Text style={[styles.cardTitle, { color: Colors.green, marginBottom: 10 }]}>
                        Pronostici IA - Giornata {simData.giornata}
                      </Text>
                      {/* Tabella pronostici - identica alla webapp (riga 860) */}
                      {/* Header */}
                      <View style={styles.simHeader}>
                        <Text style={[styles.simTh, { flex: 1, textAlign: 'left' }]}>Partita</Text>
                        <Text style={styles.simTh}>Tip</Text>
                        <Text style={styles.simTh}>O/U</Text>
                        <Text style={styles.simTh}>Goal</Text>
                      </View>
                      {simData.giocate.map((g: any, i: number) => {
                        const tipColor = g.tip === '1' ? Colors.green
                          : g.tip === 'X' ? Colors.yellow : Colors.red;
                        return (
                          <View key={i} style={styles.simRow}>
                            <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                              <TeamBadgeInline name={g.home} size={14} />
                              <Text style={{ color: Colors.text, fontSize: 12, fontWeight: '600' }} numberOfLines={1}>
                                {g.home} - {g.away}
                              </Text>
                              <TeamBadgeInline name={g.away} size={14} />
                            </View>
                            <View style={[styles.tipTag, { backgroundColor: tipColor }]}>
                              <Text style={{ color: '#000', fontWeight: '800', fontSize: 12 }}>{g.tip}</Text>
                            </View>
                            <Text style={[styles.simTd, { color: Colors.accent }]}>{g.over_under || '—'}</Text>
                            <Text style={[styles.simTd, { color: Colors.yellow }]}>{g.goal || '—'}</Text>
                          </View>
                        );
                      })}
                      {/* Quota totale */}
                      {simData.quota_totale && (
                        <View style={{ alignItems: 'center', marginTop: 10, padding: 8, backgroundColor: '#0d1b2a', borderRadius: 8 }}>
                          <Text style={{ color: Colors.muted, fontSize: 12 }}>Quota totale schedina:</Text>
                          <Text style={{ fontSize: 22, fontWeight: '800', color: Colors.green }}>{simData.quota_totale}</Text>
                        </View>
                      )}
                    </Card>
                  )}
                </>
              ) : (
                <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 24 }}>
                  Seleziona una giornata
                </Text>
              )}
            </>
          )}

          {!loading && !data && (
            <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 32 }}>
              Impossibile caricare il calendario. Riprova.
            </Text>
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
  giornataPill: {
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 20,
    backgroundColor: '#1f3460', borderWidth: 1, borderColor: Colors.border,
  },
  giornataPillText: { color: Colors.muted, fontSize: 12, fontWeight: '600' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text },
  liveBadge: { backgroundColor: Colors.red, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10 },
  liveBadgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  // Bottone Simula Giornata - stile identico a btn-green webapp
  simulaBtn: {
    backgroundColor: Colors.green,
    paddingVertical: 12, paddingHorizontal: 16,
    borderRadius: 10, alignItems: 'center', marginBottom: 12,
  },
  simulaBtnText: { color: '#000', fontWeight: '700', fontSize: 15 },
  partitaRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  teamSide: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 3 },
  teamName: { color: Colors.text, fontSize: 12, fontWeight: '600', flex: 1 },
  scoreBox: { minWidth: 70, alignItems: 'center' },
  score: { fontSize: 16, fontWeight: '800' },
  statusText: { color: Colors.muted, fontSize: 11, marginTop: 2, textAlign: 'center' },
  // Simulazione tabella
  simHeader: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 6,
    borderBottomWidth: 2, borderBottomColor: Colors.border,
  },
  simTh: { width: 50, textAlign: 'center', color: Colors.muted, fontSize: 10, fontWeight: '700' },
  simRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: Colors.border, gap: 4,
  },
  tipTag: {
    width: 28, height: 24, borderRadius: 6, alignItems: 'center', justifyContent: 'center',
  },
  simTd: { width: 50, textAlign: 'center', fontSize: 11, fontWeight: '600', color: Colors.muted },
});
