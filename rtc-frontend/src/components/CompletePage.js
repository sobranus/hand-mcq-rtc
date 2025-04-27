import React from 'react';

function CompletePage({ score, handDownTime, onReset }) {
  return (
    <div className="container">
      <h1>Quiz Complete</h1>
      <div className="completion-message">
        You have successfully completed the quiz!
      </div>
      <div className="quiz-score">
        Score: {score}/100
      </div>
      <div className="hand-down">
        Hand down time: {handDownTime} s
      </div>
      <button className="button" onClick={onReset}>
        Exit
      </button>
    </div>
  );
}

export default CompletePage;