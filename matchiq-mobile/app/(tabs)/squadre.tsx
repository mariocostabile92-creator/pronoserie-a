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

const LEAGUES_TEAMS: { key: string; label: string; color: string; teams: { name: string; id: number }[] }[] = [
  {
    key: 'serie-a', label: 'Serie A', color: Colors.green,
    teams: [
      { name: 'Inter', id: 505 }, { name: 'Milan', id: 489 }, { name: 'Napoli', id: 492 },
      { name: 'Juventus', id: 496 }, { name: 'Roma', id: 497 }, { name: 'Atalanta', id: 499 },
      { name: 'Lazio', id: 487 }, { name: 'Bologna', id: 500 }, { name: 'Fiorentina', id: 502 },
      { name: 'Torino', id: 503 }, { name: 'Como', id: 895 }, { name: 'Udinese', id: 494 },
      { name: 'Parma', id: 523 }, { name: 'Genoa', id: 495 }, { name: 'Cagliari', id: 490 },
      { name: 'Sassuolo', id: 488 }, { name: 'Lecce', id: 867 }, { name: 'Verona', id: 504 },
      { name: 'Cremonese', id: 520 }, { name: 'Pisa', id: 801 },
    ],
  },
  {
    key: 'premier-league', label: 'Premier League', color: Colors.accent,
    teams: [
      { name: 'Arsenal', id: 42 }, { name: 'Aston Villa', id: 66 }, { name: 'Chelsea', id: 49 },
      { name: 'Liverpool', id: 40 }, { name: 'Man City', id: 50 }, { name: 'Man United', id: 33 },
      { name: 'Newcastle', id: 34 }, { name: 'Tottenham', id: 47 }, { name: 'West Ham', id: 48 },
      { name: 'Brighton', id: 51 }, { name: 'Brentford', id: 55 }, { name: 'Fulham', id: 36 },
      { name: 'Crystal Palace', id: 52 }, { name: 'Everton', id: 45 }, { name: 'Wolves', id: 39 },
      { name: 'Bournemouth', id: 35 }, { name: 'Burnley', id: 44 }, { name: 'Nott. Forest', id: 65 },
    ],
  },
  {
    key: 'la-liga', label: 'La Liga', color: Colors.yellow,
    teams: [
      { name: 'Barcelona', id: 529 }, { name: 'Real Madrid', id: 541 }, { name: 'Atletico Madrid', id: 530 },
      { name: 'Athletic Club', id: 531 }, { name: 'Real Sociedad', id: 548 }, { name: 'Villarreal', id: 533 },
      { name: 'Real Betis', id: 543 }, { name: 'Sevilla', id: 536 }, { name: 'Valencia', id: 532 },
      { name: 'Osasuna', id: 727 }, { name: 'Girona', id: 547 }, { name: 'Celta Vigo', id: 538 },
    ],
  },
  {
    key: 'bundesliga', label: 'Bundesliga', color: '#d50000',
    teams: [
      { name: 'Bayern Munich', id: 157 }, { name: 'Bayer Leverkusen', id: 168 }, { name: 'Borussia Dortmund', id: 165 },
      { name: 'Eintracht Frankfurt', id: 169 }, { name: 'RB Leipzig', id: 173 }, { name: 'Wolfsburg', id: 161 },
      { name: 'Freiburg', id: 160 }, { name: 'Stuttgart', id: 172 }, { name: 'Werder Bremen', id: 162 },
      { name: 'Hoffenheim', id: 167 }, { name: 'Mainz', id: 164 }, { name: 'Augsburg', id: 170 },
    ],
  },
  {
    key: 'ligue-1', label: 'Ligue 1', color: '#003189',
    teams: [
      { name: 'Paris Saint Germain', id: 85 }, { name: 'Marseille', id: 81 }, { name: 'Monaco', id: 91 },
      { name: 'Lyon', id: 80 }, { name: 'Nice', id: 84 }, { name: 'Lille', id: 79 },
      { name: 'Lens', id: 116 }, { name: 'Rennes', id: 94 }, { name: 'Nantes', id: 83 },
      { name: 'Strasbourg', id: 95 }, { name: 'Toulouse', id: 96 }, { name: 'Auxerre', id: 110 },
    ],
  },
];

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
