import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'

/**
 * Fake API response matching the FastAPI contract expected by App.jsx:
 * POST http://127.0.0.1:8000/api/detect/image  (multipart/form-data, field "file")
 * -> { object_count, processing_time_seconds, detections: [{ detected_class, confidence_score, bounding_box: { x_min, y_min, x_max, y_max } }] }
 */
const mockDetectResponse = {
  object_count: 3,
  processing_time_seconds: 0.184,
  detections: [
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
  ],
}

const API_URL = 'http://127.0.0.1:8000/api/detect/image'

/** Create a fake image File for the <input type="file"> */
function makeFakeImageFile() {
  return new File(['fake-image-bytes'], 'test-photo.png', { type: 'image/png' })
}

/** Select a file in the file input (triggers preview + enables the button) */
function selectFile(file = makeFakeImageFile()) {
  const input = document.querySelector('input[type="file"]')
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

/**
 * getByText only matches direct text nodes, but the result list renders
 * `<li><b>person</b> (Confidence: 95%)</li>` — match on full textContent instead.
 */
function queryByFullText(text) {
  return screen.queryByText((_, element) => element?.textContent === text)
}

function getByFullText(text) {
  const el = queryByFullText(text)
  if (!el) throw new Error(`Unable to find element with textContent: "${text}"`)
  return el
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App – Detection Result', () => {
  it('shows the placeholder text before detecting', () => {
    render(<App />)
    selectFile()

    expect(screen.getByAltText('Preview')).toBeInTheDocument()
    expect(
      screen.getByText(/Press "Upload and Detect" to see results\./i)
    ).toBeInTheDocument()
  })

  it('disables the "Upload and Detect" button until a file is selected', () => {
    render(<App />)
    const button = screen.getByRole('button', { name: /upload and detect/i })
    expect(button).toBeDisabled()

    selectFile()
    expect(screen.getByRole('button', { name: /upload and detect/i })).toBeEnabled()
  })

  it('calls the API with FormData and renders the detection result after clicking "Upload and Detect"', async () => {
    // Deferred fetch: lets us observe the loading state before the response arrives
    let resolveFetch
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        })
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const file = selectFile()
    fireEvent.click(screen.getByRole('button', { name: /upload and detect/i }))

    // --- Loading state ---
    expect(await screen.findByText(/Uploading\.\.\./i)).toBeInTheDocument()

    // --- API contract ---
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(fetchMock).toHaveBeenCalledWith(
      API_URL,
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    )
    const sentBody = fetchMock.mock.calls[0][1].body
    expect(sentBody.get('file')).toBe(file)

    // Deliver the mock detection response
    resolveFetch(
      new Response(JSON.stringify(mockDetectResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    // --- Detection Result panel ---
    expect(await screen.findByText('Detection Result')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument() // object_count
    expect(screen.getByText('0.184')).toBeInTheDocument() // processing_time_seconds

    // Each detection label: "class (Confidence: NN%)" — text is split by <b>, match textContent
    expect(getByFullText('person (Confidence: 95%)')).toBeInTheDocument()
    expect(getByFullText('dog (Confidence: 87%)')).toBeInTheDocument()
    expect(getByFullText('car (Confidence: 78%)')).toBeInTheDocument()

    // Placeholder is gone
    expect(
      screen.queryByText(/Press "Upload and Detect" to see results\./i)
    ).not.toBeInTheDocument()

    // --- Bounding box labels drawn over the image ---
    expect(screen.getByText('person (95%)')).toBeInTheDocument()
    expect(screen.getByText('dog (87%)')).toBeInTheDocument()
    expect(screen.getByText('car (78%)')).toBeInTheDocument()

    // Button is re-enabled after loading finishes
    expect(screen.getByRole('button', { name: /upload and detect/i })).toBeEnabled()
  })

  it('shows an alert when the API returns an error', async () => {
    const alertSpy = vi.fn()
    vi.stubGlobal('alert', alertSpy)
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('Server Error', { status: 500 })))
    )

    render(<App />)
    selectFile()
    fireEvent.click(screen.getByRole('button', { name: /upload and detect/i }))

    await waitFor(() => expect(alertSpy).toHaveBeenCalledWith('Error uploading file. Please try again.'))

    // Result panel still shows the placeholder
    expect(
      screen.getByText(/Press "Upload and Detect" to see results\./i)
    ).toBeInTheDocument()
  })

  it('resets the previous result when a new file is selected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify(mockDetectResponse), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        )
      )
    )

    render(<App />)
    selectFile()
    fireEvent.click(screen.getByRole('button', { name: /upload and detect/i }))
    expect(await screen.findByText('Detection Result')).toBeInTheDocument()
    expect(getByFullText('person (Confidence: 95%)')).toBeInTheDocument()

    // Pick another image -> result must be cleared
    selectFile(makeFakeImageFile())
    expect(
      screen.getByText(/Press "Upload and Detect" to see results\./i)
    ).toBeInTheDocument()
    expect(queryByFullText('person (Confidence: 95%)')).not.toBeInTheDocument()
  })
})
