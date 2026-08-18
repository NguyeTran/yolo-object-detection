/**
 * Mock detection backend for testing the frontend without FastAPI/YOLO.
 *
 * Serves exactly the API the frontend expects:
 *   POST http://127.0.0.1:8000/api/detect/image   (multipart/form-data, field "file")
 *   -> {
 *        "object_count": 3,
 *        "processing_time_seconds": 0.184,
 *        "detections": [
 *          { "detected_class": "person", "confidence_score": 0.95, "bounding_box": {...} },
 *          ...
 *        ]
 *      }
 *
 * Usage:  node mock-server.mjs     (then run the frontend: npm run dev)
 *
 * Zero dependencies — plain Node HTTP server with CORS enabled.
 */
import http from 'node:http'

const PORT = 8000

// Fake detections (bounding boxes in pixels of the "original" image)
const MOCK_DETECTIONS = [
  {
    detected_class: 'person',
    confidence_score: 0.9523,
    bounding_box: { x_min: 50, y_min: 80, x_max: 240, y_max: 400 },
  },
  {
    detected_class: 'dog',
    confidence_score: 0.8712,
    bounding_box: { x_min: 300, y_min: 200, x_max: 480, y_max: 420 },
  },
  {
    detected_class: 'car',
    confidence_score: 0.7845,
    bounding_box: { x_min: 520, y_min: 150, x_max: 760, y_max: 320 },
  },
]

const server = http.createServer((req, res) => {
  // CORS so the Vite dev server (localhost:5173) can call this API
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', '*')

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    return res.end()
  }

  if (req.method === 'POST' && req.url === '/api/detect/image') {
    // Read the multipart body just to show it was received
    let received = 0
    req.on('data', (chunk) => (received += chunk.length))
    req.on('end', () => {
      // Simulate model inference time
      setTimeout(() => {
        const payload = {
          object_count: MOCK_DETECTIONS.length,
          processing_time_seconds: 0.184,
          detections: MOCK_DETECTIONS,
        }
        console.log(
          `[mock-server] POST /api/detect/image -> ${payload.object_count} detections (${received} bytes received)`
        )
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify(payload))
      }, 600)
    })
    return
  }

  res.writeHead(404, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ detail: 'Not Found' }))
})

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`❌ Port ${PORT} is already in use.`)
    console.error('   Either the mock server is already running, or your real FastAPI backend is on port 8000.')
    console.error('   Stop the other process first, or change PORT in mock-server.mjs.')
    process.exit(1)
  }
  throw err
})

server.listen(PORT, () => {
  console.log(`✅ Mock detection API running at http://127.0.0.1:${PORT}`)
  console.log('   Endpoint: POST /api/detect/image')
  console.log('   Waiting for "Upload and Detect" from the frontend...')
})
