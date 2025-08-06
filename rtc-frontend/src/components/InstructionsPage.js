import React from 'react';

function InstructionsPage({ onStart }) {

  return (
    <div className="container">
      <h1>Quiz Instructions</h1>
      <div className="instructions-content">
        <div className="video-area">
          <video 
            id="output-video"
            autoPlay 
            playsInline
          />
        </div>
        {/* Add actual instructions */}
        <p><br/><br/>Please read the following instructions carefully:<br/><br/>

          Do not start the test if you dont see your camera's video in this page<br/> 
          Use hand gestures to select answers<br/>
          You have 30 minutes to complete the quiz<br/>
        </p>
      </div>
      <button 
        className="button" 
        onClick={() => onStart()}
      >
        Start Quiz
      </button>
    </div>
  );
}

export default InstructionsPage;