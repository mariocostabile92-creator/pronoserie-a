/**
 * Script per generare le immagini placeholder per MatchIQ.
 * Richiede: npm install canvas
 *
 * Esecuzione: node scripts/generate-icons.js
 *
 * Genera:
 *   assets/icon.png           — 1024x1024  (icona app)
 *   assets/adaptive-icon.png  — 1024x1024  (icona adattiva Android)
 *   assets/splash.png         — 1284x2778  (splash screen)
 *   assets/favicon.png        —  196x196   (favicon web)
 */

const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

// Colori dal tema dark di MatchIQ (constants/theme.ts)
const BG_COLOR = '#0D1117';
const PRIMARY   = '#4CAF50';
const TEXT      = '#E6EDF3';

const ASSETS = path.join(__dirname, '..', 'assets');

function saveCanvas(canvas, filename) {
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(path.join(ASSETS, filename), buffer);
  console.log(`Generato: assets/${filename}`);
}

/** Disegna uno sfondo con lettera "M" centrata */
function drawIcon(size) {
  const canvas = createCanvas(size, size);
  const ctx    = canvas.getContext('2d');

  // Sfondo
  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, size, size);

  // Cerchio verde
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.38, 0, Math.PI * 2);
  ctx.fillStyle = PRIMARY;
  ctx.fill();

  // Lettera M
  ctx.fillStyle  = TEXT;
  ctx.font       = `bold ${size * 0.38}px sans-serif`;
  ctx.textAlign  = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('M', size / 2, size / 2);

  return canvas;
}

/** Splash screen 1284x2778 */
function drawSplash() {
  const W = 1284;
  const H = 2778;
  const canvas = createCanvas(W, H);
  const ctx    = canvas.getContext('2d');

  // Sfondo
  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, W, H);

  // Logo centrato verticalmente
  const iconSize = 320;
  const x = (W - iconSize) / 2;
  const y = (H - iconSize) / 2;

  ctx.beginPath();
  ctx.arc(x + iconSize / 2, y + iconSize / 2, iconSize / 2, 0, Math.PI * 2);
  ctx.fillStyle = PRIMARY;
  ctx.fill();

  ctx.fillStyle  = TEXT;
  ctx.font       = `bold ${iconSize * 0.4}px sans-serif`;
  ctx.textAlign  = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('MatchIQ', W / 2, H / 2);

  return canvas;
}

// Genera tutti i file
saveCanvas(drawIcon(1024), 'icon.png');
saveCanvas(drawIcon(1024), 'adaptive-icon.png');
saveCanvas(drawSplash(),   'splash.png');
saveCanvas(drawIcon(196),  'favicon.png');

console.log('\nIcone placeholder generate con successo.');
console.log('ATTENZIONE: Sostituire con asset grafici definitivi prima della pubblicazione!');
