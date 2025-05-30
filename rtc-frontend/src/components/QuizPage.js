import React, { useState, useEffect } from 'react';
import { globalStream } from "../App";

function QuizPage({ infoBar, question, image, onQuizComplete }) {
  const [timeRemaining, setTimeRemaining] = useState(180);

  useEffect(() => {
    document.getElementById('output-video').srcObject = globalStream.stream
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

  return (
    <div className="container-quiz">
      <div className="quiz-header">
        <div className="question-counter">
          Question No.
        </div>
        <div className="timer">{formatTime(timeRemaining)}</div>
      </div>
      <div className="quiz-container">
        <div className="left-section">
          <div className="info-bar" style={{ backgroundColor: infoBar.color }}>
            {infoBar.text}
          </div>
          <div className="video-area">
            <video 
              id="output-video"
              autoPlay 
              playsInline
            />
          </div>
          <div className="question-area">
            <img 
              src={image} 
              alt="image" 
              className="question-image" 
            />
            <div><p>{question.question}</p></div>
          </div>
        </div>
        <div className="right-section">
          <div className="choice-box" >
            <div className="choice-number">1</div>
            <div id="choice1" className="choice-text">{question.choice1}</div>
          </div>
          <div className="choice-box" >
            <div className="choice-number">2</div>
            <div id="choice2" className="choice-text">{question.choice2}</div>
          </div>
          <div className="choice-box" >
            <div className="choice-number">3</div>
            <div id="choice3" className="choice-text">{question.choice3}</div>
          </div>
          <div className="choice-box" >
            <div className="choice-number">4</div>
            <div id="choice4" className="choice-text">{question.choice4}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default QuizPage;