import React from 'react';

function InstructionsPage({ onStart }) {
  const mockQuizQuestions = [
    {
      id: 1,
      question: 'Sample question 1',
      choices: ['Choice A', 'Choice B', 'Choice C', 'Choice D'],
      image: null
    },
    // More questions...
  ];

  return (
    <div className="container">
      <h1>Quiz Instructions</h1>
      <div className="instructions-content">
        {/* Add actual instructions */}
        <p>Please read the following instructions carefully:</p>
        <ul>
          <li>Use hand gestures to select answers</li>
          <li>You have 3 minutes to complete the quiz</li>
        </ul>
      </div>
      <button 
        className="button" 
        onClick={() => onStart(mockQuizQuestions)}
      >
        Start Quiz
      </button>
    </div>
  );
}

export default InstructionsPage;