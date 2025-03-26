import React from 'react';

function CompletePage({ onReset }) {
  return (
    <div className="container">
      <h1>Quiz Complete</h1>
      <div className="completion-message">
        You have successfully completed the quiz!
      </div>
      <button className="button" onClick={onReset}>
        Exit
      </button>
    </div>
  );
}

export default CompletePage;