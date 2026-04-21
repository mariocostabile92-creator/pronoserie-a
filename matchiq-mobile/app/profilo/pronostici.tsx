/**
 * Storico pronostici personali dell'utente.
 * Mostra tutti i pronostici salvati con esito reale (se verificato).
 * Endpoint: GET /api/user/my-predictions (autenticazione richiesta)
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { ThemedText } from '../../components/ThemedText';
import { ThemedView } from '../../components/ThemedView';
import { Colors, Spacing, BorderRadius } from '../../constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { getMyPredictions } from '../../services/api';

// Struttura di un singolo pronostico salvato
interface Pronostico {
  id: number;
  league: string;
  home: string;
  away: string;
  pronostico: string;
  prob: number;
  confidence: string;
  over_under: string;
  goal: string;
  created_at: string;
  match_date: string;
  verificato: boolean;
  corretto: boolean | null;
  risultato_reale: string | null;
  gol_h_reale: number | null;
  gol_a_reale: number | null;
}

// Statistiche aggregate dei pronostici dell'utente
interface StatsPredizioni {
  totale: number;
  verificati: number;
  ok_1x2: number;
  ok_ou: number;
  ok_goal: number;
  acc_1x2: number;
  acc_ou: number;
  acc_goal: number;
}

export default function StoricoPronosticiScreen() {
  const { token } = useAuth();

  const [pronostici, setPronostici] = useState<Pronostico[]>([]);
  const [stats, setStats] = useState<StatsPredizioni | null>(null);
  const [caricamento, setCaricamento] = useState(true);
  const [aggiornamento, setAggiornamento] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  // Carica i pronostici dall'API
  const caricaPronostici = useCallback(async (refresh = false) => {
    if (refresh) setAggiornamento(true);
    else setCaricamento(true);
    setErrore(null);

    try {
      const res = await getMyPredictions();
      setPronostici(res.data.predictions);
      setStats(res.data.stats);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Impossibile caricare i pronostici.';
      setErrore(msg);
    } finally {
      setCaricamento(false);
      setAggiornamento(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      caricaPronostici();
    } else {
      setCaricamento(false);
    }
  }, [token]);

  // Formatta la data ISO in stringa leggibile
  const formatData = (iso: string): string => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' });
    } catch {
      return '–';
    }
  };

  // Colore in base al risultato corretto/errato/non verificato
  const coloreEsito = (corretto: boolean | null): string => {
    if (corretto === true) return Colors.success;
    if (corretto === false) return Colors.error;
    return Colors.textMuted;
  };

  // Icona in base all'esito
  const iconaEsito = (corretto: boolean | null) => {
    if (corretto === true) return 'checkmark-circle';
    if (corretto === false) return 'close-circle';
    return 'time-outline';
  };

  if (!token) {
    return (
      <View style={styles.centrato}>
        <Ionicons name="lock-closed-outline" size={48} color={Colors.textMuted} />
        <ThemedText type="body" color="muted" style={styles.messaggioVuoto}>
          Accedi per vedere i tuoi pronostici salvati.
        </ThemedText>
      </View>
    );
  }

  if (caricamento) {
    return (
      <View style={styles.centrato}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (errore) {
    return (
      <View style={styles.centrato}>
        <Ionicons name="alert-circle-outline" size={48} color={Colors.error} />
        <ThemedText type="body" color="muted" style={styles.messaggioVuoto}>{errore}</ThemedText>
        <TouchableOpacity style={styles.bottoneRiprova} onPress={() => caricaPronostici()}>
          <ThemedText color="primary">Riprova</ThemedText>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={aggiornamento}
          onRefresh={() => caricaPronostici(true)}
          tintColor={Colors.primary}
        />
      }
    >
      {/* Riepilogo statistiche personali */}
      {stats && stats.verificati > 0 && (
        <ThemedView style={styles.statsBox}>
          <ThemedText type="h3" style={styles.titoloStats}>Le tue statistiche</ThemedText>
          <View style={styles.rigaStats}>
            <View style={styles.statItem}>
              <ThemedText type="h2" color="primary">{stats.acc_1x2}%</ThemedText>
              <ThemedText type="small" color="muted">1X2</ThemedText>
            </View>
            <View style={styles.statItem}>
              <ThemedText type="h2" color="primary">{stats.acc_ou}%</ThemedText>
              <ThemedText type="small" color="muted">Over/Under</ThemedText>
            </View>
            <View style={styles.statItem}>
              <ThemedText type="h2" color="primary">{stats.acc_goal}%</ThemedText>
              <ThemedText type="small" color="muted">Goal/NoGoal</ThemedText>
            </View>
          </View>
          <ThemedText type="small" color="muted" style={styles.subtitleStats}>
            Su {stats.verificati} pronostici verificati (totale: {stats.totale})
          </ThemedText>
        </ThemedView>
      )}

      {/* Lista pronostici */}
      {pronostici.length === 0 ? (
        <View style={styles.centrato}>
          <Ionicons name="bookmark-outline" size={48} color={Colors.textMuted} />
          <ThemedText type="body" color="muted" style={styles.messaggioVuoto}>
            Nessun pronostico salvato. Calcolane uno e usa "Salva Pronostico"!
          </ThemedText>
        </View>
      ) : (
        <View style={styles.lista}>
          {pronostici.map((p) => (
            <ThemedView key={p.id} style={styles.cardPronostico}>
              {/* Header: home vs away */}
              <View style={styles.headerCard}>
                <ThemedText type="body" style={styles.nomeSq}>{p.home}</ThemedText>
                <ThemedText type="small" color="muted">vs</ThemedText>
                <ThemedText type="body" style={styles.nomeSq}>{p.away}</ThemedText>
              </View>

              {/* Dettagli: pronostico, over/under, goal */}
              <View style={styles.dettagliRiga}>
                <View style={styles.badge}>
                  <ThemedText type="small" color="primary">{p.pronostico}</ThemedText>
                </View>
                {p.over_under ? (
                  <View style={styles.badge}>
                    <ThemedText type="small" color="secondary">{p.over_under}</ThemedText>
                  </View>
                ) : null}
                {p.goal ? (
                  <View style={styles.badge}>
                    <ThemedText type="small" color="secondary">Goal: {p.goal}</ThemedText>
                  </View>
                ) : null}
                {p.confidence ? (
                  <View style={[styles.badge, { borderColor: Colors.accent }]}>
                    <ThemedText type="small" style={{ color: Colors.accent }}>{p.confidence}</ThemedText>
                  </View>
                ) : null}
              </View>

              {/* Esito reale (se verificato) */}
              <View style={styles.rigaEsito}>
                <Ionicons
                  name={iconaEsito(p.verificato ? p.corretto : null) as any}
                  size={18}
                  color={coloreEsito(p.verificato ? p.corretto : null)}
                />
                {p.verificato && p.risultato_reale ? (
                  <ThemedText type="small" style={{ color: coloreEsito(p.corretto), marginLeft: 4 }}>
                    Reale: {p.risultato_reale}
                    {p.gol_h_reale != null ? ` (${p.gol_h_reale}-${p.gol_a_reale})` : ''}
                  </ThemedText>
                ) : (
                  <ThemedText type="small" color="muted" style={{ marginLeft: 4 }}>
                    {p.verificato ? 'Verificato' : 'In attesa di risultato'}
                  </ThemedText>
                )}

                {/* Data salvataggio */}
                <ThemedText type="small" color="muted" style={styles.dataCard}>
                  {formatData(p.created_at)}
                </ThemedText>
              </View>

              {/* Lega */}
              {p.league ? (
                <ThemedText type="small" color="muted" style={styles.legaLabel}>
                  {p.league}
                </ThemedText>
              ) : null}
            </ThemedView>
          ))}
        </View>
      )}
    </ScrollView>
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
    marginTop: 80,
  },
  messaggioVuoto: {
    textAlign: 'center',
    marginTop: Spacing.md,
  },
  bottoneRiprova: {
    marginTop: Spacing.md,
    padding: Spacing.sm,
  },
  // Riquadro statistiche
  statsBox: {
    margin: Spacing.md,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  titoloStats: {
    marginBottom: Spacing.sm,
  },
  rigaStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  subtitleStats: {
    textAlign: 'center',
    marginTop: Spacing.sm,
  },
  // Lista card
  lista: {
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  cardPronostico: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.xs,
  },
  headerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.xs,
  },
  nomeSq: {
    flex: 1,
    fontWeight: '600',
  },
  dettagliRiga: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
  },
  badge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    borderColor: Colors.primary,
    backgroundColor: Colors.surfaceLight,
  },
  rigaEsito: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  dataCard: {
    marginLeft: 'auto',
  },
  legaLabel: {
    marginTop: 2,
    fontStyle: 'italic',
  },
});
