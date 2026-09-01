import { useState, useRef } from 'react'

function App() {

  //Save picture user uploaded
  const [selectedFile, setSelectedFile] = useState(null);

  //Save the temporary URL of the uploaded picture
  const [previewUrl, setPreviewUrl] = useState(null);

  //Notice: AI is thinking?
  const [isLoading, setIsLoading] = useState(false);

  //Result from FastAPI
  const [result, setResult] = useState(null);
  const [annotatedImage, setAnnotatedImage] = useState(null);

  //Display the picture to drawing the bounding box
  const imageRef = useRef(null);

  // Video user uploaded
  const [selectedVideo, setSelectedVideo] = useState(null);

  // Temporary URL of the uploaded video
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);

  // Notice: AI is processing video?
  const [isVideoLoading, setIsVideoLoading] = useState(false);

  // Result from FastAPI
  const [videoResult, setVideoResult] = useState(null);

  // URL of processed video
  const [processedVideoUrl, setProcessedVideoUrl] = useState(null);

  //2. Function to handle file selection

  const API_URL = import.meta.env.VITE_API_BASE_URL; // Replace with your FastAPI endpoint

  console.log("API URL:", API_URL);

  const handleFileChange = (event) => {
    // Get the selected file from the input
    const file = event.target.files[0];
    if (!file) return
      // Update the selected file state
      setSelectedFile(file);

      // Create a temporary URL for the selected file to display it
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }

      setPreviewUrl(URL.createObjectURL(file));

      // Reset the result state when a new file is selected
      setResult(null);
      setAnnotatedImage(null);

      if (videoPreviewUrl) {
        URL.revokeObjectURL(videoPreviewUrl);
      }
      setSelectedVideo(null);
      setVideoPreviewUrl(null);
      setVideoResult(null);
      setProcessedVideoUrl(null);
    }

  //3. Function to handle the upload and send the file to FastAPI

  const handleUpload = async () => {
    // Check if a file is selected
    if (!selectedFile) {
      alert('Please select a file first.');
      return;
    }

    // Set loading state to true
    setIsLoading(true);

    // Create a FormData object to send the file
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      // Send the file to FastAPI using fetch
      const response = await fetch(`${API_URL}/api/detect/image`, {
        method: 'POST',
        body: formData,
      });
    
      // Check if the response is OK
      if (!response.ok) {
        throw new Error('Failed to upload the file.');
      }
      
      //Parse the JSON response from FastAPI
      const data = await response.json();

      setResult(data);
      if (data.annotated_image) setAnnotatedImage(`data:image/jpeg;base64,${data.annotated_image}`);

    }
    catch (error) {
      console.error('Error uploading file:', error);
      alert('Error uploading file. Please try again.');
    } finally {
      // Set loading state to false
      setIsLoading(false);
    }
  };

  const handleVideoChange = (event) => {
    const file = event.target.files[0];

    if(!file) return

    if (!file.type.startsWith('video/')) {
      alert('Please select a video file.');
      return;
    }

    setSelectedVideo(file);

    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }

    setVideoPreviewUrl(URL.createObjectURL(file)); 
    setVideoResult(null); 
    setProcessedVideoUrl(null);

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setAnnotatedImage(null);
  }

  const handleVideoUpload = async () => { 
    if (!selectedVideo) { 
      alert('Please select a video first.'); 
      return; 
    }

    setIsVideoLoading(true); 
    setVideoResult(null); 
    setProcessedVideoUrl(null); 
    
    const formData = new FormData(); 
    formData.append('file', selectedVideo);

    try {
      // Send video to FastAPI
      const response = await fetch(
        `${API_URL}/api/detect/video`,
        {
          method: 'POST',
          body: formData,
        }
      );

      // Check response
      if (!response.ok) {
        let errorMessage = 'Failed to process the video.';

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          // Response is not JSON
        }

        throw new Error(errorMessage);
      }

      // Parse JSON response
      const data = await response.json();

      console.log('Video detection result:', data);

      // Save result
      setVideoResult(data);

      // Save processed video URL
      if (data.video_url) {
        let videoUrl = data.video_url;

        // If backend returns relative URL
        if (videoUrl.startsWith('/')) {
          videoUrl = `${API_URL}${videoUrl}`;
        }

        setProcessedVideoUrl(videoUrl);
      }

    } catch (error) {
      console.error('Error processing video:', error);

      alert(
        `Error processing video: ${error.message}`
      );

    } finally {
      // Stop loading
      setIsVideoLoading(false);
    }
  };

  // 4. Build the HTML
  return (
    <div className="app">
      <style>{`
        .app {
          min-height: 100vh;
          background: #14161a;
          color: #e8e9ec;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
          padding: 48px 24px 80px;
        }
        .app-inner { max-width: 880px; margin: 0 auto; }

        .app-title {
          font-size: 42px;
          font-weight: 600;
          letter-spacing: -0.01em;
          margin: 0 0 16px;
        }
        .app-subtitle {
          color: #8a8f98;
          font-size: 18px;
          margin: 0 0 36px;
        }

        .controls-row {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
          margin-bottom: 28px;
        }

        input[type="file"] {
          color: #c7cad1;
          font-size: 14px;
        }
        input[type="file"]::file-selector-button {
          background: #1f2228;
          color: #e8e9ec;
          border: 1px solid #30343c;
          border-radius: 6px;
          padding: 8px 14px;
          font-size: 13px;
          cursor: pointer;
          margin-right: 12px;
        }
        input[type="file"]::file-selector-button:hover {
          background: #262a31;
        }

        .btn-primary {
          background: #e8a33d;
          color: #14161a;
          border: none;
          border-radius: 6px;
          padding: 10px 20px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s ease;
        }
        .btn-primary:hover:not(:disabled) { background: #f0b358; }
        .btn-primary:disabled {
          background: #2a2d33;
          color: #6b6f78;
          cursor: not-allowed;
        }

        section.block { margin-top: 56px; }
        .block-heading {
          font-size: 18px;
          font-weight: 600;
          margin: 0 0 20px;
          padding-bottom: 10px;
          border-bottom: 1px solid #24272d;
        }

        .media-row {
          display: flex;
          gap: 20px;
          align-items: flex-start;
          flex-wrap: wrap;
        }

        .viewfinder {
          position: relative;
          display: inline-block;
          padding: 10px;
          flex: 1;
          min-width: 280px;
        }
        .viewfinder::before,
        .viewfinder::after,
        .viewfinder-frame::before,
        .viewfinder-frame::after {
          content: '';
          position: absolute;
          width: 18px;
          height: 18px;
          border: 2px solid #e8a33d;
        }
        .viewfinder::before { top: 0; left: 0; border-right: none; border-bottom: none; }
        .viewfinder::after { top: 0; right: 0; border-left: none; border-bottom: none; }
        .viewfinder-frame::before { bottom: 0; left: 0; border-right: none; border-top: none; }
        .viewfinder-frame::after { bottom: 0; right: 0; border-left: none; border-top: none; }

        .media-label {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: #8a8f98;
          margin: 0 0 10px;
        }

        .media-img, .media-video {
          max-width: 100%;
          width: 100%;
          height: auto;
          display: block;
          border-radius: 2px;
        }

        .result-panel {
          background: #1a1c21;
          border: 1px solid #24272d;
          border-radius: 8px;
          padding: 20px;
          min-width: 260px;
          flex: 0 0 260px;
        }
        .result-panel h3, .result-panel h4 {
          margin: 0 0 14px;
          font-size: 15px;
          font-weight: 600;
        }
        .result-panel hr {
          border: none;
          border-top: 1px solid #262a31;
          margin: 14px 0;
        }
        .result-panel p {
          margin: 6px 0;
          font-size: 13px;
          color: #b0b4bb;
        }
        .result-panel p b, .result-panel li b {
          color: #e8e9ec;
          font-family: 'SFMono-Regular', Consolas, monospace;
          font-weight: 600;
        }
        .result-panel .placeholder {
          color: #6b6f78;
          font-size: 13px;
        }
        .result-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .result-list li {
          font-size: 13px;
          color: #c7cad1;
          display: flex;
          justify-content: space-between;
          gap: 10px;
        }
      `}</style>

      <div className="app-inner">
        <h1 className="app-title">Object Detection</h1>
        <p className="app-subtitle">Tải ảnh hoặc video lên để nhận diện đối tượng bằng YOLO</p>

        {/* Chọn ảnh */}
        <section className="block">
          <h2 className="block-heading">Nhận diện ảnh</h2>

          <div className="controls-row">
            <input type="file" accept="image/*" onChange={handleFileChange} />
            <button
              onClick={handleUpload}
              disabled={isLoading || !selectedFile}
              className="btn-primary"
            >
              {isLoading ? 'Đang xử lý...' : 'Tải lên & nhận diện ảnh'}
            </button>
          </div>

          {/* Ảnh + kết quả */}
          {previewUrl && (
            <div className="media-row">
              <div className="viewfinder">
                <div className="viewfinder-frame">
                  <img
                    ref={imageRef}
                    src={annotatedImage || previewUrl}
                    alt="Preview"
                    className="media-img"
                  />
                </div>
              </div>

              <div className="result-panel">
                <h3>Kết quả nhận diện</h3>
                {result ? (
                  <div>
                    <p>Số đối tượng: <b>{result.object_count}</b></p>
                    <p>Thời gian xử lý: <b>{result.processing_time_seconds}</b></p>
                    <hr />
                    <ul className="result-list">
                      {result.detections.map((item, index) => (
                        <li key={index}>
                          <span>{item.detected_class}</span>
                          <b>{Math.round(item.confidence_score * 100)}%</b>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="placeholder">Nhấn "Tải lên & nhận diện" để xem kết quả.</p>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Video */}
        <section className="block">
          <h2 className="block-heading">Nhận diện video</h2>

          <div className="controls-row">
            <input type="file" accept="video/*" onChange={handleVideoChange} />
            <button
              onClick={handleVideoUpload}
              disabled={isVideoLoading || !selectedVideo}
              className="btn-primary"
            >
              {isVideoLoading ? 'Đang xử lý video...' : 'Tải lên & nhận diện video'}
            </button>
          </div>

          {videoPreviewUrl && (
            <div className="media-row">
              <div style={{ flex: '1', minWidth: '280px' }}>
                <p className="media-label">
                  {processedVideoUrl ? 'Video đã xử lý' : 'Video gốc'}
                </p>
                <video
                  key={processedVideoUrl || videoPreviewUrl}
                  controls
                  className="media-video"
                >
                  <source
                    src={processedVideoUrl || videoPreviewUrl}
                    type={selectedVideo.type}
                  />
                  Trình duyệt của bạn không hỗ trợ phát video.
                </video>
              </div>

              <div className="result-panel">
                <h3>Kết quả video</h3>
                {videoResult ? (
                  <div>
                    <p>Số khung hình: <b>{videoResult.frames_processed}</b></p>
                    <p>FPS: <b>{videoResult.fps}</b></p>
                    <p>Thời lượng: <b>{videoResult.duration_seconds}s</b></p>
                    <p>Thời gian xử lý: <b>{videoResult.processing_time_seconds}s</b></p>
                    <hr />
                    <h4>Đối tượng phát hiện</h4>
                    {videoResult.summary_counts && Object.keys(videoResult.summary_counts).length > 0 ? (
                      <ul className="result-list">
                        {Object.entries(videoResult.summary_counts).map(([className, count]) => (
                          <li key={className}>
                            <span>{className}</span>
                            <b>{count}</b>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="placeholder">Không phát hiện đối tượng nào.</p>
                    )}
                  </div>
                ) : (
                  <p className="placeholder">Nhấn "Tải lên & nhận diện video" để xử lý video.</p>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default App;