import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import { writeFileSync, mkdirSync } from 'fs';
import { Boom } from '@hapi/boom';
import pino from 'pino';

const SESSION_DIR = '/home/ubuntu/.hermes/platforms/whatsapp/session';
mkdirSync(SESSION_DIR, { recursive: true });

const phoneNumber = process.argv[2];
if (!phoneNumber) { process.exit(1); }

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
  const { connection, lastDisconnect } = update;
  if (connection === 'open') {
    writeFileSync('/tmp/whatsapp_status.txt', 'CONNECTED');
    process.exit(0);
  }
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) {
      writeFileSync('/tmp/whatsapp_status.txt', 'LOGGED_OUT');
      process.exit(1);
    }
  }
});

setTimeout(async () => {
  const code = await sock.requestPairingCode(phoneNumber);
  writeFileSync('/tmp/whatsapp_code.txt', code);
  writeFileSync('/tmp/whatsapp_status.txt', 'AWAITING_SCAN');
}, 2000);
