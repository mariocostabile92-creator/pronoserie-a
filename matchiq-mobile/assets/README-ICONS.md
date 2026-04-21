# Icone richieste per MatchIQ

Questa cartella deve contenere le seguenti immagini **prima della build EAS**.

## File richiesti

| File | Dimensioni | Uso |
|------|-----------|-----|
| `icon.png` | 1024 × 1024 px | Icona principale (iOS + Android) |
| `adaptive-icon.png` | 1024 × 1024 px | Icona adattiva Android (foreground) |
| `splash.png` | 1284 × 2778 px | Splash screen |
| `favicon.png` | 196 × 196 px | Favicon web |

## Colori tema

- **Background**: `#0D1117` (da `constants/theme.ts`)  
- **Primary**: `#4CAF50`  
- **Text**: `#E6EDF3`

## Come generare le immagini placeholder

```bash
# Nella root di matchiq-mobile/
npm install canvas
node scripts/generate-icons.js
```

Lo script crea immagini PNG con il logo "M" su sfondo scuro.  
**Sostituire con asset grafici definitivi prima della pubblicazione sul Play Store.**

## Note Play Store

- L'`icon.png` **non deve avere angoli arrotondati** — li applica il Play Store automaticamente.  
- L'`adaptive-icon.png` è il foreground layer; il background è definito in `app.json` (`android.adaptiveIcon.backgroundColor`).  
- La splash deve avere margini generosi perché viene ritagliata su diversi formati schermo.
