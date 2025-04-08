import React from 'react';

function CompletePage({ score, onReset }) {
  return (
    <div className="container">
      <h1>Quiz Complete</h1>
      <div className="completion-message">
        You have successfully completed the quiz!
      </div>
      <div className="completion-message">
        Score: {score}/100
      </div>
      <button className="button" onClick={onReset}>
        Exit
      </button>
    </div>
  );
}

export default CompletePage;