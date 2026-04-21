/**
 * notifications.ts
 * Gestione notifiche push con expo-notifications.
 * Richiede il permesso all'utente, ottiene il token Expo e lo invia al backend.
 * Infrastruttura pronta: il backend riceverà il token quando verrà aggiunto l'endpoint.
 */
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { registerPushToken } from './api';

// Configura come mostrare le notifiche quando l'app è in primo piano
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

/**
 * Richiede il permesso per le notifiche push e ottiene il token Expo.
 * Invia il token al backend se disponibile.
 * Restituisce il token oppure null se non disponibile o rifiutato.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  try {
    // Verifica/richiedi permesso
    const { status: statoCorrente } = await Notifications.getPermissionsAsync();
    let statoFinale = statoCorrente;

    if (statoCorrente !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      statoFinale = status;
    }

    if (statoFinale !== 'granted') {
      console.log('[Notifiche] Permesso rifiutato dall\'utente');
      return null;
    }

    // Configura il canale di notifica per Android
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('matchiq-default', {
        name: 'MatchIQ Notifiche',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#4CAF50',
        description: 'Notifiche per gol live, pronostici e aggiornamenti MatchIQ',
      });
    }

    // Recupera il token Expo push
    const tokenData = await Notifications.getExpoPushTokenAsync();
    const pushToken = tokenData.data;
    console.log('[Notifiche] Token ottenuto:', pushToken);

    // Invia il token al backend (ignora l'errore se l'endpoint non esiste ancora)
    try {
      await registerPushToken(pushToken);
      console.log('[Notifiche] Token inviato al backend');
    } catch (errBackend) {
      // Endpoint non ancora disponibile lato backend: nessun problema
      console.log('[Notifiche] Backend non ha ancora l\'endpoint push/register, token salvato solo localmente');
    }

    return pushToken;
  } catch (errore) {
    console.error('[Notifiche] Errore registrazione push notifications:', errore);
    return null;
  }
}
