import { View, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { ThemedText } from './ThemedText';
import { Colors, Spacing, BorderRadius } from '../constants/theme';

// Interfaccia notizia ricevuta dal backend
interface Notizia {
  titolo: string;
  fonte: string;
  url: string;
  data?: string; // opzionale: data pubblicazione
}

interface NewsCardProps {
  notizia: Notizia;
}

// Apre il link della notizia nel browser
async function apriNotizia(url: string) {
  try {
    const supportato = await Linking.canOpenURL(url);
    if (supportato) {
      await Linking.openURL(url);
    }
  } catch (error) {
    console.error('Errore apertura link:', error);
  }
}

export function NewsCard({ notizia }: NewsCardProps) {
  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => apriNotizia(notizia.url)}
      activeOpacity={0.75}
    >
      {/* Punto colorato + fonte */}
      <View style={styles.header}>
        <View style={styles.dot} />
        <ThemedText type="small" color="muted" style={styles.fonte} numberOfLines={1}>
          {notizia.fonte}
        </ThemedText>
        {notizia.data && (
          <ThemedText type="small" color="muted" style={styles.data}>
            {notizia.data}
          </ThemedText>
        )}
      </View>

      {/* Titolo notizia */}
      <ThemedText type="caption" style={styles.titolo} numberOfLines={3}>
        {notizia.titolo}
      </ThemedText>

      {/* Label "Leggi" */}
      <View style={styles.footer}>
        <ThemedText type="small" style={styles.leggi}>
          Leggi →
        </ThemedText>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.xs,
    gap: Spacing.xs,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.primary,
  },
  fonte: {
    flex: 1,
    textTransform: 'uppercase',
    fontSize: 11,
    letterSpacing: 0.5,
  },
  data: {
    fontSize: 11,
  },
  titolo: {
    color: Colors.text,
    lineHeight: 20,
    marginBottom: Spacing.xs,
  },
  footer: {
    alignItems: 'flex-end',
  },
  leggi: {
    color: Colors.primary,
    fontWeight: '600',
  },
});
