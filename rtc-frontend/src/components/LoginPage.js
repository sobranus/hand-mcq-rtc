import React, { useState } from 'react';

function LoginPage({ onLogin }) {
  const [passcode, setPasscode] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(passcode);
  };

  return (
    <div className="container">
      <h1>Quiz Access</h1>
      <form onSubmit={handleSubmit}>
        <div className="passcode-section">
          <input 
            type="password" 
            className="passcode-input" 
            placeholder="Enter passcode"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
          />
        </div>
        <button type="submit" className="button">Enter Quiz</button>
      </form>
    </div>
  );
}

export default LoginPage;