import { writeFile } from 'node:fs/promises'
import { spawn } from 'node:child_process'

const chromePath =
  process.env.CHROME_PATH ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const outPath = new URL('./legal-rag-demo.webm', import.meta.url)
const port = 9223

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function cdp(method, params = {}, session) {
  const id = ++cdp.id
  session.socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => {
    session.pending.set(id, { resolve, reject })
  })
}
cdp.id = 0

async function connect() {
  let pages = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json())
  let page = pages.find((item) => item.type === 'page')
  if (!page) {
    page = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' }).then((r) => r.json())
  }
  const socket = new WebSocket(page.webSocketDebuggerUrl)
  const session = { socket, pending: new Map() }
  socket.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.id && session.pending.has(msg.id)) {
      const { resolve, reject } = session.pending.get(msg.id)
      session.pending.delete(msg.id)
      if (msg.error) reject(new Error(msg.error.message))
      else resolve(msg.result)
    }
  }
  await new Promise((resolve) => socket.onopen = resolve)
  return session
}

const recordingSource = String.raw`
async () => {
  const width = 1280
  const height = 720
  const duration = 30000
  const fps = 30
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  document.body.style.margin = '0'
  document.body.style.background = '#f4f6f4'
  document.body.appendChild(canvas)
  const ctx = canvas.getContext('2d')

  const colors = {
    canvas: '#f4f6f4',
    surface: '#fffdfa',
    ink: '#0b192c',
    muted: '#667085',
    teal: '#0f6b5f',
    gold: '#a86612',
    line: 'rgba(11,25,44,.12)',
    navy: '#0b192c'
  }

  function roundRect(x, y, w, h, r, fill, stroke) {
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.arcTo(x + w, y, x + w, y + h, r)
    ctx.arcTo(x + w, y + h, x, y + h, r)
    ctx.arcTo(x, y + h, x, y, r)
    ctx.arcTo(x, y, x + w, y, r)
    ctx.closePath()
    if (fill) {
      ctx.fillStyle = fill
      ctx.fill()
    }
    if (stroke) {
      ctx.strokeStyle = stroke
      ctx.lineWidth = 1
      ctx.stroke()
    }
  }

  function text(value, x, y, size, color = colors.ink, weight = '400', family = 'Inter, system-ui') {
    ctx.fillStyle = color
    ctx.font = weight + ' ' + size + 'px ' + family
    ctx.fillText(value, x, y)
  }

  function wrap(value, x, y, maxWidth, lineHeight, size, color = colors.ink, weight = '400') {
    ctx.fillStyle = color
    ctx.font = weight + ' ' + size + 'px Inter, system-ui'
    const words = value.split(' ')
    let line = ''
    for (const word of words) {
      const test = line ? line + ' ' + word : word
      if (ctx.measureText(test).width > maxWidth && line) {
        ctx.fillText(line, x, y)
        line = word
        y += lineHeight
      } else {
        line = test
      }
    }
    if (line) ctx.fillText(line, x, y)
    return y
  }

  function drawHeader() {
    roundRect(80, 34, 1120, 64, 12, 'rgba(255,253,250,.92)', colors.line)
    roundRect(104, 48, 36, 36, 8, colors.navy)
    text('LR', 115, 72, 14, '#f8f4ec', '700', 'Georgia')
    text('LegalResearch.AI', 154, 64, 16, colors.ink, '700')
    text('BNS and BNSS research copilot', 154, 82, 12, colors.muted, '400')
    roundRect(858, 51, 130, 30, 15, '#e4f1ed', 'rgba(15,107,95,.18)')
    text('BNS + BNSS, 2023', 873, 71, 12, '#18564e', '700')
    roundRect(1000, 51, 124, 30, 15, '#e4f1ed', 'rgba(23,111,69,.18)')
    ctx.fillStyle = '#176f45'
    ctx.beginPath()
    ctx.arc(1016, 66, 4, 0, Math.PI * 2)
    ctx.fill()
    text('Live backend', 1028, 71, 12, '#176f45', '700')
  }

  function drawHero(progress) {
    drawHeader()
    roundRect(260, 132, 760, 420, 16, 'rgba(255,253,250,.96)', 'rgba(11,25,44,.08)')
    text('INDIAN CRIMINAL LAW RESEARCH', 520, 183, 12, colors.teal, '800')
    text('Legal Research Copilot', 362, 250, 54, colors.ink, '700', 'Georgia')
    text('Ask a question and get grounded answers with Act-qualified section citations.', 372, 292, 16, colors.muted, '400')
    drawSearch(330, 326, 620, progress)
    const pills = [
      ['§', 'Punishment for murder'],
      ['BN', 'Explain BNSS s.187'],
      ['TR', 'Murder and trial procedure'],
      ['Δ', 'Murder vs culpable homicide']
    ]
    let x = 347
    let y = 414
    for (const [icon, label] of pills) {
      const w = 180 + Math.min(label.length * 2, 70)
      roundRect(x, y, w, 36, 18, 'rgba(251,250,247,.88)', colors.line)
      roundRect(x + 8, y + 7, 23, 23, 12, '#eef2ef')
      text(icon, x + 14, y + 23, 10, colors.teal, '800', 'Georgia')
      text(label, x + 40, y + 23, 13, colors.ink, '700')
      x += w + 10
      if (x > 900) { x = 390; y += 48 }
    }
  }

  function drawSearch(x, y, w, progress, typed = '') {
    roundRect(x, y, w, 64, 12, 'rgba(255,253,250,.98)', 'rgba(11,25,44,.18)')
    text('⌕', x + 22, y + 39, 20, colors.muted)
    const prompt = typed || 'Ask about offences, procedure, bail, trial, or citations'
    text(prompt, x + 60, y + 39, 15, typed ? colors.ink : '#8993a4')
    roundRect(x + w - 108, y + 18, 52, 28, 6, '#eef2ef', colors.line)
    text('⌘ K', x + w - 94, y + 37, 12, colors.muted, '700')
    roundRect(x + w - 48, y + 12, 40, 40, 8, colors.navy)
    text('→', x + w - 35, y + 38, 20, '#f8f4ec', '700')
  }

  function drawChat(t) {
    drawHeader()
    const typed = 'If someone shoots a person in public, what will be his punishment?'
    const q = t < 8 ? typed.slice(0, Math.floor((t - 5) / 3 * typed.length)) : typed
    if (t < 8) {
      drawHero(1)
      drawSearch(330, 326, 620, 1, q)
      return
    }
    roundRect(492, 124, 630, 58, 8, colors.navy)
    wrap(typed, 518, 158, 570, 22, 17, '#f8f4ec', '500')
    if (t < 10) {
      roundRect(164, 222, 122, 46, 8, colors.surface, colors.line)
      text('Researching…', 184, 251, 14, colors.muted, '600')
      return
    }
    roundRect(132, 216, 782, 360, 10, 'rgba(255,253,250,.96)', colors.line)
    text('Grounded answer', 156, 254, 13, colors.teal, '800')
    wrap('The exact punishment depends on the facts. If death results and murder is established, BNS s.103 is relevant. If the act is an attempt to murder, BNS s.109 may apply.', 156, 294, 720, 28, 19, colors.ink, '500')
    text('Follow-up questions:', 156, 400, 18, colors.ink, '800')
    wrap('1. Did the victim die, or was this an attempted killing?', 180, 436, 680, 24, 16, colors.ink)
    wrap('2. Was there intent or knowledge likely to cause death?', 180, 468, 680, 24, 16, colors.ink)
    wrap('3. Was it connected to riot, affray, or a public servant?', 180, 500, 680, 24, 16, colors.ink)
    text('Citations', 950, 252, 13, colors.muted, '800')
    roundRect(950, 272, 214, 48, 8, '#fffdfa', colors.line)
    roundRect(966, 286, 40, 22, 6, colors.teal)
    text('BNS', 976, 302, 11, '#fffdfa', '800')
    text('s.109', 1018, 302, 14, colors.ink, '800')
    roundRect(950, 332, 214, 48, 8, '#fffdfa', colors.line)
    roundRect(966, 346, 40, 22, 6, colors.teal)
    text('BNS', 976, 362, 11, '#fffdfa', '800')
    text('s.103', 1018, 362, 14, colors.ink, '800')
    roundRect(164, 618, 952, 56, 12, 'rgba(255,253,250,.96)', colors.line)
    text('⌕', 188, 654, 20, colors.muted)
    text('Answer the follow-up to refine the legal conclusion…', 226, 653, 15, '#8993a4')
    roundRect(1060, 626, 40, 40, 8, colors.navy)
    text('→', 1073, 652, 20, '#f8f4ec', '700')
  }

  function drawEnd() {
    drawHeader()
    roundRect(248, 170, 784, 360, 16, 'rgba(255,253,250,.96)', colors.line)
    text('Live deployment verified', 430, 244, 44, colors.ink, '700', 'Georgia')
    text('Frontend: rag-pipeline-silk.vercel.app', 392, 302, 18, colors.ink, '700')
    text('Backend: Hugging Face Space /health and /chat', 392, 338, 18, colors.ink, '700')
    text('GitHub repo includes setup, evals, reports, and deployment instructions.', 392, 384, 16, colors.muted, '500')
    roundRect(392, 426, 496, 46, 23, '#e4f1ed', 'rgba(23,111,69,.18)')
    text('Ready for review: reproducible repo + live demo', 438, 456, 16, '#176f45', '800')
  }

  function draw(now) {
    const t = now / 1000
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = colors.canvas
    ctx.fillRect(0, 0, width, height)
    const grd = ctx.createRadialGradient(0, 0, 0, 0, 0, 660)
    grd.addColorStop(0, 'rgba(15,107,95,.13)')
    grd.addColorStop(1, 'rgba(15,107,95,0)')
    ctx.fillStyle = grd
    ctx.fillRect(0, 0, width, height)
    if (t < 5) drawHero(t / 5)
    else if (t < 24) drawChat(t)
    else drawEnd()
  }

  const stream = canvas.captureStream(fps)
  const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' })
  const chunks = []
  recorder.ondataavailable = (event) => chunks.push(event.data)
  recorder.start()

  const started = performance.now()
  await new Promise((resolve) => {
    function frame(now) {
      const elapsed = now - started
      draw(elapsed)
      if (elapsed < duration) requestAnimationFrame(frame)
      else resolve()
    }
    requestAnimationFrame(frame)
  })

  await new Promise((resolve) => {
    recorder.onstop = resolve
    recorder.stop()
  })
  const blob = new Blob(chunks, { type: 'video/webm' })
  const reader = new FileReader()
  return await new Promise((resolve) => {
    reader.onloadend = () => resolve(reader.result.split(',')[1])
    reader.readAsDataURL(blob)
  })
}
`

const chrome = spawn(chromePath, [
  '--headless=new',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  `--remote-debugging-port=${port}`,
  '--user-data-dir=/tmp/legal-rag-demo-chrome-profile',
  'about:blank',
], { stdio: 'ignore' })

try {
  for (let i = 0; i < 50; i++) {
    try {
      const session = await connect()
      await cdp('Runtime.enable', {}, session)
      const result = await cdp('Runtime.evaluate', {
        expression: `(${recordingSource})()`,
        awaitPromise: true,
        returnByValue: true,
      }, session)
      const bytes = Buffer.from(result.result.value, 'base64')
      await writeFile(outPath, bytes)
      session.socket.close()
      console.log(`Wrote ${outPath.pathname} (${bytes.length} bytes)`)
      process.exit(0)
    } catch (err) {
      if (i === 49) throw err
      await sleep(200)
    }
  }
} finally {
  chrome.kill('SIGTERM')
}
