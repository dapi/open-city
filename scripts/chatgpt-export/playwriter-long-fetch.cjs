// NODE_OPTIONS=--require патч: убирает 5-минутный лимит (undici headersTimeout/bodyTimeout=300s)
// Каноническое расположение: scripts/chatgpt-export/playwriter-long-fetch.cjs
// у встроенного fetch Node.js. Нужен для длинных playwriter-вызовов (>5 мин).
// Использование:
//   NODE_OPTIONS="--require /Users/danil/code/open-city/chatgpt-chat-archive/scripts/playwriter-long-fetch.cjs" \
//     playwriter -s 4 -f script.js --timeout 3600000
const http = require('node:http');
const https = require('node:https');

const nativeFetch = globalThis.fetch;

function longFetch(url, opts = {}) {
  // Только простые кейсы CLI (POST JSON → JSON). Остальное — нативный fetch.
  if (opts && opts.method && String(opts.method).toUpperCase() !== 'GET') {
    return new Promise((resolve, reject) => {
      const u = new URL(url);
      const mod = u.protocol === 'https:' ? https : http;
      const req = mod.request(
        u,
        { method: opts.method, headers: opts.headers },
        (res) => {
          const chunks = [];
          res.on('data', (c) => chunks.push(c));
          res.on('end', () => {
            const buf = Buffer.concat(chunks);
            const headersMap = new Map(
              Object.entries(res.headers).map(([k, v]) => [k, Array.isArray(v) ? v.join(', ') : v]),
            );
            resolve({
              ok: res.statusCode >= 200 && res.statusCode < 300,
              status: res.statusCode,
              statusText: res.statusMessage,
              headers: headersMap,
              text: async () => buf.toString('utf8'),
              json: async () => JSON.parse(buf.toString('utf8')),
              arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
            });
          });
        },
      );
      req.on('error', reject);
      req.setTimeout(0); // без таймаута сокета
      if (opts.body) req.write(opts.body);
      req.end();
    });
  }
  return nativeFetch(url, opts);
}

globalThis.fetch = longFetch;
