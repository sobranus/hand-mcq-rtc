import React, { useState } from 'react';
import LoginPage from './components/LoginPage';
import InstructionsPage from './components/InstructionsPage';
import QuizPage from './components/QuizPage';
import CompletePage from './components/CompletePage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('login');
  const [quizData, setQuizData] = useState(null);

  const handleLogin = (passcode) => {
    // Validate passcode (you'd typically do this with backend)
    if (passcode === '1234') {
      setCurrentPage('instructions');
    } else {
      alert('Invalid Passcode');
    }
  };

  const handleStartQuiz = (questions) => {
    setQuizData(questions);
    setCurrentPage('quiz');
  };

  const handleQuizComplete = () => {
    setCurrentPage('complete');
  };

  const handleReset = () => {
    setCurrentPage('login');
    setQuizData(null);
  };

  const renderPage = () => {
    switch(currentPage) {
      case 'login':
        return <LoginPage onLogin={handleLogin} />;
      case 'instructions':
        return <InstructionsPage onStart={handleStartQuiz} />;
      case 'quiz':
        return <QuizPage 
          quizData={quizData} 
          onQuizComplete={handleQuizComplete} 
        />;
      case 'complete':
        return <CompletePage onReset={handleReset} />;
      default:
        return <LoginPage onLogin={handleLogin} />;
    }
  };

  return (
    <div className="app-container">
      {renderPage()}
    </div>
  );
}

export default App;