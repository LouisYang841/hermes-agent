import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import qrcode from 'qrcode';
import { writeFileSync, mkdirSync } from 'fs';
import { Boom } from '@hapi/boom';
import pino from 'pino';

const SESSION_DIR = '/home/ubuntu/.hermes/platforms/whatsapp/session';
mkdirSync(SESSION_DIR, { recursive: true });

const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
const { version } = await fetchLatestBaileysVersion();

const sock = makeWASocket({
  version, auth: state, printQRInTerminal: false,
  logger: pino({ level: 'silent' }),
  browser: ['Hermes Agent', 'Chrome', '0.12.0'],
  syncFullHistory: false, markOnlineOnConnect: false, emitOwnEvents: true,
});

sock.ev.on('creds.update', saveCreds);

sock.ev.on('connection.update', async (update) => {
  const { connection, lastDisconnect, qr } = update;
  if (qr) {
    // Save QR as PNG + HTML page
    await qrcode.toFile('/tmp/whatsapp_qr.png', qr, { type: 'png', width: 500, margin: 2 });
    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes WhatsApp QR</title>
<style>body{background:#1a1a2e;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;color:#eee}
h1{color:#e94560;margin-bottom:10px}p{color:#aaa;margin-bottom:20px;text-align:center}
img{border-radius:12px;box-shadow:0 0 30px rgba(233,69,96,.3);max-width:90vw}</style></head>
<body><h1>Scan to link Hermes</h1>
<p>Open WhatsApp → Linked Devices → Link a Device<br>Scan this QR code with your phone</p>
<img src="data:image/png;base64,${(await qrcode.toDataURL(qr, { width: 500, margin: 2 })).split(',')[1]}" />
<p style="margin-top:30px;font-size:12px;color:#666">Auto-refresh every 30s — close this page when done</p>
<script>setTimeout(()=>location.reload(),30000)</script>
</body></html>`;
    writeFileSync('/tmp/whatsapp_qr.html', html);
    process.stdout.write('QR_GENERATED');
  }
  if (connection === 'open') {
    process.stdout.write('CONNECTED');
    process.exit(0);
  }
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) { process.exit(1); }
  }
});
