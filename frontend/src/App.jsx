import { useState, useRef } from 'react'
import './App.css'

function App() {
  // 1. State to save data

  //Save picture user uploaded
  const [selectedFile, setSelectedFile] = useState(null);

  //Save the temporary URL of the uploaded picture
  const [previewUrl, setPreviewUrl] = useState(null);

  //Notice: AI is thinking?
  const [isLoading, setIsLoading] = useState(false);

  //Result from FastAPI
  const [result, setResult] = useState(null);

  //Display the picture to drawing the bounding box
  const imageRef = useRef(null);

  //2. Function to handle file selection

  const handleFileChange = (event) => {
    // Get the selected file from the input
    const file = event.target.files[0];
    if (file) {
      // Update the selected file state
      setSelectedFile(file);

      // Create a temporary URL for the selected file to display it
      setPreviewUrl(URL.createObjectURL(file));

      // Reset the result state when a new file is selected
      setResult(null);
    }
  };

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
      const response = await fetch('http://127.0.0.1:8000/api/detect/image', {
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
    }
    catch (error) {
      console.error('Error uploading file:', error);
      alert('Error uploading file. Please try again.');
    } finally {
      // Set loading state to false
      setIsLoading(false);
    }
  };

  // 4. Build the HTML
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Object Detection with FastAPI</h1>

      {/*Button to select a file */}
      <div style={{ marginBottom: '20px', display: 'flex', gap : '10px', alignItems: 'center' }}>
        <input type="file" accept="image/*" onChange={handleFileChange} />

        <button
          onClick={handleUpload}
          disabled={isLoading || !selectedFile}
          style={{ padding: '10px 20px', cursor: isLoading || !selectedFile ? 'not-allowed' : 'pointer' }}
          >
          {isLoading ? 'Uploading...' : 'Upload and Detect'}
          </button>
      </div>

      {/*Display the uploaded picture */}
      {previewUrl && (
        <div style={{ display : 'flex', gap : '20px', alignItems : 'flex-start', marginBottom: '20px' }}>

          {/*Left side: Display the uploaded picture */}
          <div style={{ position: 'relative' }}>
            <img
              ref={imageRef}
              src={previewUrl}
              alt="Preview"
              style={{ maxWidth: '100%', height: 'auto', display: 'block' }}
            />

            {/*Draw bounding boxes if result is available */}

            {result && result.detections.length > 0 && (
              <div sytle={{
                position: 'absolute',
                top = '10%', left = '10%',
                width = '100px', height = '150px',
                border = '3px solid red',
                boxSizing = 'border-box',
              }}>
                  <span sytle={{ backgroundColor: 'red', color: 'white', padding: '2px 5px', fontSize: '12px', position: 'absolute', top: '-20px', left: '-3px' }}>
                  
                  </span>
               </div>
             )}
          </div>

          {/*Right side: Display the result from FastAPI */}
          <div style={{ backgroundColor: '#f0f0f0', padding: '15px', borderRadius: '8px', minWidth: '250px' }}>
            <h3 style={{marginTop: '0'}}>Detection Result</h3>
            {result ? (
              <div>
                <p>Number of Detections: <b>{result.object_count}</b></p>
                <p>Runtime: <b>{result.processing_time_seconds}</b></p>
                <hr/>
                <ul style={{ paddingLeft: '20px' }}>
                  {result.detections.map((item, index) => (
                    <li key={index}>
                      <b>{item.detected_class}</b> (Confidence: {Math.round(item.confidence_score * 100)}%)
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p>Press "Upload and Detect" to see results.</p>
            )}
          </div>

        </div>
      )}
    </div>
  );
}

export default App;
