import { View, StyleSheet, Text } from 'react-native';
import { Colors, Spacing, BorderRadius } from '../constants/theme';

// Dati formazione dal backend
interface Formazione {
  modulo: string;      // es. "4-3-3", "3-5-2"
  titolari: string[];  // ordine: portiere, difensori, centrocampisti, attaccanti
}

interface PitchViewProps {
  formazione: Formazione;
}

// Analizza il modulo e ritorna le righe di giocatori sul campo
// Il primo elemento è sempre il portiere, poi le righe secondo il modulo
function getLinee(modulo: string, titolari: string[]): string[][] {
  // Parsa il modulo (es. "4-3-3" -> [4, 3, 3])
  const parti = modulo.split('-').map(Number).filter((n) => !isNaN(n) && n > 0);

  // Totale giocatori in campo = 11
  const linee: string[][] = [];
  let idx = 1; // salto il portiere (indice 0)

  for (const n of parti) {
    const linea = titolari.slice(idx, idx + n);
    linee.push(linea);
    idx += n;
  }

  return linee;
}

// Colori sfondo per riga (dalla difesa all'attacco)
const RIGA_COLORS = [
  Colors.info + '40',    // difesa - blu
  Colors.accent + '35',  // centrocampo - giallo
  Colors.danger + '35',  // attacco - rosso
];

export function PitchView({ formazione }: PitchViewProps) {
  const { modulo, titolari } = formazione;

  // Portiere
  const portiere = titolari[0] ?? '–';

  // Righe restanti secondo il modulo
  const linee = getLinee(modulo, titolari);

  return (
    <View style={styles.container}>
      {/* Etichetta modulo */}
      <View style={styles.moduloBadge}>
        <Text style={styles.moduloText}>{modulo}</Text>
      </View>

      {/* Campo verde con linee bianche */}
      <View style={styles.campo}>
        {/* Linea di centrocampo */}
        <View style={styles.lineaMeta} />

        {/* Attacco → Difesa (visuale dal basso, portiere in basso) */}
        {/* Mostriamo dall'attacco verso la difesa, poi portiere */}
        {[...linee].reverse().map((linea, rigaIdx) => {
          const colorIdx = Math.min(rigaIdx, RIGA_COLORS.length - 1);
          return (
            <View key={rigaIdx} style={styles.riga}>
              {linea.map((nome, idx) => (
                <View key={idx} style={styles.giocatoreWrap}>
                  <View style={[styles.cerchio, { backgroundColor: RIGA_COLORS[colorIdx] }]}>
                    <Text style={styles.numeroCerchio}>{idx + 1}</Text>
                  </View>
                  <Text style={styles.nomeGiocatore} numberOfLines={1}>
                    {abbrevia(nome)}
                  </Text>
                </View>
              ))}
            </View>
          );
        })}

        {/* Portiere */}
        <View style={styles.riga}>
          <View style={styles.giocatoreWrap}>
            <View style={[styles.cerchio, styles.cerchioPortiere]}>
              <Text style={styles.numeroCerchio}>1</Text>
            </View>
            <Text style={styles.nomeGiocatore} numberOfLines={1}>
              {abbrevia(portiere)}
            </Text>
          </View>
        </View>

        {/* Area di rigore (decorativa) */}
        <View style={styles.areaRigore} />
      </View>
    </View>
  );
}

// Abbrevia cognome lungo: "Lautaro Martinez" → "L. Martinez"
function abbrevia(nome: string): string {
  if (!nome) return '–';
  const parti = nome.trim().split(' ');
  if (parti.length === 1 || nome.length <= 10) return nome;
  return parti[parti.length - 1]; // mostra solo cognome
}

const styles = StyleSheet.create({
  container: {
    marginVertical: Spacing.sm,
  },
  moduloBadge: {
    alignSelf: 'center',
    backgroundColor: Colors.primary + '30',
    borderColor: Colors.primary,
    borderWidth: 1,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    marginBottom: Spacing.sm,
  },
  moduloText: {
    color: Colors.primary,
    fontWeight: '700',
    fontSize: 13,
  },
  campo: {
    backgroundColor: '#1a3a1a',
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.sm,
    borderWidth: 2,
    borderColor: '#2d6a2d',
    gap: Spacing.sm,
    position: 'relative',
    overflow: 'hidden',
  },
  lineaMeta: {
    position: 'absolute',
    top: '50%',
    left: Spacing.md,
    right: Spacing.md,
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.25)',
  },
  riga: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    alignItems: 'center',
  },
  giocatoreWrap: {
    alignItems: 'center',
    width: 56,
    gap: 3,
  },
  cerchio: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: Colors.accent + '40',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  cerchioPortiere: {
    backgroundColor: Colors.info + '50',
    borderColor: Colors.info,
  },
  numeroCerchio: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  nomeGiocatore: {
    color: '#e8f5e8',
    fontSize: 9,
    textAlign: 'center',
    fontWeight: '600',
  },
  areaRigore: {
    position: 'absolute',
    bottom: 0,
    left: '30%',
    right: '30%',
    height: 28,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
    borderWidth: 1.5,
    borderBottomWidth: 0,
    borderColor: 'rgba(255,255,255,0.3)',
  },
});
