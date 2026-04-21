import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { ThemedText } from './ThemedText';
import { ThemedView } from './ThemedView';
import { Colors, Spacing } from '../constants/theme';

type MatchCardProps = {
  homeTeam: string;
  awayTeam: string;
  homeScore?: number;
  awayScore?: number;
  time?: string;
  status?: 'live' | 'finished' | 'upcoming';
  prediction?: string;
  onPress?: () => void;
};

export function MatchCard({ 
  homeTeam, 
  awayTeam, 
  homeScore, 
  awayScore, 
  time, 
  status = 'upcoming',
  prediction,
  onPress 
}: MatchCardProps) {
  const statusColors = {
    live: Colors.danger,
    finished: Colors.textMuted,
    upcoming: Colors.primary,
  };

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.8}>
      <ThemedView variant="card" style={styles.card}>
        <View style={styles.header}>
          <View style={[styles.statusDot, { backgroundColor: statusColors[status] }]} />
          <ThemedText type="caption" color="muted">
            {time || 'Da definire'}
          </ThemedText>
        </View>

        <View style={styles.teamsContainer}>
          <View style={styles.team}>
            <ThemedText type="body">{homeTeam}</ThemedText>
            {homeScore !== undefined && (
              <ThemedText type="h2">{homeScore}</ThemedText>
            )}
          </View>

          <ThemedText type="h3" color="muted">VS</ThemedText>

          <View style={styles.team}>
            <ThemedText type="body">{awayTeam}</ThemedText>
            {awayScore !== undefined && (
              <ThemedText type="h2">{awayScore}</ThemedText>
            )}
          </View>
        </View>

        {prediction && (
          <View style={styles.prediction}>
            <ThemedText type="caption" color="accent">
              Pronostico: {prediction}
            </ThemedText>
          </View>
        )}
      </ThemedView>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: Spacing.md,
    marginVertical: Spacing.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: Spacing.sm,
  },
  teamsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  team: {
    alignItems: 'center',
    flex: 1,
  },
  prediction: {
    marginTop: Spacing.md,
    paddingTop: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    alignItems: 'center',
  },
});
