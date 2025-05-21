import React from 'react';

function CompletePage({ score, handDownTime, onReset }) {
  return (
    <div className="container">
      <h1>Quiz Complete</h1>
      <div className="completion-message">
        You have successfully completed the quiz!
      </div>
      <div className="completion-message">
        Score: {score}%
        <br />Hands down time: {handDownTime} s
      </div>
      <button className="button" onClick={onReset}>
        Exit
      </button>
    </div>
  );
}

export default CompletePage;