import { View, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useEffect, useState } from 'react';
import { ThemedText } from '../../components/ThemedText';
import { ThemedView } from '../../components/ThemedView';
import { Colors, Spacing, BorderRadius, Typography } from '../../constants/theme';
import { getFixtureDetail } from '../../services/api';

// ─── Tipi ───────────────────────────────────────────────────────────────────

interface Evento {
  minuto: string;
  tipo: string;        // 'Goal', 'Card', 'subst', ecc.
  dettaglio: string;   // 'Normal Goal', 'Yellow Card', 'Red Card', 'Penalty', ecc.
  giocatore: string;
  assist?: string;
  squadra: 'home' | 'away';
}

interface FixtureDetail {
  fixture_id: number;
  home: string;
  away: string;
  gol_h: number;
  gol_a: number;
  status: string;
  status_it: string;
  minuto: number | null;
  live: boolean;
  data: string;
  ora: string;
  arbitro?: string;
  stadio?: string;
  citta?: string;
  eventi: Evento[];
}

// ─── Icone evento ─────────────────────────────────────────────────────────────

function iconaEvento(tipo: string, dettaglio: string): string {
  if (tipo === 'Goal') {
    if (dettaglio === 'Penalty') return '⚽ (R)';
    if (dettaglio === 'Own Goal') return '⚽ (aut.)';
    return '⚽';
  }
  if (tipo === 'Card') {
    if (dettaglio === 'Yellow Card') return '🟨';
    if (dettaglio === 'Red Card') return '🟥';
    if (dettaglio === 'Yellow Red Card') return '🟨🟥';
  }
  if (tipo === 'subst') return '🔄';
  if (tipo === 'Var') return '📺';
  return '•';
}

// ─── Colore sfondo evento ─────────────────────────────────────────────────────

function coloreSfondoEvento(tipo: string, dettaglio: string): string {
  if (tipo === 'Goal') return Colors.primary + '22';
  if (tipo === 'Card' && dettaglio === 'Red Card') return Colors.danger + '22';
  if (tipo === 'Card') return Colors.accent + '22';
  return Colors.surfaceLight;
}

// ─── Riga evento nella timeline ───────────────────────────────────────────────

function RigaEvento({ evento, isHome }: { evento: Evento; isHome: boolean }) {
  const icona = iconaEvento(evento.tipo, evento.dettaglio);
  const sfondo = coloreSfondoEvento(evento.tipo, evento.dettaglio);

  return (
    <View
      style={[
        styles.eventoRow,
        isHome ? styles.eventoHome : styles.eventoAway,
        { backgroundColor: sfondo },
      ]}
    >
      {/* Icona + minuto al centro (o lato) */}
      {isHome ? (
        <>
          <View style={styles.eventoInfo}>
            <ThemedText type="caption" style={{ color: Colors.text }}>{evento.giocatore}</ThemedText>
            {evento.assist ? (
              <ThemedText type="small" color="muted">Assist: {evento.assist}</ThemedText>
            ) : null}
          </View>
          <View style={styles.eventoMinuto}>
            <ThemedText type="small" style={{ fontSize: 16 }}>{icona}</ThemedText>
            <ThemedText type="small" color="muted">{evento.minuto}</ThemedText>
          </View>
        </>
      ) : (
        <>
          <View style={styles.eventoMinuto}>
            <ThemedText type="small" color="muted">{evento.minuto}</ThemedText>
            <ThemedText type="small" style={{ fontSize: 16 }}>{icona}</ThemedText>
          </View>
          <View style={[styles.eventoInfo, { alignItems: 'flex-end' }]}>
            <ThemedText type="caption" style={{ color: Colors.text }}>{evento.giocatore}</ThemedText>
            {evento.assist ? (
              <ThemedText type="small" color="muted">Assist: {evento.assist}</ThemedText>
            ) : null}
          </View>
        </>
      )}
    </View>
  );
}

// ─── Schermata Dettaglio Partita ──────────────────────────────────────────────

export default function MatchDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [dati, setDati] = useState<FixtureDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);

  useEffect(() => {
    if (id) caricaDettaglio();
  }, [id]);

  const caricaDettaglio = async () => {
    setLoading(true);
    setErrore(null);
    try {
      const response = await getFixtureDetail(id!);
      setDati(response.data);
    } catch (err) {
      setErrore('Impossibile caricare i dettagli della partita.');
      console.error('Errore fixture detail:', err);
    } finally {
      setLoading(false);
    }
  };

  // Formatta data ISO in italiano
  const formattaData = (dataStr: string) => {
    if (!dataStr) return '';
    try {
      const d = new Date(dataStr);
      return d.toLocaleDateString('it-IT', {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      });
    } catch {
      return dataStr;
    }
  };

  // Filtra solo gol e cartellini nella timeline
  const eventiSignificativi = dati?.eventi?.filter(
    (e) => e.tipo === 'Goal' || e.tipo === 'Card'
  ) ?? [];

  const isLive = dati?.live;
  const statusColor = isLive ? Colors.danger : Colors.textMuted;

  return (
    <>
      {/* Configura l'header della Stack con il titolo della partita */}
      <Stack.Screen
        options={{
          title: dati ? `${dati.home} vs ${dati.away}` : 'Dettaglio Partita',
          headerStyle: { backgroundColor: Colors.surface },
          headerTintColor: Colors.text,
        }}
      />

      <ScrollView style={styles.container}>
        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <ThemedText color="muted" style={{ marginTop: Spacing.md }}>
              Caricamento partita...
            </ThemedText>
          </View>
        ) : errore ? (
          <ThemedView variant="card" style={styles.centeredBox}>
            <ThemedText color="danger">{errore}</ThemedText>
            <TouchableOpacity onPress={caricaDettaglio} style={styles.retryBtn}>
              <ThemedText type="caption" color="muted">Riprova</ThemedText>
            </TouchableOpacity>
          </ThemedView>
        ) : dati ? (
          <>
            {/* ── Hero score ────────────────────────────────────────────── */}
            <ThemedView variant="card" style={styles.heroCard}>
              {/* Stato partita */}
              <View style={styles.statoRow}>
                {isLive && (
                  <View style={styles.liveDot}>
                    <View style={styles.liveDotInner} />
                  </View>
                )}
                <ThemedText type="small" style={{ color: statusColor }}>
                  {isLive && dati.minuto ? `${dati.minuto}'` : dati.status_it}
                </ThemedText>
              </View>

              {/* Squadre e punteggio */}
              <View style={styles.scoreRow}>
                <ThemedText type="h2" style={styles.teamName} numberOfLines={2}>
                  {dati.home}
                </ThemedText>
                <View style={styles.scoreCentro}>
                  <ThemedText type="h1" style={styles.scoreTesto}>
                    {dati.gol_h} - {dati.gol_a}
                  </ThemedText>
                </View>
                <ThemedText
                  type="h2"
                  style={[styles.teamName, styles.teamNameAway]}
                  numberOfLines={2}
                >
                  {dati.away}
                </ThemedText>
              </View>
            </ThemedView>

            {/* ── Info partita ─────────────────────────────────────────── */}
            <ThemedView variant="card" style={styles.infoCard}>
              <ThemedText type="caption" color="secondary" style={styles.infoTitle}>
                Info Partita
              </ThemedText>
              {dati.stadio ? (
                <View style={styles.infoRow}>
                  <ThemedText type="small" color="muted">Stadio</ThemedText>
                  <ThemedText type="small">{dati.stadio}{dati.citta ? `, ${dati.citta}` : ''}</ThemedText>
                </View>
              ) : null}
              {dati.arbitro ? (
                <View style={styles.infoRow}>
                  <ThemedText type="small" color="muted">Arbitro</ThemedText>
                  <ThemedText type="small">{dati.arbitro}</ThemedText>
                </View>
              ) : null}
              <View style={styles.infoRow}>
                <ThemedText type="small" color="muted">Data</ThemedText>
                <ThemedText type="small">
                  {formattaData(dati.data)}{dati.ora ? ` - ${dati.ora}` : ''}
                </ThemedText>
              </View>
            </ThemedView>

            {/* ── Timeline eventi ──────────────────────────────────────── */}
            <ThemedView variant="card" style={styles.timelineCard}>
              <ThemedText type="caption" color="secondary" style={styles.infoTitle}>
                Cronaca
              </ThemedText>

              {/* Intestazione colonne */}
              <View style={styles.timelineHeader}>
                <ThemedText type="small" color="muted" style={{ flex: 1 }}>{dati.home}</ThemedText>
                <ThemedText type="small" color="muted" style={styles.timelineCenter}>Min</ThemedText>
                <ThemedText
                  type="small"
                  color="muted"
                  style={{ flex: 1, textAlign: 'right' }}
                >
                  {dati.away}
                </ThemedText>
              </View>

              {eventiSignificativi.length === 0 ? (
                <ThemedText color="muted" style={styles.nessunoEvento}>
                  Nessun evento disponibile
                </ThemedText>
              ) : (
                eventiSignificativi.map((ev, idx) => (
                  <RigaEvento
                    key={`${ev.minuto}-${ev.giocatore}-${idx}`}
                    evento={ev}
                    isHome={ev.squadra === 'home'}
                  />
                ))
              )}
            </ThemedView>

            {/* ── Tutti gli eventi (sostituzioni, VAR) ─────────────────── */}
            {dati.eventi && dati.eventi.length > eventiSignificativi.length && (
              <ThemedView variant="card" style={styles.allEventiCard}>
                <ThemedText type="caption" color="secondary" style={styles.infoTitle}>
                  Sostituzioni & Altro
                </ThemedText>
                {dati.eventi
                  .filter((e) => e.tipo !== 'Goal' && e.tipo !== 'Card')
                  .map((ev, idx) => (
                    <View key={`subst-${idx}`} style={styles.substRow}>
                      <ThemedText type="small" color="muted" style={styles.substMin}>
                        {ev.minuto}
                      </ThemedText>
                      <ThemedText type="small" color="secondary">
                        {ev.squadra === 'home' ? dati.home : dati.away}
                      </ThemedText>
                      <ThemedText type="small" style={{ flex: 1, marginLeft: Spacing.sm }}>
                        {ev.tipo === 'subst'
                          ? `🔄 ${ev.giocatore}${ev.assist ? ` → ${ev.assist}` : ''}`
                          : `${ev.tipo}: ${ev.giocatore}`}
                      </ThemedText>
                    </View>
                  ))}
              </ThemedView>
            )}

            <View style={{ height: Spacing.xl }} />
          </>
        ) : null}
      </ScrollView>
    </>
  );
}

// ─── Stili ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingBox: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 80,
  },
  centeredBox: {
    margin: Spacing.md,
    alignItems: 'center',
    paddingVertical: Spacing.xl,
  },
  retryBtn: {
    marginTop: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  heroCard: {
    margin: Spacing.md,
    marginTop: Spacing.lg,
  },
  statoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
    gap: Spacing.xs,
  },
  liveDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: Colors.danger + '44',
    alignItems: 'center',
    justifyContent: 'center',
  },
  liveDotInner: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.danger,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  teamName: {
    flex: 1,
    textAlign: 'left',
    color: Colors.text,
  },
  teamNameAway: {
    textAlign: 'right',
  },
  scoreCentro: {
    paddingHorizontal: Spacing.md,
    alignItems: 'center',
  },
  scoreTesto: {
    color: Colors.text,
    fontSize: 36,
    fontWeight: '800',
  },
  infoCard: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
  },
  infoTitle: {
    marginBottom: Spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  timelineCard: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
    padding: Spacing.md,
  },
  timelineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingBottom: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    marginBottom: Spacing.xs,
  },
  timelineCenter: {
    width: 40,
    textAlign: 'center',
  },
  eventoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: Spacing.xs,
    borderRadius: BorderRadius.sm,
    marginVertical: 2,
  },
  eventoHome: {
    justifyContent: 'flex-start',
  },
  eventoAway: {
    justifyContent: 'flex-end',
  },
  eventoInfo: {
    flex: 1,
    alignItems: 'flex-start',
  },
  eventoMinuto: {
    width: 50,
    alignItems: 'center',
    flexDirection: 'column',
  },
  nessunoEvento: {
    textAlign: 'center',
    paddingVertical: Spacing.md,
  },
  allEventiCard: {
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
  },
  substRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  substMin: {
    width: 36,
    textAlign: 'center',
  },
});
