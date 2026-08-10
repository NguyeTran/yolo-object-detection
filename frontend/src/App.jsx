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

  return (
    <>
      <section id="center">
        <div className="hero">
          <img src={heroImg} className="base" width="170" height="179" alt="" />
          <img src={reactLogo} className="framework" alt="React logo" />
          <img src={viteLogo} className="vite" alt="Vite logo" />
        </div>
        <div>
          <h1>Get started</h1>
          <p>
            Edit <code>src/App.jsx</code> and save to test <code>HMR</code>
          </p>
        </div>
        <button
          type="button"
          className="counter"
          onClick={() => setCount((count) => count + 1)}
        >
          Count is {count}
        </button>
      </section>

      <div className="ticks"></div>

      <section id="next-steps">
        <div id="docs">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#documentation-icon"></use>
          </svg>
          <h2>Documentation</h2>
          <p>Your questions, answered</p>
          <ul>
            <li>
              <a href="https://vite.dev/" target="_blank">
                <img className="logo" src={viteLogo} alt="" />
                Explore Vite
              </a>
            </li>
            <li>
              <a href="https://react.dev/" target="_blank">
                <img className="button-icon" src={reactLogo} alt="" />
                Learn more
              </a>
            </li>
          </ul>
        </div>
        <div id="social">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#social-icon"></use>
          </svg>
          <h2>Connect with us</h2>
          <p>Join the Vite community</p>
          <ul>
            <li>
              <a href="https://github.com/vitejs/vite" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#github-icon"></use>
                </svg>
                GitHub
              </a>
            </li>
            <li>
              <a href="https://chat.vite.dev/" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#discord-icon"></use>
                </svg>
                Discord
              </a>
            </li>
            <li>
              <a href="https://x.com/vite_js" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#x-icon"></use>
                </svg>
                X.com
              </a>
            </li>
            <li>
              <a href="https://bsky.app/profile/vite.dev" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#bluesky-icon"></use>
                </svg>
                Bluesky
              </a>
            </li>
          </ul>
        </div>
      </section>

      <div className="ticks"></div>
      <section id="spacer"></section>
    </>
  )
}

export default App
