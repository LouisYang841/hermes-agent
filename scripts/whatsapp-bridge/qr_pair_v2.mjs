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
  version,
  auth: state,
  printQRInTerminal: false,
  logger: pino({ level: 'silent' }),
  browser: ['Chrome', 'Linux', '121.0.6167.139'],  // Real Chrome UA
  syncFullHistory: false,
  markOnlineOnConnect: false,
  emitOwnEvents: true,
});

sock.ev.on('creds.update', saveCreds);
let qrDisplayed = false;

sock.ev.on('connection.update', async (update) => {
  const { connection, lastDisconnect, qr } = update;
  if (qr && !qrDisplayed) {
    qrDisplayed = true;
    writeFileSync('/tmp/whatsapp_qr_string.txt', qr);
    const text = await qrcode.toString(qr, { type: 'utf8', small: false });
    process.stdout.write('\nSCAN THIS QR WITH WHATSAPP:\n');
    process.stdout.write(text + '\n');
    process.stdout.write('Waiting for scan... (timeout: 3 min)\n');
  }
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) {
      process.stdout.write('LOGGED_OUT\n');
      process.exit(1);
    }
    qrDisplayed = false;  // Allow retry on reconnect
  }
  if (connection === 'open') {
    process.stdout.write('CONNECTED\n');
    process.exit(0);
  }
});
