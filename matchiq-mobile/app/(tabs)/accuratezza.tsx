/**
 * Accuratezza - Statistiche backtesting del modello IA, identica alla webapp.
 * FIX: l'API restituisce percentuali già in formato 0-100 (es. 68),
 * non 0-1 (es. 0.68). La webapp mostra direttamente ${t.acc_1x2}% senza moltiplicare.
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, ActivityIndicator,
} from 'react-native';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getAccuratezza } from '../../services/api';

interface GiornataAcc {
  campionato?: string;
  league_key?: string;
  giornata: number;
  ok_1x2?: number;
  totale?: number;
  partite?: number;
  acc_1x2: number;   // già in formato percentuale 0-100 (es. 68 = 68%)
  acc_ou: number;
  acc_goal: number;
  acc_alta?: number;
  ok_alta?: number;
  tot_alta?: number;
}

interface TotaleAcc {
  partite: number;
  acc_1x2: number;   // già in formato percentuale 0-100
  acc_ou: number;
  acc_goal: number;
  acc_alta: number;
  tot_alta: number;
}

/** Barra di progresso colorata (valore 0-100) */
function BarChart({ value, color }: { value: number; color: string }) {
  // Clamp tra 0 e 100 (valore già percentuale)
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  return (
    <View style={styles.barContainer}>
      <View style={[styles.barFill, { width: `${pct}%` as any, backgroundColor: color }]} />
    </View>
  );
}

export default function AccuratezzaScreen() {
  const [data, setData] = useState<{ giornate: GiornataAcc[]; totale: TotaleAcc } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAcc();
  }, []);

  const loadAcc = async () => {
    setLoading(true);
    try {
      const res = await getAccuratezza();
      setData(res.data);
    } catch (_) {}
    setLoading(false);
  };

  const t = data?.totale;

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="accuratezza" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Accuratezza del Modello IA</Text>
          <Text style={styles.pageSub}>
            Risultati del backtesting su partite reali della stagione 2025-2026
          </Text>

          {loading && <ActivityIndicator color={Colors.accent} style={{ marginTop: 32 }} />}

          {!loading && t && (
            <>
              {/* BOX TOTALI - 3 card identiche alla webapp */}
              <View style={styles.statsGrid}>
                <Card highlight="green" style={styles.statMini}>
                  <Text style={[styles.statMiniNum, { color: Colors.green }]}>{Math.round(t.acc_1x2)}%</Text>
                  <Text style={styles.statMiniLabel}>1X2</Text>
                  <Text style={styles.statMiniSub}>{t.partite} partite</Text>
                </Card>
                <Card style={styles.statMini}>
                  <Text style={[styles.statMiniNum, { color: Colors.accent }]}>{Math.round(t.acc_ou)}%</Text>
                  <Text style={styles.statMiniLabel}>Over/Under</Text>
                  <Text style={styles.statMiniSub}>O/U 2.5</Text>
                </Card>
                <Card highlight="green" style={styles.statMini}>
                  <Text style={[styles.statMiniNum, { color: Colors.green }]}>{Math.round(t.acc_alta)}%</Text>
                  <Text style={styles.statMiniLabel}>Alta conf.</Text>
                  <Text style={styles.statMiniSub}>{t.tot_alta} partite</Text>
                </Card>
              </View>

              {/* RIEPILOGO CON BARRE DI PROGRESSO */}
              <Card highlight="green">
                <Text style={styles.cardTitle}>Riepilogo Complessivo</Text>
                <Text style={{ color: Colors.muted, fontSize: 13, marginBottom: 16 }}>
                  Su {t.partite} partite analizzate
                </Text>

                {[
                  { label: '1X2 (Risultato)',    value: t.acc_1x2,  color: Colors.green },
                  { label: 'Over/Under 2.5',      value: t.acc_ou,   color: Colors.yellow },
                  { label: 'Goal/NoGoal',          value: t.acc_goal, color: Colors.accent },
                  { label: 'Confidenza Alta',      value: t.acc_alta, color: Colors.green },
                ].map((item) => (
                  <View key={item.label} style={styles.statRow}>
                    <View style={styles.statLabelRow}>
                      <Text style={styles.statLabel}>{item.label}</Text>
                      {/* Valore già percentuale: mostrare direttamente senza *100 */}
                      <Text style={[styles.statPct, { color: item.color }]}>
                        {Math.round(item.value)}%
                      </Text>
                    </View>
                    <BarChart value={item.value} color={item.color} />
                  </View>
                ))}

                {t.tot_alta > 0 && (
                  <Text style={{ color: Colors.muted, fontSize: 12, marginTop: 12 }}>
                    * Confidenza Alta: {t.tot_alta} partite analizzate
                  </Text>
                )}
              </Card>

              {/* NOTA */}
              <Card style={{ backgroundColor: '#0d1b2a', borderColor: Colors.accent }}>
                <Text style={{ color: Colors.text, fontSize: 14, lineHeight: 22, textAlign: 'center' }}>
                  Quando l'IA ha confidenza Alta, centra il risultato 1X2{' '}
                  <Text style={{ color: Colors.green, fontWeight: '700' }}>2 volte su 3</Text>.{'\n'}
                  Questi dati sono aggiornati in tempo reale.
                </Text>
              </Card>

              {/* TABELLA DETTAGLIO PER GIORNATA - identica alla webapp */}
              {data?.giornate && data.giornate.length > 0 && (
                <Card style={{ padding: 0, overflow: 'hidden' }}>
                  <View style={[styles.tableRow, styles.tableHeader]}>
                    <Text style={[styles.thCell, { flex: 1, textAlign: 'left' }]}>Giornata</Text>
                    <Text style={styles.thCell}>Partite</Text>
                    <Text style={styles.thCell}>1X2</Text>
                    <Text style={styles.thCell}>O/U</Text>
                    <Text style={styles.thCell}>Goal</Text>
                  </View>
                  {data.giornate.slice(-10).reverse().map((g, idx) => {
                    // acc_1x2 già percentuale — colore in base al valore
                    const colAcc = g.acc_1x2 >= 70 ? Colors.green
                      : g.acc_1x2 >= 50 ? Colors.yellow : Colors.red;
                    return (
                      <View key={idx} style={styles.tableRow}>
                        <View style={{ flex: 1 }}>
                          {g.campionato && (
                            <Text style={{ color: Colors.accent, fontSize: 10 }}>{g.campionato}</Text>
                          )}
                          <Text style={{ color: Colors.text, fontSize: 12 }}>G.{g.giornata}</Text>
                        </View>
                        <Text style={styles.tdCell}>{g.ok_1x2 !== undefined ? `${g.ok_1x2}/${g.totale || g.partite}` : (g.partite ?? '—')}</Text>
                        <Text style={[styles.tdCell, { color: colAcc }]}>{Math.round(g.acc_1x2)}%</Text>
                        <Text style={[styles.tdCell, { color: Colors.yellow }]}>{Math.round(g.acc_ou)}%</Text>
                        <Text style={[styles.tdCell, { color: Colors.green }]}>{Math.round(g.acc_goal)}%</Text>
                      </View>
                    );
                  })}
                </Card>
              )}
            </>
          )}

          {!loading && !t && (
            <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 32 }}>
              Impossibile caricare le statistiche. Riprova.
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
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text, marginBottom: 4 },
  pageSub: { color: Colors.muted, fontSize: 13, marginBottom: 16, lineHeight: 18 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 8 },
  statRow: { marginBottom: 12 },
  statLabelRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  statLabel: { color: Colors.text, fontSize: 14 },
  statPct: { fontSize: 16, fontWeight: '800' },
  barContainer: {
    height: 8, borderRadius: 4, backgroundColor: Colors.border, overflow: 'hidden',
  },
  barFill: { height: '100%', borderRadius: 4 },
  statsGrid: { flexDirection: 'row', gap: 8, marginBottom: 4 },
  statMini: { flex: 1, alignItems: 'center', padding: 12 },
  statMiniNum: { fontSize: 22, fontWeight: '800', color: Colors.accent },
  statMiniLabel: { color: Colors.text, fontSize: 12, fontWeight: '600', marginTop: 4 },
  statMiniSub: { color: Colors.muted, fontSize: 10, marginTop: 2 },
  tableRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 8,
    paddingHorizontal: 12, borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  tableHeader: { backgroundColor: Colors.surface },
  thCell: { width: 48, textAlign: 'center', color: Colors.muted, fontSize: 11, fontWeight: '700' },
  tdCell: { width: 48, textAlign: 'center', color: Colors.muted, fontSize: 13 },
});
