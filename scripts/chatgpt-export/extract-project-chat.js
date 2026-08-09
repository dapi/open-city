// Выкачка ОДНОГО чата проекта ChatGPT через backend-api (нужен залогин).
// Каноническое расположение: scripts/chatgpt-export/extract-project-chat.js
// Перед запуском: state.chatId = "69077bb5-..."
//
// Метод:
//   1. Bearer token из /api/auth/session
//   2. GET /backend-api/conversation/<id> → полный mapping (вся история, без скролла)
//   3. Ассеты: sediment://file_* / file-service://file-* / metadata.attachments
//      → GET /backend-api/files/<file_id>/download → подписанный download_url → байты
//
// Результат (cwd = корень репо):
//   chatgpt-project-archive/chats/<id>.json        — сообщения + реестр артефактов
//   chatgpt-project-archive/chats/<id>.raw.json    — полный ответ API
//   chatgpt-project-archive/artifacts/<id>/        — файлы с настоящими именами

const fs = require('node:fs');
const path = require('node:path');

const chatId = state.chatId;
if (!chatId) throw new Error('state.chatId is not set');

const baseDir = 'chatgpt-project-archive';
const artDir = path.join(baseDir, 'artifacts', chatId);
fs.mkdirSync(artDir, { recursive: true });
fs.mkdirSync(path.join(baseDir, 'chats'), { recursive: true });

// Всё делаем в контексте страницы (там куки + токен)
const result = await state.page.evaluate(async (chatId) => {
  const sess = await (await fetch('https://chatgpt.com/api/auth/session')).json();
  const h = { Authorization: 'Bearer ' + sess.accessToken };

  const res = await fetch('https://chatgpt.com/backend-api/conversation/' + chatId, { headers: h });
  if (!res.ok) return { error: 'conversation HTTP ' + res.status + ': ' + (await res.text()).slice(0, 200) };
  const conv = await res.json();

  // Линеаризация: от current_node вверх к корню
  const chain = [];
  let node = conv.mapping[conv.current_node];
  const guard = 10000;
  while (node && chain.length < guard) {
    chain.unshift(node);
    node = node.parent ? conv.mapping[node.parent] : null;
  }

  // Собираем сообщения и id файлов
  const fileIds = new Map(); // fileId -> где встретился
  const addFile = (fid, where) => { if (fid && !fileIds.has(fid)) fileIds.set(fid, where); };
  const messages = [];
  for (const n of chain) {
    const m = n.message;
    if (!m || !m.author) continue;
    const content = m.content || {};
    const texts = [];
    const attachments = [];
    for (const p of content.parts || []) {
      if (typeof p === 'string') texts.push(p);
      else if (p && typeof p === 'object') {
        if (p.asset_pointer) {
          const fid = (p.asset_pointer.match(/file[-_][A-Za-z0-9]+/) || [])[0];
          addFile(fid, 'part:' + (p.content_type || 'asset'));
          attachments.push({ file_id: fid, asset_pointer: p.asset_pointer, content_type: p.content_type, width: p.width, height: p.height });
        } else if (p.content_type === 'text' && p.text) texts.push(p.text);
      }
    }
    for (const att of m.metadata?.attachments || []) {
      addFile(att.id, 'attachment:' + (att.mimeType || att.mime_type || ''));
      attachments.push({ file_id: att.id, name: att.name, mimeType: att.mimeType || att.mime_type, size: att.size });
    }
    const rec = {
      id: m.id,
      role: m.author.role,
      content_type: content.content_type,
      create_time: m.create_time,
      text: texts.join('\n'),
      attachments,
    };
    if (m.metadata?.thoughts) rec.thoughts = m.metadata.thoughts;
    if (m.metadata?.citations?.length) rec.citations = m.metadata.citations;
    messages.push(rec);
  }
  // На всякий случай сканируем весь JSON на file_ id (могут быть не в parts)
  const rawStr = JSON.stringify(conv);
  for (const mm of rawStr.matchAll(/sediment:\/\/(file_[A-Za-z0-9]+)/g)) addFile(mm[1], 'raw-scan');
  for (const mm of rawStr.matchAll(/file-service:\/\/(file-[A-Za-z0-9]+)/g)) addFile(mm[1], 'raw-scan');

  // Скачиваем файлы: file_id → download_url → bytes (base64 чанками наружу не тянем — качаем тут,
  // но bytes в page context не сохранить; поэтому возвращаем только мету + download_url)
  const downloads = [];
  for (const [fid, where] of fileIds) {
    try {
      const metaRes = await fetch('https://chatgpt.com/backend-api/files/' + fid + '/download', { headers: h });
      if (!metaRes.ok) throw new Error('meta HTTP ' + metaRes.status);
      const meta = await metaRes.json();
      if (!meta.download_url) throw new Error('no download_url: ' + JSON.stringify(meta).slice(0, 120));
      downloads.push({ file_id: fid, where, file_name: meta.file_name, mime_type: meta.mime_type, size: meta.file_size_bytes, download_url: meta.download_url });
    } catch (e) {
      downloads.push({ file_id: fid, where, error: e.message });
    }
  }
  return { conv, messages, downloads };
}, chatId);

if (result.error) throw new Error(result.error);
const { conv, messages, downloads } = result;
console.log('Chat:', conv.title, '| nodes:', Object.keys(conv.mapping).length, '| messages:', messages.length, '| files:', downloads.length);

// Сохраняем raw + messages
fs.writeFileSync(path.join(baseDir, 'chats', chatId + '.raw.json'), JSON.stringify(conv, null, 2));

// Скачиваем байты В КОНТЕКСТЕ СТРАНИЦЫ (подписанный URL требует кук — из Node даёт 403),
// передаём в Node base64-чанками по ~700 КБ
const extByMime = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif', 'image/webp': 'webp', 'image/svg+xml': 'svg', 'application/pdf': 'pdf' };
const artifacts = [];
for (const d of downloads) {
  if (d.error) { artifacts.push({ ...d, status: 'error: ' + d.error }); continue; }
  try {
    const meta = await state.page.evaluate(async (url) => {
      const res = await fetch(url);
      if (!res.ok) return { error: 'HTTP ' + res.status };
      const bytes = new Uint8Array(await res.arrayBuffer());
      window.__dl = { bytes, mime: (res.headers.get('content-type') || '').split(';')[0] };
      return { size: bytes.length, mime: window.__dl.mime };
    }, d.download_url);
    if (meta.error) throw new Error(meta.error);
    const CHUNK = 500000;
    const parts = [];
    for (let off = 0; off < meta.size; off += CHUNK) {
      const part = await state.page.evaluate(({ off, len }) => {
        const slice = window.__dl.bytes.subarray(off, off + len);
        let bin = '';
        for (let i = 0; i < slice.length; i++) bin += String.fromCharCode(slice[i]);
        return btoa(bin);
      }, { off, len: Math.min(CHUNK, meta.size - off) });
      // Decode each independently padded base64 chunk before concatenating.
      // Joining base64 strings first makes Node stop at the first chunk's
      // padding, silently truncating every file larger than CHUNK bytes.
      parts.push(Buffer.from(part, 'base64'));
    }
    const buf = Buffer.concat(parts);
    if (buf.length !== meta.size) {
      throw new Error(`size mismatch: expected ${meta.size}, got ${buf.length}`);
    }
    // Имя файла: настоящее (basename) или по file_id
    let fname = d.file_name ? d.file_name.split('/').pop() : null;
    if (!fname || fname.length < 3) fname = d.file_id;
    fname = fname.replace(/[^\wа-яА-ЯёЁ.-]+/g, '_');
    if (!/\.[a-z0-9]{2,5}$/i.test(fname)) {
      const ext = extByMime[d.mime_type] || (buf[0] === 0xff && buf[1] === 0xd8 ? 'jpg' : buf[0] === 0x89 ? 'png' : 'bin');
      fname += '.' + ext;
    }
    fs.writeFileSync(path.join(artDir, fname), buf);
    artifacts.push({ file_id: d.file_id, where: d.where, file: fname, bytes: buf.length, mime: d.mime_type, status: 'ok' });
  } catch (e) {
    artifacts.push({ file_id: d.file_id, where: d.where, status: 'error: ' + e.message });
  }
}
const okCount = artifacts.filter((a) => a.status === 'ok').length;
for (const a of artifacts.filter((a) => a.status !== 'ok')) console.log('FAIL:', a.file_id, a.status);

const out = {
  chatUrl: 'https://chatgpt.com/c/' + chatId,
  conversationId: conv.conversation_id || chatId,
  title: conv.title,
  create_time: conv.create_time,
  update_time: conv.update_time,
  extractedAt: new Date().toISOString(),
  messageCount: messages.length,
  messages,
  artifacts,
};
fs.writeFileSync(path.join(baseDir, 'chats', chatId + '.json'), JSON.stringify(out, null, 2));
console.log('DONE:', chatId, '| messages:', messages.length, '| artifacts ok:', okCount, '/', artifacts.length);
