/**
 * TopNavbar - Navbar orizzontale scrollabile identica alla webapp.
 * Sostituisce il tab bar inferiore con una navbar in cima stile web.
 */
import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Image,
} from 'react-native';
import { useRouter, usePathname } from 'expo-router';
import { Colors } from '../constants/theme';
import { useAuth } from '../contexts/AuthContext';

interface NavItem {
  label: string;
  route: string;
  tab?: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Home',          route: '/(tabs)/home',         tab: 'home' },
  { label: 'Fantacalcio',   route: '/fantacalcio',         tab: 'fantacalcio' },
  { label: 'Pronostici',    route: '/(tabs)/pronostici',   tab: 'pronostici' },
  { label: 'Calendario',    route: '/(tabs)/calendario',   tab: 'calendario' },
  { label: 'Classifiche',   route: '/(tabs)/classifica',   tab: 'classifica' },
  { label: 'Squadre',       route: '/(tabs)/squadre',      tab: 'squadre' },
  { label: 'Notizie',       route: '/(tabs)/notizie',      tab: 'notizie' },
  { label: 'Accuratezza',   route: '/(tabs)/accuratezza',  tab: 'accuratezza' },
  { label: '🏆 Mondiali',   route: '/mondiali',            tab: 'mondiali' },
  { label: 'Risultati Live',route: '/(tabs)/risultati',    tab: 'risultati' },
  { label: 'Pricing',       route: '/(tabs)/pricing',      tab: 'pricing' },
];

interface TopNavbarProps {
  activeTab?: string;
}

export function TopNavbar({ activeTab }: TopNavbarProps) {
  const router = useRouter();
  const { token } = useAuth();

  const handleNav = (route: string) => {
    router.push(route as any);
  };

  const handleAuth = () => {
    if (token) {
      router.push('/(tabs)/profilo' as any);
    } else {
      router.push('/auth/login' as any);
    }
  };

  return (
    <View style={styles.navContainer}>
      {/* Logo */}
      <View style={styles.logoContainer}>
        <Text style={styles.logo}>⚽ MatchIQ</Text>
      </View>

      {/* Nav links scrollabili */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        style={styles.scrollView}
      >
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.tab;
          return (
            <TouchableOpacity
              key={item.tab}
              onPress={() => handleNav(item.route)}
              style={[styles.navLink, isActive && styles.navLinkActive]}
            >
              <Text style={[styles.navLinkText, isActive && styles.navLinkTextActive]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}

        {/* Bottone Accedi */}
        <TouchableOpacity onPress={handleAuth} style={styles.authBtn}>
          <Text style={styles.authBtnText}>
            {token ? '👤 Profilo' : '👤 Accedi'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  navContainer: {
    backgroundColor: '#0d1b2a',
    borderBottomWidth: 2,
    borderBottomColor: '#1f3460',
    paddingTop: 44, // safe area per notch
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 8,
  },
  logoContainer: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  logo: {
    fontSize: 16,
    fontWeight: '800',
    color: Colors.green,
    textShadowColor: 'rgba(46,204,113,0.3)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  scrollView: {
    flexGrow: 0,
  },
  scrollContent: {
    paddingHorizontal: 8,
    paddingBottom: 8,
    gap: 4,
    flexDirection: 'row',
    alignItems: 'center',
  },
  navLink: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
  },
  navLinkActive: {
    backgroundColor: 'rgba(52,152,219,0.2)',
    borderWidth: 1,
    borderColor: 'rgba(52,152,219,0.3)',
  },
  navLinkText: {
    color: Colors.muted,
    fontSize: 13,
    fontWeight: '500',
  },
  navLinkTextActive: {
    color: Colors.text,
  },
  authBtn: {
    marginLeft: 8,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 10,
    backgroundColor: '#1f3460',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  authBtnText: {
    color: Colors.text,
    fontSize: 13,
    fontWeight: '600',
  },
});
