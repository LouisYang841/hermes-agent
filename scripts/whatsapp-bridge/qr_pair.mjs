import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import qrcode from 'qrcode';
import { writeFileSync, readFileSync, mkdirSync } from 'fs';
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

let qrRendered = false;

sock.ev.on('connection.update', async (update) => {
  const { connection, lastDisconnect, qr } = update;
  if (qr && !qrRendered) {
    qrRendered = true;
    writeFileSync('/tmp/whatsapp_qr_string.txt', qr);
    const text = await qrcode.toString(qr, { type: 'utf8', small: false });
    console.log('\n' + '='.repeat(70));
    console.log('SCAN THIS QR CODE WITH YOUR PHONE:');
    console.log('Open WhatsApp -> Settings -> Linked Devices -> Link a Device');
    console.log('='.repeat(70) + '\n');
    console.log(text);
    console.log('\n' + '='.repeat(70));
    console.log('Waiting for scan... (timeout: 3 minutes)');
    console.log('='.repeat(70) + '\n');
  }
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) {
      console.log('Logged out. Delete session to re-pair.');
      process.exit(1);
    }
    if (!qrRendered) {
      // Allow another QR attempt on reconnect
      qrRendered = false;
    }
  }
  if (connection === 'open') {
    console.log('WhatsApp connected successfully!');
    process.exit(0);
  }
});

sock.ev.on('creds.update', saveCreds);
