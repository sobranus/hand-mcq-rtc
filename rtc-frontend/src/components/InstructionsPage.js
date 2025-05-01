import React from 'react';

function InstructionsPage({ onStart }) {

  return (
    <div className="container">
      <h1>Quiz Instructions</h1>
      <div className="instructions-content">
        <video 
          id="output-video"
          autoPlay 
          playsInline
        />
        {/* Add actual instructions */}
        <p>Please read the following instructions carefully:</p>
        <ul>
          <li>Use hand gestures to select answers</li>
          <li>You have 3 minutes to complete the quiz</li>
        </ul>
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