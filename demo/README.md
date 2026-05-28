# Demo Video

`legal-rag-demo.webm` is a short, silent 30-second overview for reviewers. It
shows the premium chat UI, an ambiguous legal question, grounded citations, and
targeted follow-up questions.

Regenerate it from the repo root with:

```bash
node demo/create_demo_video.mjs
```

The generator uses local Chrome's built-in canvas `MediaRecorder`; it does not
need ffmpeg or extra npm packages.
