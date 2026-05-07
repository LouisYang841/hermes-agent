import qrcode from 'qrcode';
import { readFileSync } from 'fs';
const qrStr = readFileSync('/tmp/whatsapp_qr_string.txt', 'utf-8').trim();

// Try different output types
const utf8 = await qrcode.toString(qrStr, { type: 'utf8', small: false });
process.stdout.write('=== UTF8 ===\n' + utf8 + '\n');

const svg = await qrcode.toString(qrStr, { type: 'svg' });
// Save SVG
import { writeFileSync } from 'fs';
writeFileSync('/tmp/whatsapp_qr.svg', svg);
process.stdout.write('SVG saved\n');
