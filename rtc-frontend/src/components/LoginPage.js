import React, { useState } from 'react';

function LoginPage({ onLogin }) {
  const [passcode, setPasscode] = useState('');
  const [userId, setUserId] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(passcode, userId);
  };

  return (
    <div className="container">
      <h1>Quiz Access</h1>
      <form onSubmit={handleSubmit}>
        <div className="user_id-section">
          <div className="invisible-spacer"></div>
          <strong className="form-label">ID : </strong>
          <input 
            type="text" 
            className="user_id-input" 
            placeholder="Enter ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </div>
        <div className="passcode-section">
          <strong className="form-label">Passcode : </strong>
          <input 
            type="password" 
            className="passcode-input" 
            placeholder="Enter Passcode"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
          />
        </div>
        <button type="submit" className="button">Login</button>
      </form>
    </div>
  );
}

export default LoginPage;