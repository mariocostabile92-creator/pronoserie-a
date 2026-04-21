import { View, StyleSheet } from 'react-native';
import { ThemedText } from './ThemedText';
import { Colors, Spacing, BorderRadius } from '../constants/theme';

// Interfaccia del giocatore ricevuta dal backend
interface Giocatore {
  nome: string;
  ruolo: string; // "P" = Portiere, "D" = Difensore, "C" = Centrocampista, "A" = Attaccante
  numero: number;
  infortunato?: boolean; // true se il giocatore è negli infortunati
}

interface PlayerRowProps {
  giocatore: Giocatore;
  inTeam?: boolean; // true se è nella formazione titolare
}

// Colore badge per ruolo
function getBadgeColor(ruolo: string): string {
  switch (ruolo) {
    case 'P': return Colors.info;
    case 'D': return Colors.primary;
    case 'C': return Colors.accent;
    case 'A': return Colors.danger;
    default: return Colors.textMuted;
  }
}

// Etichetta leggibile del ruolo
function getRuoloLabel(ruolo: string): string {
  switch (ruolo) {
    case 'P': return 'POR';
    case 'D': return 'DIF';
    case 'C': return 'CEN';
    case 'A': return 'ATT';
    default: return ruolo;
  }
}

export function PlayerRow({ giocatore, inTeam = false }: PlayerRowProps) {
  const badgeColor = getBadgeColor(giocatore.ruolo);

  return (
    <View style={[styles.row, inTeam && styles.rowTitolare]}>
      {/* Numero maglia */}
      <View style={styles.numero}>
        <ThemedText type="small" style={{ color: Colors.textSecondary, textAlign: 'center' }}>
          {giocatore.numero}
        </ThemedText>
      </View>

      {/* Badge ruolo */}
      <View style={[styles.badge, { backgroundColor: badgeColor + '30', borderColor: badgeColor }]}>
        <ThemedText type="small" style={{ color: badgeColor, fontWeight: '700', fontSize: 10 }}>
          {getRuoloLabel(giocatore.ruolo)}
        </ThemedText>
      </View>

      {/* Nome giocatore */}
      <ThemedText type="caption" style={styles.nome} numberOfLines={1}>
        {giocatore.nome}
      </ThemedText>

      {/* Badge infortunato (se applicabile) */}
      {giocatore.infortunato && (
        <View style={styles.injBadge}>
          <ThemedText style={styles.injText}>INF</ThemedText>
        </View>
      )}

      {/* Badge titolare (se nella formazione) */}
      {inTeam && !giocatore.infortunato && (
        <View style={styles.titolareBadge}>
          <ThemedText style={styles.titolareText}>TIT</ThemedText>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.xs + 2,
    paddingHorizontal: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: Spacing.xs,
  },
  rowTitolare: {
    backgroundColor: Colors.primary + '10',
  },
  numero: {
    width: 24,
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
    borderWidth: 1,
    minWidth: 34,
    alignItems: 'center',
  },
  nome: {
    flex: 1,
    color: Colors.text,
  },
  injBadge: {
    backgroundColor: Colors.danger + '30',
    borderColor: Colors.danger,
    borderWidth: 1,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: 5,
    paddingVertical: 2,
  },
  injText: {
    color: Colors.danger,
    fontSize: 10,
    fontWeight: '700',
  },
  titolareBadge: {
    backgroundColor: Colors.primary + '25',
    borderColor: Colors.primary,
    borderWidth: 1,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: 5,
    paddingVertical: 2,
  },
  titolareText: {
    color: Colors.primary,
    fontSize: 10,
    fontWeight: '700',
  },
});
