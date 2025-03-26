import React, { useState, useEffect } from 'react';

function QuizPage({ quizData, onQuizComplete }) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(180);
  const [selectedAnswer, setSelectedAnswer] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 0) {
          clearInterval(timer);
          onQuizComplete();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [onQuizComplete]);

  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const handleNextQuestion = () => {
    if (currentQuestion < quizData.length - 1) {
      setCurrentQuestion(prev => prev + 1);
      setSelectedAnswer(null);
    } else {
      onQuizComplete();
    }
  };

  const question = quizData[currentQuestion];

  return (
    <div className="container-quiz">
      <div className="quiz-header">
        <div className="question-counter">
          Question {currentQuestion + 1} of {quizData.length}
        </div>
        <div className="timer">{formatTime(timeRemaining)}</div>
      </div>
      <div className="quiz-container">
        <div className="left-section">
          <div className="question-area">
            <div>{question.question}</div>
            {question.image && (
              <img 
                src={question.image} 
                alt="Question" 
                className="question-image" 
              />
            )}
          </div>
          <div className="video-area">
            <div className="video-placeholder">
              Camera feed will appear here
            </div>
          </div>
          <div className="info-bar">
            Use hand gestures to select your answer
          </div>
        </div>
        <div className="right-section">
          {question.choices.map((choice, index) => (
            <div 
              key={index} 
              className={`choice-box ${selectedAnswer === index ? 'selected' : ''}`}
              onClick={() => setSelectedAnswer(index)}
            >
              <div className="choice-number">{index + 1}</div>
              <div className="choice-text">{choice}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default QuizPage;