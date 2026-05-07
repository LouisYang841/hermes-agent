import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
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
  browser: ['Hermes Agent', 'Chrome', '0.12.0'],
  syncFullHistory: false,
  markOnlineOnConnect: false,
  emitOwnEvents: true,
});

console.log('PAIRING_STARTED');

sock.ev.on('connection.update', async (update) => {
  const { connection, lastDisconnect, qr } = update;
  if (qr) {
    writeFileSync('/tmp/whatsapp_qr_string.txt', qr);
    console.log('QR_SAVED');
  }
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) {
      console.log('LOGGED_OUT');
      process.exit(1);
    }
  }
  if (connection === 'open') {
    console.log('CONNECTED');
    process.exit(0);
  }
});

sock.ev.on('creds.update', saveCreds);
