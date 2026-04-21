/**
 * Schermata Mondiali 2026 - Gironi e pronostici partite.
 * Mostra tutti i gironi con classifica squadre e permette di calcolare pronostici.
 * Endpoint: GET /api/mondiali-2026/gironi, GET /api/pronostico/{home}/{away}
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  Alert,
} from 'react-native';
import { ThemedText } from '../components/ThemedText';
import { ThemedView } from '../components/ThemedView';
import { TopNavbar } from '../components/TopNavbar';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { getMondialiGironi, getMondialiPronostico } from '../services/api';

// Struttura di una squadra nel girone
interface SquadraGirone {
  squadra: string;
  punti: number;
  vinte: number;
  pareggiate: number;
  perse: number;
  gol_fatti: number;
  gol_subiti: number;
}

// Struttura di una partita del girone
interface PartitaGirone {
  home: string;
  away: string;
  round: string;
  status: string;
  gol_h: number | null;
  gol_a: number | null;
}

// Risposta completa dell'API mondiali
interface RispostaMondiali {
  gironi: Record<string, SquadraGirone[]>;
  partite_gironi: Record<string, PartitaGirone[]>;
  fasi_finale: Record<string, any[]>;
  totale_partite: number;
}

// Risposta pronostico
interface RispostaPronostico {
  suggerimento?: string;
  prob_1?: number;
  prob_x?: number;
  prob_2?: number;
  over_25?: number;
  goal_si?: number;
  confidence_label?: string;
  result?: { '1x2': string; goal: string; over: string };
  probs?: Record<string, number>;
}

export default function MondialiScreen() {
  const [dati, setDati] = useState<RispostaMondiali | null>(null);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);

  // Girone espanso (toggle)
  const [gironeAperto, setGironeAperto] = useState<string | null>(null);

  // Modal pronostico
  const [modalVisible, setModalVisible] = useState(false);
  const [partitaSelezionata, setPartitaSelezionata] = useState<{ home: string; away: string } | null>(null);
  const [pronostico, setPronostico] = useState<RispostaPronostico | null>(null);
  const [caricamentoPronostico, setCaricamentoPronostico] = useState(false);

  // Carica i dati gironi all'avvio
  useEffect(() => {
    caricaGironi();
  }, []);

  const caricaGironi = async () => {
    setCaricamento(true);
    setErrore(null);
    try {
      const res = await getMondialiGironi();
      setDati(res.data);
      // Apre il primo girone di default
      const lettere = Object.keys(res.data.gironi || {}).sort();
      if (lettere.length > 0) setGironeAperto(lettere[0]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Impossibile caricare i gironi del Mondiale.';
      setErrore(msg);
    } finally {
      setCaricamento(false);
    }
  };

  // Apre il modal e calcola il pronostico per la partita selezionata
  const apriPronostico = useCallback(async (home: string, away: string) => {
    setPartitaSelezionata({ home, away });
    setPronostico(null);
    setModalVisible(true);
    setCaricamentoPronostico(true);
    try {
      const res = await getMondialiPronostico(home, away);
      setPronostico(res.data as RispostaPronostico);
    } catch (err: any) {
      Alert.alert('Errore', 'Impossibile calcolare il pronostico per questa partita.');
      setModalVisible(false);
    } finally {
      setCaricamentoPronostico(false);
    }
  }, []);

  // Differenza reti di una squadra
  const diffReti = (sq: SquadraGirone) => {
    const diff = (sq.gol_fatti || 0) - (sq.gol_subiti || 0);
    return diff >= 0 ? `+${diff}` : `${diff}`;
  };

  if (caricamento) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
        <TopNavbar activeTab="mondiali" />
        <View style={styles.centrato}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <ThemedText type="caption" color="muted" style={{ marginTop: Spacing.md }}>
            Caricamento gironi...
          </ThemedText>
        </View>
      </View>
    );
  }

  if (errore) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
        <TopNavbar activeTab="mondiali" />
        <View style={styles.centrato}>
          <Ionicons name="alert-circle-outline" size={48} color={Colors.error} />
          <ThemedText type="body" color="muted" style={styles.messaggioVuoto}>{errore}</ThemedText>
          <TouchableOpacity style={styles.bottoneRiprova} onPress={caricaGironi}>
            <ThemedText color="primary">Riprova</ThemedText>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const lettereGironi = Object.keys(dati?.gironi || {}).sort();

  return (
    <>
      <TopNavbar activeTab="mondiali" />
      <ScrollView style={styles.container}>
        {/* Intestazione */}
        <ThemedView style={styles.header}>
          <View style={styles.headerRow}>
            <Ionicons name="globe" size={28} color={Colors.accent} />
            <ThemedText type="h1" style={{ marginLeft: Spacing.sm }}>
              Mondiali 2026
            </ThemedText>
          </View>
          <ThemedText type="caption" color="muted">
            FIFA World Cup — {dati?.totale_partite ?? 0} partite totali
          </ThemedText>
        </ThemedView>

        {/* Gironi */}
        {lettereGironi.length === 0 ? (
          <ThemedView style={styles.sezione}>
            <ThemedText color="muted" style={{ textAlign: 'center' }}>
              Nessun dato gironi disponibile al momento.
            </ThemedText>
          </ThemedView>
        ) : (
          lettereGironi.map((lettera) => {
            const squadre = dati!.gironi[lettera] || [];
            const partite = dati!.partite_gironi?.[lettera] || [];
            const aperto = gironeAperto === lettera;

            return (
              <ThemedView key={lettera} style={styles.gironeBox}>
                {/* Header girone (cliccabile) */}
                <TouchableOpacity
                  style={styles.gironeHeader}
                  onPress={() => setGironeAperto(aperto ? null : lettera)}
                >
                  <ThemedText type="h3">Girone {lettera}</ThemedText>
                  <Ionicons
                    name={aperto ? 'chevron-up' : 'chevron-down'}
                    size={20}
                    color={Colors.textSecondary}
                  />
                </TouchableOpacity>

                {aperto && (
                  <>
                    {/* Classifica girone */}
                    <View style={styles.intestazioneTabella}>
                      <ThemedText type="small" color="muted" style={styles.colSquadra}>Squadra</ThemedText>
                      <ThemedText type="small" color="muted" style={styles.colNum}>G</ThemedText>
                      <ThemedText type="small" color="muted" style={styles.colNum}>V</ThemedText>
                      <ThemedText type="small" color="muted" style={styles.colNum}>P</ThemedText>
                      <ThemedText type="small" color="muted" style={styles.colNum}>S</ThemedText>
                      <ThemedText type="small" color="muted" style={styles.colNum}>DR</ThemedText>
                      <ThemedText type="small" style={[styles.colNum, { color: Colors.primary }]}>Pts</ThemedText>
                    </View>

                    {squadre.map((sq, idx) => (
                      <View
                        key={sq.squadra}
                        style={[
                          styles.rigaSquadra,
                          idx < 2 && styles.qualificata,
                        ]}
                      >
                        <ThemedText type="small" style={styles.colSquadra} numberOfLines={1}>
                          {idx + 1}. {sq.squadra}
                        </ThemedText>
                        <ThemedText type="small" color="muted" style={styles.colNum}>
                          {(sq.vinte || 0) + (sq.pareggiate || 0) + (sq.perse || 0)}
                        </ThemedText>
                        <ThemedText type="small" color="muted" style={styles.colNum}>{sq.vinte || 0}</ThemedText>
                        <ThemedText type="small" color="muted" style={styles.colNum}>{sq.pareggiate || 0}</ThemedText>
                        <ThemedText type="small" color="muted" style={styles.colNum}>{sq.perse || 0}</ThemedText>
                        <ThemedText type="small" color="muted" style={styles.colNum}>{diffReti(sq)}</ThemedText>
                        <ThemedText type="small" style={[styles.colNum, { color: Colors.primary, fontWeight: '700' }]}>
                          {sq.punti || 0}
                        </ThemedText>
                      </View>
                    ))}

                    {/* Partite del girone */}
                    {partite.length > 0 && (
                      <>
                        <ThemedText type="small" color="muted" style={styles.titoloPartite}>
                          Partite
                        </ThemedText>
                        {partite.map((p, i) => (
                          <View key={i} style={styles.rigaPartita}>
                            <View style={styles.partitaInfo}>
                              <ThemedText type="small" style={{ fontWeight: '600' }} numberOfLines={1}>
                                {p.home}
                              </ThemedText>
                              <ThemedText type="small" color="muted"> vs </ThemedText>
                              <ThemedText type="small" style={{ fontWeight: '600' }} numberOfLines={1}>
                                {p.away}
                              </ThemedText>
                              {/* Risultato se disponibile */}
                              {p.gol_h != null && p.gol_a != null && (
                                <ThemedText type="small" color="primary" style={{ marginLeft: 4 }}>
                                  {p.gol_h}-{p.gol_a}
                                </ThemedText>
                              )}
                            </View>
                            {/* Bottone pronostico */}
                            <TouchableOpacity
                              style={styles.bottonePronostico}
                              onPress={() => apriPronostico(p.home, p.away)}
                            >
                              <Ionicons name="analytics-outline" size={14} color={Colors.primary} />
                              <ThemedText type="small" color="primary" style={{ marginLeft: 3 }}>
                                Pronostico
                              </ThemedText>
                            </TouchableOpacity>
                          </View>
                        ))}
                      </>
                    )}
                  </>
                )}
              </ThemedView>
            );
          })
        )}

        {/* Fasi finali (se presenti) */}
        {dati?.fasi_finale && Object.keys(dati.fasi_finale).length > 0 && (
          <ThemedView style={styles.sezione}>
            <ThemedText type="h3" style={{ marginBottom: Spacing.sm }}>Fasi Finali</ThemedText>
            {Object.entries(dati.fasi_finale).map(([fase, partite]) => (
              <View key={fase} style={{ marginBottom: Spacing.sm }}>
                <ThemedText type="small" style={{ color: Colors.accent, fontWeight: '700', marginBottom: 4 }}>
                  {fase}
                </ThemedText>
                {(partite as PartitaGirone[]).map((p, i) => (
                  <TouchableOpacity
                    key={i}
                    style={styles.rigaFaseFinale}
                    onPress={() => apriPronostico(p.home, p.away)}
                  >
                    <ThemedText type="small">{p.home} vs {p.away}</ThemedText>
                    <Ionicons name="analytics-outline" size={14} color={Colors.primary} />
                  </TouchableOpacity>
                ))}
              </View>
            ))}
          </ThemedView>
        )}

        <View style={{ height: Spacing.xl }} />
      </ScrollView>

      {/* Modal pronostico */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            {/* Header modal */}
            <View style={styles.modalHeader}>
              <ThemedText type="h3">Pronostico</ThemedText>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            {partitaSelezionata && (
              <ThemedText type="body" style={styles.nomePartita}>
                {partitaSelezionata.home} vs {partitaSelezionata.away}
              </ThemedText>
            )}

            {caricamentoPronostico ? (
              <View style={styles.centrato}>
                <ActivityIndicator size="large" color={Colors.primary} />
              </View>
            ) : pronostico ? (
              <View style={styles.contenutoPronostico}>
                {/* Esito principale */}
                <View style={styles.rigaPronostico}>
                  <ThemedText type="body" color="muted">Esito</ThemedText>
                  <ThemedText type="h2" color="primary">
                    {pronostico.result?.['1x2'] || pronostico.suggerimento || '–'}
                  </ThemedText>
                </View>
                {/* Over/Under */}
                <View style={styles.rigaPronostico}>
                  <ThemedText type="body" color="muted">Over 2.5</ThemedText>
                  <ThemedText type="body" color="primary">
                    {pronostico.result?.over ||
                      (pronostico.over_25 != null ? `${pronostico.over_25}%` : '–')}
                  </ThemedText>
                </View>
                {/* Goal/NoGoal */}
                <View style={styles.rigaPronostico}>
                  <ThemedText type="body" color="muted">Goal</ThemedText>
                  <ThemedText type="body" color="primary">
                    {pronostico.result?.goal ||
                      (pronostico.goal_si != null ? (pronostico.goal_si > 50 ? 'SI' : 'NO') : '–')}
                  </ThemedText>
                </View>
                {/* Confidenza */}
                {pronostico.confidence_label && (
                  <View style={styles.rigaPronostico}>
                    <ThemedText type="body" color="muted">Confidenza</ThemedText>
                    <ThemedText type="body" style={{ color: Colors.accent }}>
                      {pronostico.confidence_label}
                    </ThemedText>
                  </View>
                )}
                {/* Probabilità */}
                {(pronostico.prob_1 != null || pronostico.probs) && (
                  <View style={styles.probBox}>
                    <ThemedText type="small" color="muted" style={{ marginBottom: 6 }}>
                      Probabilità
                    </ThemedText>
                    {[
                      { key: '1 (Casa)', val: pronostico.prob_1 ?? pronostico.probs?.['1'] },
                      { key: 'X (Pareggio)', val: pronostico.prob_x ?? pronostico.probs?.['X'] },
                      { key: '2 (Trasferta)', val: pronostico.prob_2 ?? pronostico.probs?.['2'] },
                    ]
                      .filter(({ val }) => val != null)
                      .map(({ key, val }) => (
                        <View key={key} style={styles.probRiga}>
                          <ThemedText type="small" color="muted" style={{ width: 90 }}>{key}</ThemedText>
                          <View style={styles.probBar}>
                            <View style={[styles.probFill, { width: `${val as number}%` as `${number}%` }]} />
                          </View>
                          <ThemedText type="small">{val}%</ThemedText>
                        </View>
                      ))}
                  </View>
                )}
              </View>
            ) : null}
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centrato: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xl,
    marginTop: 60,
  },
  messaggioVuoto: {
    textAlign: 'center',
    marginTop: Spacing.md,
  },
  bottoneRiprova: {
    marginTop: Spacing.md,
    padding: Spacing.sm,
  },
  header: {
    padding: Spacing.lg,
    paddingTop: Spacing.xl,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.xs,
  },
  sezione: {
    margin: Spacing.md,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
  },
  // Girone
  gironeBox: {
    margin: Spacing.md,
    marginBottom: 0,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    overflow: 'hidden',
  },
  gironeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.md,
  },
  // Tabella classifica
  intestazioneTabella: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    paddingBottom: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  rigaSquadra: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  qualificata: {
    backgroundColor: `${Colors.primary}11`,
  },
  colSquadra: {
    flex: 1,
    marginRight: Spacing.xs,
  },
  colNum: {
    width: 28,
    textAlign: 'center',
  },
  // Partite nel girone
  titoloPartite: {
    margin: Spacing.md,
    marginBottom: Spacing.xs,
    fontWeight: '700',
  },
  rigaPartita: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: Spacing.sm,
  },
  partitaInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  bottonePronostico: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  // Fasi finali
  rigaFaseFinale: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  modalBox: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: Spacing.lg,
    minHeight: 300,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  nomePartita: {
    fontWeight: '600',
    marginBottom: Spacing.md,
    color: Colors.textSecondary,
  },
  contenutoPronostico: {
    gap: Spacing.sm,
  },
  rigaPronostico: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  probBox: {
    marginTop: Spacing.sm,
  },
  probRiga: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  probBar: {
    flex: 1,
    height: 8,
    backgroundColor: Colors.surfaceLight,
    borderRadius: 4,
    marginHorizontal: Spacing.sm,
    overflow: 'hidden',
  },
  probFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    borderRadius: 4,
  },
});
