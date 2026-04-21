import { View, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ThemedText } from '../../components/ThemedText';
import { ThemedView } from '../../components/ThemedView';
import { PlayerRow } from '../../components/PlayerRow';
import { PitchView } from '../../components/PitchView';
import { Colors, Spacing, BorderRadius } from '../../constants/theme';
import { getSquadra } from '../../services/api';

// ─── Tipi ────────────────────────────────────────────────────────────────────

interface Formazione {
  modulo: string;
  titolari: string[];
}

interface Infortunato {
  nome: string;
  tipo: string;       // "infortunio" | "squalifica" | "dubbio"
  dettaglio: string;
}

interface Giocatore {
  nome: string;
  ruolo: string;     // "P" | "D" | "C" | "A"
  numero: number;
}

interface DatiSquadra {
  nome: string;
  allenatore: string;
  formazione: Formazione | null;
  infortunati: Infortunato[];
  rosa: Giocatore[];
  ultimo_aggiornamento: string;
}

// ─── Colore badge per tipo infortunio ────────────────────────────────────────

function coloreTipo(tipo: string): string {
  switch (tipo) {
    case 'squalifica': return Colors.warning;
    case 'dubbio': return Colors.accent;
    default: return Colors.danger;
  }
}

// ─── Schermata Dettaglio Squadra ─────────────────────────────────────────────

export default function TeamScreen() {
  const { nome } = useLocalSearchParams<{ nome: string }>();

  const [dati, setDati] = useState<DatiSquadra | null>(null);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [tabRosa, setTabRosa] = useState<'modulo' | 'rosa' | 'inj'>('modulo');

  useEffect(() => {
    if (nome) caricaDati();
  }, [nome]);

  // Carica dati squadra dall'endpoint /api/squadra/{nome}
  const caricaDati = async () => {
    setErrore(null);
    try {
      const response = await getSquadra(nome as string);
      setDati(response.data);
    } catch (err) {
      setErrore('Impossibile caricare i dati della squadra. Riprova.');
      console.error('Errore squadra:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    caricaDati();
  };

  // Costruisce set di nomi infortunati per evidenziare nella rosa
  const nomiInfortunati = new Set(
    (dati?.infortunati ?? []).map((i) => i.nome.toLowerCase())
  );

  // Costruisce set di nomi titolari per evidenziarli nella rosa
  const nomiTitolari = new Set(
    (dati?.formazione?.titolari ?? []).map((n) => n.toLowerCase())
  );

  if (loading) {
    return (
      <View style={styles.centered}>
        <ThemedText color="muted">Caricamento squadra...</ThemedText>
      </View>
    );
  }

  if (errore || !dati) {
    return (
      <View style={styles.centered}>
        <ThemedText color="danger">{errore ?? 'Dati non disponibili'}</ThemedText>
        <TouchableOpacity onPress={caricaDati} style={styles.retryBtn}>
          <ThemedText type="caption" color="muted">Riprova</ThemedText>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
      }
    >
      {/* Intestazione squadra */}
      <ThemedView style={styles.header}>
        <ThemedText type="h1" style={styles.nomeSquadra}>{dati.nome}</ThemedText>
        <View style={styles.allenatoreBadge}>
          <ThemedText type="small" color="muted">Allenatore:</ThemedText>
          <ThemedText type="caption" style={styles.allenatoreNome}>{dati.allenatore}</ThemedText>
        </View>
        {dati.formazione?.modulo && (
          <ThemedText type="small" color="muted">Modulo: {dati.formazione.modulo}</ThemedText>
        )}
        {dati.ultimo_aggiornamento ? (
          <ThemedText type="small" color="muted" style={styles.aggiornamento}>
            Aggiornato: {dati.ultimo_aggiornamento}
          </ThemedText>
        ) : null}
      </ThemedView>

      {/* Tab selector */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, tabRosa === 'modulo' && styles.tabAttivo]}
          onPress={() => setTabRosa('modulo')}
        >
          <ThemedText
            type="small"
            style={{ color: tabRosa === 'modulo' ? Colors.background : Colors.textSecondary }}
          >
            Formazione
          </ThemedText>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, tabRosa === 'rosa' && styles.tabAttivo]}
          onPress={() => setTabRosa('rosa')}
        >
          <ThemedText
            type="small"
            style={{ color: tabRosa === 'rosa' ? Colors.background : Colors.textSecondary }}
          >
            Rosa
          </ThemedText>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, tabRosa === 'inj' && styles.tabAttivo]}
          onPress={() => setTabRosa('inj')}
        >
          <View style={styles.tabInner}>
            <ThemedText
              type="small"
              style={{ color: tabRosa === 'inj' ? Colors.background : Colors.textSecondary }}
            >
              Infortunati
            </ThemedText>
            {dati.infortunati.length > 0 && (
              <View style={styles.badge}>
                <ThemedText style={styles.badgeText}>{dati.infortunati.length}</ThemedText>
              </View>
            )}
          </View>
        </TouchableOpacity>
      </View>

      {/* Contenuto tab FORMAZIONE */}
      {tabRosa === 'modulo' && (
        <View style={styles.section}>
          {dati.formazione && dati.formazione.titolari.length >= 11 ? (
            <>
              {/* Vista campo semplificata */}
              <PitchView formazione={dati.formazione} />

              {/* Lista titolari */}
              <ThemedView variant="card" style={styles.tableCard}>
                <ThemedText type="caption" color="muted" style={styles.subTitle}>
                  Formazione titolare
                </ThemedText>
                {dati.formazione.titolari.map((nomeGiocatore, idx) => {
                  // Cerca il giocatore nella rosa per avere numero e ruolo
                  const datiGiocatore = dati.rosa.find(
                    (g) => g.nome.toLowerCase() === nomeGiocatore.toLowerCase()
                  );
                  const giocatore = datiGiocatore ?? {
                    nome: nomeGiocatore,
                    ruolo: idx === 0 ? 'P' : 'C',
                    numero: 0,
                  };
                  const isInj = nomiInfortunati.has(nomeGiocatore.toLowerCase());
                  return (
                    <PlayerRow
                      key={idx}
                      giocatore={{ ...giocatore, infortunato: isInj }}
                      inTeam
                    />
                  );
                })}
              </ThemedView>
            </>
          ) : (
            <ThemedView variant="card" style={styles.centeredBox}>
              <ThemedText color="muted">Formazione non ancora disponibile</ThemedText>
            </ThemedView>
          )}
        </View>
      )}

      {/* Contenuto tab ROSA */}
      {tabRosa === 'rosa' && (
        <View style={styles.section}>
          {dati.rosa.length > 0 ? (
            <ThemedView variant="card" style={styles.tableCard}>
              {/* Intestazione */}
              <View style={[styles.tableHeader]}>
                <ThemedText type="small" color="muted" style={{ width: 24, textAlign: 'center' }}>#</ThemedText>
                <ThemedText type="small" color="muted" style={{ width: 38, textAlign: 'center' }}>Ruolo</ThemedText>
                <ThemedText type="small" color="muted" style={{ flex: 1, paddingLeft: Spacing.xs }}>Nome</ThemedText>
              </View>
              {['P', 'D', 'C', 'A'].map((ruolo) => {
                const giocatoriRuolo = dati.rosa.filter((g) => g.ruolo === ruolo);
                if (giocatoriRuolo.length === 0) return null;
                return giocatoriRuolo.map((g) => {
                  const isInj = nomiInfortunati.has(g.nome.toLowerCase());
                  const isTit = nomiTitolari.has(g.nome.toLowerCase());
                  return (
                    <PlayerRow
                      key={g.nome}
                      giocatore={{ ...g, infortunato: isInj }}
                      inTeam={isTit}
                    />
                  );
                });
              })}
            </ThemedView>
          ) : (
            <ThemedView variant="card" style={styles.centeredBox}>
              <ThemedText color="muted">Rosa non disponibile</ThemedText>
            </ThemedView>
          )}
        </View>
      )}

      {/* Contenuto tab INFORTUNATI */}
      {tabRosa === 'inj' && (
        <View style={styles.section}>
          {dati.infortunati.length > 0 ? (
            <ThemedView variant="card" style={styles.tableCard}>
              {dati.infortunati.map((inj, idx) => (
                <View key={idx} style={[styles.injRow, idx > 0 && { borderTopWidth: 1, borderTopColor: Colors.border }]}>
                  <View style={styles.injLeft}>
                    <ThemedText type="caption" style={{ color: Colors.text }}>{inj.nome}</ThemedText>
                    <ThemedText type="small" color="muted">{inj.dettaglio}</ThemedText>
                  </View>
                  <View style={[styles.tipoBadge, { borderColor: coloreTipo(inj.tipo) }]}>
                    <ThemedText style={{ color: coloreTipo(inj.tipo), fontSize: 11, fontWeight: '700' }}>
                      {inj.tipo.toUpperCase()}
                    </ThemedText>
                  </View>
                </View>
              ))}
            </ThemedView>
          ) : (
            <ThemedView variant="card" style={styles.centeredBox}>
              <ThemedText color="muted">Nessun infortunato in elenco</ThemedText>
            </ThemedView>
          )}
        </View>
      )}

      <View style={{ height: Spacing.xl }} />
    </ScrollView>
  );
}

// ─── Stili ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
    padding: Spacing.xl,
  },
  header: {
    padding: Spacing.lg,
    paddingTop: Spacing.xl,
    gap: Spacing.xs,
  },
  nomeSquadra: {
    color: Colors.text,
  },
  allenatoreBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    marginTop: Spacing.xs,
  },
  allenatoreNome: {
    color: Colors.primary,
    fontWeight: '600',
  },
  aggiornamento: {
    marginTop: Spacing.xs,
  },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: 3,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tab: {
    flex: 1,
    paddingVertical: Spacing.xs + 2,
    alignItems: 'center',
    borderRadius: BorderRadius.sm,
  },
  tabAttivo: {
    backgroundColor: Colors.primary,
  },
  tabInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  badge: {
    backgroundColor: Colors.danger,
    borderRadius: BorderRadius.full,
    width: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  section: {
    paddingHorizontal: Spacing.md,
  },
  subTitle: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.surfaceLight,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  tableCard: {
    padding: 0,
    overflow: 'hidden',
    marginTop: Spacing.sm,
  },
  tableHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.surfaceLight,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  centeredBox: {
    alignItems: 'center',
    paddingVertical: Spacing.xl,
  },
  injRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
  },
  injLeft: {
    flex: 1,
    gap: 2,
  },
  tipoBadge: {
    borderWidth: 1,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.xs,
    paddingVertical: 2,
  },
  retryBtn: {
    marginTop: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
});
