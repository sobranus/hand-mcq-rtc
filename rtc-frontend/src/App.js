import React, { useState, useRef, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import InstructionsPage from './components/InstructionsPage';
import QuizPage from './components/QuizPage';
import CompletePage from './components/CompletePage';
import './App.css';
export const globalStream = { stream: null };

function App() {
  const [currentPage, setCurrentPage] = useState('login');
  const [dataChannel, setDataChannel] = useState(null);
  const peerConnection = useRef(null);
  const websocket = useRef(null);
  const connectionInitiated = useRef(false);
  let component_int = useRef(1);

  const [currentInfoBar, setCurrentInfoBar] = useState({
    text: "Use your hands",
    color: "yellow"});
  const [currentQuestion, setCurrentQuestion] = useState('Question');
  const [imageData, setImageData] = useState(null);
  const [quizScore, setQuizScore] = useState(0);
  const [handDown, sethandDown] = useState(0);

  useEffect(() => {

    if (connectionInitiated.current) {
      return;
    }
    connectionInitiated.current = true;

    const socket = new WebSocket(`wss://super-present-antelope.ngrok-free.app/ws/rtc/`);
    websocket.current = socket;

    socket.onopen = () => {
      console.log('WebSocket connection established with server');
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleSignalingData(data);
    };
    
    socket.onclose = () => {
      console.log('WebSocket connection closed');
      connectionInitiated.current = false;
    };
  }, []);

  const setupPeerConnection = async () => {
    try {
      const configuration = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' },
          {
            urls: 'turn:relay1.expressturn.com:3478',
            username: 'ef4D0W10T15FXPIADE',
            credential: 'q5aQSKhZ2swakoCM',
          },
        ]
      };
      
      const pc = new RTCPeerConnection(configuration);
      peerConnection.current = pc;

      const dc = peerConnection.current.createDataChannel("signal");
      dc.onopen = () => console.log("DataChannel is open");
      dc.onclose = () => console.log("DataChannel closed");
      setDataChannel(dc);
      
      await navigator.mediaDevices.getUserMedia({ video: true, audio: false }).then((stream) => {
        stream.getTracks().forEach(track => {
          pc.addTrack(track, stream);
        });
      }, (err) => {
        alert('Could not acquire media: ' + err);
      });
      
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          console.log(event.candidate)
          if (event.candidate.component === 'rtp') {
            component_int.current = 1
          } else if (event.candidate.component === 'rtcp') {
            component_int.current = 2
          } else {
            component_int.current = null
          }
          try {
            websocket.current.send(JSON.stringify({
              type: 'ice_candidate',
              candidate: event.candidate
            }));
            console.log('Sent ICE candidate to server');
          } catch (error) {
            console.error('Error sending ICE candidate:', error);
          }
        }
      };
      
      pc.ondatachannel = (event) => {
        const channel = event.channel;
        channel.onmessage = (event) => {
          const quizData = JSON.parse(event.data)
          if (quizData.message === 'hand_unseen') {
            setCurrentInfoBar(quizData)
          } else if (quizData.message === 'hand_seen') {
            setCurrentInfoBar(quizData)
          } else if (quizData.message === 'new_question') {
            setCurrentQuestion(quizData);
            setImageData(`data:image/png;base64,${quizData.image}`);
          } else if (quizData.message === 'quiz_finished') {
            handleQuizComplete();
            setQuizScore(quizData.score);
            sethandDown(quizData.hands_unseen.toFixed(2))
          }
        };
      };

      pc.addEventListener('track', (evt) => {
        globalStream.stream = evt.streams[0];
        document.getElementById('output-video').srcObject = globalStream.stream
      });

      pc.oniceconnectionstatechange = () => {
        console.log('ICE connection state:', pc.iceConnectionState);
      };
      createOffer();
      
    } catch (error) {
      console.error('Error setting up peer connection:', error);
    }
  };

  const createOffer = async () => {
    try {
      const offer = await peerConnection.current.createOffer()
      await peerConnection.current.setLocalDescription(offer)
      websocket.current.send(JSON.stringify({
          type: 'offer',
          offer: {
              sdp: offer.sdp,
              type: offer.type
          }
      }));
      console.log('Offer sent to server');
    } catch (error) {
      console.error('Error sending offer:', error);
    }
  };

  const handleSignalingData = async (data) => {
    switch (data.type) {
      case 'answer':
        await handleAnswer(data.answer);
        break;
      case 'ice_candidate':
        handleRemoteICECandidate(data.candidate);
        break;
      default:
        console.warn('Unknown message type:', data.type);
    }
  };

  const handleAnswer = async (answer) => {
    try {
      if (peerConnection.current.signalingState !== "stable") {
        const remoteDesc = new RTCSessionDescription(answer);
        await peerConnection.current.setRemoteDescription(remoteDesc)
      } else {
        console.log('Ignoring answer - connection already in stable state');
      }
    } catch (error) {
      console.error('Error handling server answer:', error);
    }
  };

  const handleRemoteICECandidate = async (candidate) => {
    try {
      if (candidate) {
        console.log('Received ICE candidate from server');
        await peerConnection.current.addIceCandidate(
          new RTCIceCandidate({
            component: candidate.component,
            foundation: candidate.foundation,
            ip: candidate.ip,
            port: candidate.port,
            priority: candidate.priority,
            protocol: candidate.protocol,
            type: candidate.type,
            sdpMid: candidate.sdpMid,
            sdpMLineIndex: candidate.sdpMLineIndex,
          })
        );
      }
    } catch (error) {
      console.error('Error adding received ICE candidate:', error);
    }
  };

  const sendMessage = (message) => {
    if (dataChannel && dataChannel.readyState === "open") {
        dataChannel.send(message);
    } else {
        console.log("DataChannel is not open yet.");
    }
  };



  const handleLogin = (passcode) => {
    // Validate passcode (typically with backend)
    if (passcode === '1234') {
      setCurrentPage('instructions');
      setupPeerConnection();
    } else {
      alert('Invalid Passcode');
    }
  };

  const handleStartQuiz = () => {
    setCurrentPage('quiz');
    sendMessage('quiz_start');
  };

  const handleQuizComplete = () => {
    setCurrentPage('complete');
  };

  const handleReset = () => {
    window.location.reload();
  };

  const renderPage = () => {
    switch(currentPage) {
      case 'login':
        return <LoginPage onLogin={handleLogin} />;
      case 'instructions':
        return <InstructionsPage onStart={handleStartQuiz} />;
      case 'quiz':
        return <QuizPage 
          onQuizComplete={handleQuizComplete} 
          infoBar={currentInfoBar}
          question={currentQuestion} 
          image={imageData} 
        />;
      case 'complete':
        return <CompletePage 
          score={quizScore}
          handDownTime={handDown}
          onReset={handleReset}  
        />;
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