import { Tabs } from 'expo-router';
import { Colors } from '../../constants/theme';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        // Nascondi la bottom tab bar: la navigazione è gestita da TopNavbar
        tabBarStyle: { display: 'none' },
        headerShown: false,
      }}
    >
      <Tabs.Screen name="home" />
      <Tabs.Screen name="pronostici" />
      <Tabs.Screen name="classifica" />
      <Tabs.Screen name="calendario" />
      <Tabs.Screen name="risultati" />
      <Tabs.Screen name="notizie" />
      <Tabs.Screen name="profilo" />
      <Tabs.Screen name="squadre" />
      <Tabs.Screen name="accuratezza" />
      <Tabs.Screen name="pricing" />
    </Tabs>
  );
}
