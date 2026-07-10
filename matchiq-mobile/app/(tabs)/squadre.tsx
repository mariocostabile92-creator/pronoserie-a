/**
 * Squadre - Grid di tutte le squadre per lega con badge.
 */
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getTeamId, LEAGUE_TEAM_NAMES } from '../../constants/teamIds';

const LEAGUES_TEAMS: { key: string; label: string; color: string; teams: { name: string; id: number }[] }[] = [
  { key: 'serie-a', label: 'Serie A', color: Colors.green, teams: teamsForLeague('serie-a') },
  { key: 'premier-league', label: 'Premier League', color: Colors.accent, teams: teamsForLeague('premier-league') },
  { key: 'la-liga', label: 'La Liga', color: Colors.yellow, teams: teamsForLeague('la-liga') },
  { key: 'bundesliga', label: 'Bundesliga', color: '#d50000', teams: teamsForLeague('bundesliga') },
  { key: 'ligue-1', label: 'Ligue 1', color: '#003189', teams: teamsForLeague('ligue-1') },
  { key: 'champions-league', label: 'Champions League', color: '#1a237e', teams: teamsForLeague('champions-league') },
  { key: 'europa-league', label: 'Europa League', color: '#ff6f00', teams: teamsForLeague('europa-league') },
  { key: 'conference-league', label: 'Conference League', color: '#4caf50', teams: teamsForLeague('conference-league') },
];

function teamsForLeague(key: string) {
  return (LEAGUE_TEAM_NAMES[key] || []).map((name) => ({ name, id: getTeamId(name) || 0 }));
}

export default function SquadreScreen() {
  const router = useRouter();
  const [leagueIdx, setLeagueIdx] = useState(0);
  const league = LEAGUES_TEAMS[leagueIdx];

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="squadre" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <Text style={styles.pageTitle}>Squadre</Text>

          {/* LEAGUE TABS */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
            <View style={styles.leagueTabs}>
              {LEAGUES_TEAMS.map((l, i) => (
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

          <Text style={styles.leagueTitle}>{league.label}</Text>

          {/* GRID SQUADRE */}
          <View style={styles.grid}>
            {league.teams.map((team) => (
              <TouchableOpacity
                key={team.name}
                style={styles.teamCard}
                onPress={() => router.push(`/team/${encodeURIComponent(team.name)}` as any)}
              >
                <Image
                  source={{ uri: `https://media.api-sports.io/football/teams/${team.id}.png` }}
                  style={styles.teamBadge}
                  resizeMode="contain"
                />
                <Text style={styles.teamName} numberOfLines={2}>{team.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text, marginBottom: 16 },
  leagueTabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  leagueTab: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, alignItems: 'center' },
  leagueTabText: { fontSize: 12, fontWeight: '700' },
  leagueTitle: { fontSize: 18, fontWeight: '700', color: Colors.text, marginBottom: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  teamCard: {
    width: '30%',
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 12,
    alignItems: 'center',
  },
  teamBadge: { width: 50, height: 50, marginBottom: 8 },
  teamName: { color: Colors.text, fontSize: 12, fontWeight: '600', textAlign: 'center' },
});
