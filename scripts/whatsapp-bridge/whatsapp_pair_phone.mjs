import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import { mkdirSync } from 'fs';
import { Boom } from '@hapi/boom';
import pino from 'pino';

const SESSION_DIR = '/home/ubuntu/.hermes/platforms/whatsapp/session';
mkdirSync(SESSION_DIR, { recursive: true });

// Get phone number from command line arg
const phoneNumber = process.argv[2];
if (!phoneNumber) {
  console.error('Usage: node whatsapp_pair_phone.mjs <phone_number>');
  console.error('  Include country code, no + or spaces');
  console.error('  Example: node whatsapp_pair_phone.mjs 60123456789');
  process.exit(1);
}

console.log(`WhatsApp phone pairing for: ${phoneNumber}`);
console.log('');

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

sock.ev.on('creds.update', saveCreds);

sock.ev.on('connection.update', async (update) => {
  const { connection, lastDisconnect } = update;
  
  if (connection === 'open') {
    console.log('WhatsApp connected successfully!');
    process.exit(0);
  }
  
  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    if (reason === DisconnectReason.loggedOut) {
      console.log('Logged out or pairing rejected.');
      process.exit(1);
    }
    console.log('Disconnected, retrying...');
  }
});

// Wait for socket to be ready, then request pairing code
setTimeout(async () => {
  try {
    console.log('Requesting pairing code from WhatsApp...');
    const code = await sock.requestPairingCode(phoneNumber);
    console.log('');
    console.log('========================================');
    console.log('  OPEN WHATSAPP ON YOUR PHONE');
    console.log('  Settings -> Linked Devices');
    console.log('  Tap "Link a Device"');
    console.log('  Then tap "Link with phone number instead"');
    console.log('');
    console.log(`  PAIRING CODE: ${code}`);
    console.log('');
    console.log('========================================');
    console.log('');
    console.log('Enter this code in WhatsApp on your phone.');
    console.log('Waiting for connection...');
  } catch (err) {
    console.error('Pairing request failed:', err.message);
    process.exit(1);
  }
}, 2000);
