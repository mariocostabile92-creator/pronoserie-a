/**
 * Notizie - Lista notizie calcistiche live.
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Linking,
} from 'react-native';
import { TopNavbar } from '../../components/TopNavbar';
import { Card } from '../../components/Card';
import { Colors } from '../../constants/theme';
import { getNotizie } from '../../services/api';

interface Notizia {
  titolo: string;
  fonte: string;
  url: string;
  data?: string;
}

export default function NotizieScreen() {
  const [notizie, setNotizie] = useState<Notizia[]>([]);
  const [loading, setLoading] = useState(true);
  const [aggiornamento, setAggiornamento] = useState('');

  useEffect(() => {
    loadNotizie();
  }, []);

  const loadNotizie = async () => {
    setLoading(true);
    try {
      const res = await getNotizie();
      setNotizie(res.data?.notizie || []);
      setAggiornamento(res.data?.aggiornamento || '');
    } catch (_) {}
    setLoading(false);
  };

  const openLink = (url: string) => {
    if (url) Linking.openURL(url);
  };

  return (
    <View style={styles.container}>
      <TopNavbar activeTab="notizie" />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.body}>
          <View style={styles.titleRow}>
            <Text style={styles.pageTitle}>Notizie dal Calcio</Text>
            <TouchableOpacity onPress={loadNotizie} style={styles.refreshBtn}>
              <Text style={styles.refreshText}>↻ Aggiorna</Text>
            </TouchableOpacity>
          </View>
          {aggiornamento ? (
            <Text style={styles.aggiornamento}>Aggiornato: {aggiornamento}</Text>
          ) : null}

          {loading && <ActivityIndicator color={Colors.accent} style={{ marginTop: 32 }} />}

          {!loading && notizie.map((n, i) => (
            <TouchableOpacity key={i} onPress={() => openLink(n.url)}>
              <Card style={styles.notiziaCard}>
                <Text style={styles.notiziaTag}>📰 {n.fonte}</Text>
                <Text style={styles.notiziaTitolo}>{n.titolo}</Text>
                {n.data ? <Text style={styles.notiziaData}>{n.data}</Text> : null}
                <Text style={styles.notiziaLink}>Leggi di più →</Text>
              </Card>
            </TouchableOpacity>
          ))}

          {!loading && notizie.length === 0 && (
            <Text style={{ color: Colors.muted, textAlign: 'center', marginTop: 32 }}>
              Nessuna notizia disponibile al momento.
            </Text>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  body: { padding: 12 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  pageTitle: { fontSize: 22, fontWeight: '700', color: Colors.text },
  refreshBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, backgroundColor: '#1f3460' },
  refreshText: { color: Colors.accent, fontSize: 13, fontWeight: '600' },
  aggiornamento: { color: Colors.muted, fontSize: 11, marginBottom: 16 },
  notiziaCard: { marginBottom: 10 },
  notiziaTag: { color: Colors.accent, fontSize: 11, fontWeight: '600', marginBottom: 6 },
  notiziaTitolo: { color: Colors.text, fontSize: 15, fontWeight: '600', lineHeight: 22, marginBottom: 8 },
  notiziaData: { color: Colors.muted, fontSize: 11, marginBottom: 6 },
  notiziaLink: { color: Colors.accent, fontSize: 13, fontWeight: '600' },
});
