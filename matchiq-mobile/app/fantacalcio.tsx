/**
 * Schermata Fantacalcio - Consigli IA per la giornata di fantacalcio.
 * Mostra squadra tipo consigliata, giocatori da schierare e da evitare.
 * Endpoint: GET /api/fantacalcio/consigli/{giornata}
 */
import React, { useState, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import { ThemedText } from '../components/ThemedText';
import { ThemedView } from '../components/ThemedView';
import { TopNavbar } from '../components/TopNavbar';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { getFantacalcioConsigli } from '../services/api';

// Struttura di un singolo giocatore consigliato
interface GiocatoreConsigliato {
  giocatore: string;
  squadra: string;
  rating: number;
  avversario: string;
  motivazione: string;
}

// Giocatore da evitare
interface GiocatoreEvitare {
  giocatore: string;
  squadra: string;
  motivazione: string;
  tipo: string;
}

// Risposta completa dell'API fantacalcio
interface RispostaFantacalcio {
  giornata: number;
  data: string;
  consigli: {
    portieri: GiocatoreConsigliato[];
    difensori: GiocatoreConsigliato[];
    centrocampisti: GiocatoreConsigliato[];
    attaccanti: GiocatoreConsigliato[];
    evitare: GiocatoreEvitare[];
  };
  squadra_tipo: {
    portieri: Array<{ nome: string; squadra: string }>;
    difensori: Array<{ nome: string; squadra: string }>;
    centrocampisti: Array<{ nome: string; squadra: string }>;
    attaccanti: Array<{ nome: string; squadra: string }>;
    panchina: Array<{ nome: string; squadra: string }>;
    capitano: { nome: string; squadra: string } | null;
  };
  error?: string;
}

// Mappa ruolo → icona e colore
const RUOLO_CONFIG: Record<string, { icona: string; colore: string; etichetta: string }> = {
  portieri: { icona: 'hand-left-outline', colore: Colors.warning, etichetta: 'Portieri' },
  difensori: { icona: 'shield-outline', colore: Colors.info, etichetta: 'Difensori' },
  centrocampisti: { icona: 'swap-horizontal-outline', colore: Colors.primary, etichetta: 'Centrocampisti' },
  attaccanti: { icona: 'football-outline', colore: Colors.danger, etichetta: 'Attaccanti' },
};

export default function FantacalcioScreen() {
  const [giornataInput, setGiornataInput] = useState('');
  const [caricamento, setCaricamento] = useState(false);
  const [dati, setDati] = useState<RispostaFantacalcio | null>(null);
  const [errore, setErrore] = useState<string | null>(null);

  // Carica i consigli per la giornata selezionata
  const caricaConsigli = useCallback(async () => {
    const g = parseInt(giornataInput, 10);
    if (!g || g < 1 || g > 38) {
      setErrore('Inserisci un numero di giornata valido (1-38).');
      return;
    }

    setCaricamento(true);
    setErrore(null);
    setDati(null);

    try {
      const res = await getFantacalcioConsigli(g);
      if (res.data.error) {
        setErrore(res.data.error);
      } else {
        setDati(res.data);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Impossibile caricare i consigli fantacalcio.';
      setErrore(msg);
    } finally {
      setCaricamento(false);
    }
  }, [giornataInput]);

  return (
    <View style={styles.container}>
      <TopNavbar />
      <ScrollView>
      {/* Intestazione */}
      <ThemedView style={styles.header}>
        <View style={styles.headerRow}>
          <Ionicons name="football" size={28} color={Colors.primary} />
          <ThemedText type="h1" style={{ marginLeft: Spacing.sm }}>
            Fantacalcio IA
          </ThemedText>
        </View>
        <ThemedText type="caption" color="muted">
          Consigli intelligenti per la tua giornata
        </ThemedText>
      </ThemedView>

      {/* Selezione giornata */}
      <ThemedView style={styles.selezioneBox}>
        <ThemedText type="caption" color="muted">Seleziona giornata (1-38)</ThemedText>
        <View style={styles.selezioneRiga}>
          <TextInput
            style={styles.inputGiornata}
            value={giornataInput}
            onChangeText={setGiornataInput}
            placeholder="Es. 31"
            placeholderTextColor={Colors.textMuted}
            keyboardType="numeric"
            maxLength={2}
          />
          <TouchableOpacity
            style={[styles.bottoneCarica, caricamento && { opacity: 0.6 }]}
            onPress={caricaConsigli}
            disabled={caricamento}
          >
            {caricamento ? (
              <ActivityIndicator size="small" color={Colors.background} />
            ) : (
              <ThemedText style={styles.testoBottone}>Carica</ThemedText>
            )}
          </TouchableOpacity>
        </View>
      </ThemedView>

      {/* Errore */}
      {errore && (
        <ThemedView style={styles.boxErrore}>
          <Ionicons name="alert-circle-outline" size={20} color={Colors.error} />
          <ThemedText type="caption" style={{ color: Colors.error, marginLeft: Spacing.sm, flex: 1 }}>
            {errore}
          </ThemedText>
        </ThemedView>
      )}

      {/* Risultati */}
      {dati && (
        <>
          {/* Intestazione giornata */}
          <ThemedView style={styles.giornataHeader}>
            <ThemedText type="h2">Giornata {dati.giornata}</ThemedText>
            {dati.data ? (
              <ThemedText type="caption" color="muted">{dati.data}</ThemedText>
            ) : null}
          </ThemedView>

          {/* Squadra tipo */}
          {dati.squadra_tipo && (
            <ThemedView style={styles.sezione}>
              <View style={styles.titoloSezioneRiga}>
                <Ionicons name="people" size={20} color={Colors.accent} />
                <ThemedText type="h3" style={styles.titoloSezione}>Squadra Tipo Consigliata</ThemedText>
              </View>

              {/* Capitano */}
              {dati.squadra_tipo.capitano && (
                <View style={styles.capitanoBox}>
                  <Ionicons name="star" size={16} color={Colors.accent} />
                  <ThemedText type="body" style={{ marginLeft: Spacing.xs, color: Colors.accent }}>
                    Capitano: {dati.squadra_tipo.capitano.nome}
                    <ThemedText type="small" color="muted"> ({dati.squadra_tipo.capitano.squadra})</ThemedText>
                  </ThemedText>
                </View>
              )}

              {/* Titolari per reparto */}
              {(['portieri', 'difensori', 'centrocampisti', 'attaccanti'] as const).map((ruolo) => {
                const giocatori = dati.squadra_tipo[ruolo];
                if (!giocatori?.length) return null;
                const cfg = RUOLO_CONFIG[ruolo];
                return (
                  <View key={ruolo} style={styles.repartoSquadra}>
                    <ThemedText type="small" style={{ color: cfg.colore, fontWeight: '700', marginBottom: 4 }}>
                      {cfg.etichetta.toUpperCase()}
                    </ThemedText>
                    <View style={styles.giocatoriRiga}>
                      {giocatori.map((g, i) => (
                        <View key={i} style={[styles.chipGiocatore, { borderColor: cfg.colore }]}>
                          <ThemedText type="small">{g.nome}</ThemedText>
                          <ThemedText type="small" color="muted"> ({g.squadra})</ThemedText>
                        </View>
                      ))}
                    </View>
                  </View>
                );
              })}

              {/* Panchina */}
              {dati.squadra_tipo.panchina?.length > 0 && (
                <View style={styles.repartoSquadra}>
                  <ThemedText type="small" style={{ color: Colors.textMuted, fontWeight: '700', marginBottom: 4 }}>
                    PANCHINA
                  </ThemedText>
                  <View style={styles.giocatoriRiga}>
                    {dati.squadra_tipo.panchina.map((g, i) => (
                      <View key={i} style={styles.chipGiocatorePanchina}>
                        <ThemedText type="small" color="muted">{g.nome}</ThemedText>
                      </View>
                    ))}
                  </View>
                </View>
              )}
            </ThemedView>
          )}

          {/* Consigli per ruolo */}
          {(['portieri', 'difensori', 'centrocampisti', 'attaccanti'] as const).map((ruolo) => {
            const giocatori = dati.consigli[ruolo];
            if (!giocatori?.length) return null;
            const cfg = RUOLO_CONFIG[ruolo];
            return (
              <ThemedView key={ruolo} style={styles.sezione}>
                <View style={styles.titoloSezioneRiga}>
                  <Ionicons name={cfg.icona as any} size={20} color={cfg.colore} />
                  <ThemedText type="h3" style={styles.titoloSezione}>{cfg.etichetta}</ThemedText>
                </View>
                {giocatori.map((g, i) => (
                  <View key={i} style={styles.rigaGiocatore}>
                    <View style={styles.infoGiocatore}>
                      <ThemedText type="body" style={{ fontWeight: '600' }}>{g.giocatore}</ThemedText>
                      <ThemedText type="small" color="muted">
                        {g.squadra} vs {g.avversario}
                      </ThemedText>
                      {g.motivazione ? (
                        <ThemedText type="small" color="muted" style={{ fontStyle: 'italic' }}>
                          {g.motivazione}
                        </ThemedText>
                      ) : null}
                    </View>
                    <View style={[styles.ratingBadge, { borderColor: cfg.colore }]}>
                      <ThemedText type="small" style={{ color: cfg.colore, fontWeight: '700' }}>
                        {typeof g.rating === 'number' ? g.rating.toFixed(1) : g.rating}
                      </ThemedText>
                    </View>
                  </View>
                ))}
              </ThemedView>
            );
          })}

          {/* Giocatori da evitare */}
          {dati.consigli.evitare?.length > 0 && (
            <ThemedView style={[styles.sezione, styles.sezioneEvitare]}>
              <View style={styles.titoloSezioneRiga}>
                <Ionicons name="close-circle-outline" size={20} color={Colors.danger} />
                <ThemedText type="h3" style={[styles.titoloSezione, { color: Colors.danger }]}>
                  Da Evitare
                </ThemedText>
              </View>
              {dati.consigli.evitare.map((g, i) => (
                <View key={i} style={styles.rigaEvitare}>
                  <Ionicons name="warning-outline" size={16} color={Colors.danger} />
                  <View style={{ marginLeft: Spacing.sm, flex: 1 }}>
                    <ThemedText type="body" style={{ fontWeight: '600' }}>{g.giocatore}</ThemedText>
                    <ThemedText type="small" color="muted">
                      {g.squadra} — {g.motivazione}
                    </ThemedText>
                  </View>
                </View>
              ))}
            </ThemedView>
          )}
        </>
      )}

      <View style={{ height: Spacing.xl }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
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
  // Selezione giornata
  selezioneBox: {
    margin: Spacing.md,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
  },
  selezioneRiga: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  inputGiornata: {
    flex: 1,
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.sm,
    padding: Spacing.sm,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
    fontSize: 16,
    textAlign: 'center',
  },
  bottoneCarica: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    minWidth: 80,
  },
  testoBottone: {
    color: Colors.background,
    fontWeight: '700',
  },
  // Errore
  boxErrore: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: Spacing.md,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    borderColor: Colors.error,
  },
  // Header giornata
  giornataHeader: {
    margin: Spacing.md,
    marginBottom: 0,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
  },
  // Sezioni generiche
  sezione: {
    margin: Spacing.md,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
  },
  sezioneEvitare: {
    borderWidth: 1,
    borderColor: Colors.danger,
  },
  titoloSezioneRiga: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.xs,
  },
  titoloSezione: {
    marginLeft: Spacing.sm,
  },
  // Squadra tipo
  capitanoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceLight,
    padding: Spacing.sm,
    borderRadius: BorderRadius.sm,
  },
  repartoSquadra: {
    marginBottom: Spacing.xs,
  },
  giocatoriRiga: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
  },
  chipGiocatore: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    backgroundColor: Colors.surfaceLight,
  },
  chipGiocatorePanchina: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surfaceLight,
  },
  // Righe giocatori per ruolo
  rigaGiocatore: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: Spacing.sm,
  },
  infoGiocatore: {
    flex: 1,
    gap: 2,
  },
  ratingBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    minWidth: 40,
    alignItems: 'center',
  },
  // Giocatori da evitare
  rigaEvitare: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
});
