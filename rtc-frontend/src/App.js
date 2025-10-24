/**
 * App.js
 * Main React component for the WebRTC MCQ application.
 * Handles the web UI flow and real-time video/data communication
 * with a remote server through RTCPeerConnection via WebSocket for signaling.
 */


import React, { useState, useRef, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import InstructionsPage from './components/InstructionsPage';
import QuizPage from './components/QuizPage';
import CompletePage from './components/CompletePage';
import './App.css';

// Global MediaStream object for the video across components
export const globalStream = { stream: null };

function App() {
  // ----------- UI & quiz state -----------
  const [currentPage, setCurrentPage] = useState('login');
  const [currentInfoBar, setCurrentInfoBar] = useState({
    text: "Use your hands",
    color: "yellow"});
  const [currentQuestion, setCurrentQuestion] = useState('Question');
  const [imageData, setImageData] = useState(null);
  const [quizScore, setQuizScore] = useState(0);
  const [handDown, sethandDown] = useState(0);            // Time hands were not detected

  // ----------- Connection & signaling refs -----------
  const [dataChannel, setDataChannel] = useState(null);   // RTCDataChannel instance
  const peerConnection = useRef(null);                    // RTCPeerConnection instance
  const websocket = useRef(null);                         // WebSocket signaling channel
  const connectionInitiated = useRef(false);              // Prevent multiple connections
  let component_int = useRef(1);                          // Track ICE component type

  
  /**
   * Establish WebSocket connection to the signaling server once on mount.
   * This handles the WebRTC offer/answer exchange and ICE candidate relay.
   */
  useEffect(() => {
    if (connectionInitiated.current) return;
    connectionInitiated.current = true;

    const socket = new WebSocket(`wss://super-present-antelope.ngrok-free.app/ws/rtc/`);
    websocket.current = socket;

    socket.onopen = () => console.log('WebSocket connection established with server');
    
    // Handle incoming signaling messages (answer, ICE candidates)
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleSignalingData(data);
    };
    
    socket.onclose = () => {
      console.log('WebSocket connection closed');
      connectionInitiated.current = false;
    };
  }, []);


  /**
   * Create and configure RTCPeerConnection, attach local video,
   * set up DataChannel and ICE candidate handlers.
   */
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

      // Create a DataChannel for exam (data,state,text,img) messages
      const dc = peerConnection.current.createDataChannel("signal");
      dc.onopen = () => console.log("DataChannel is open");
      dc.onclose = () => console.log("DataChannel closed");
      setDataChannel(dc);
      
      // Capture local webcamera video and add to the rtc track stream
      await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then((stream) => {
        stream.getTracks().forEach(track => pc.addTrack(track, stream));
      }, (err) => alert('Could not acquire media: ' + err));
      
      // Send ICE candidates to server through websocket when found
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          console.log(event.candidate)

          // Track component type for debugging
          if (event.candidate.component === 'rtp') component_int.current = 1;
          else if (event.candidate.component === 'rtcp') component_int.current = 2;
          else component_int.current = null;

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
      
      // Listen for DataChannel created by remote peer (if any)
      pc.ondatachannel = (event) => {
        const channel = event.channel;
        channel.onmessage = (event) => {
          const quizData = JSON.parse(event.data)

          // Handle different quiz-related messages
          if (quizData.message === 'hand_unseen' || quizData.message === 'hand_seen') {
            setCurrentInfoBar(quizData)
          } else if (quizData.message === 'new_question') {
            console.time("myOperation");
            setCurrentQuestion(quizData);
            if (quizData.image) {
              setImageData(`data:image/png;base64,${quizData.image}`);
            } else {
              setImageData(null);
            }
            console.timeEnd("myOperation");
          } else if (quizData.message === 'quiz_finished') {
            handleQuizComplete();
            setQuizScore(quizData.score);
            sethandDown(quizData.hands_unseen.toFixed(2))
          }
        };
      };

      // Display processed video stream from server (if any)
      pc.addEventListener('track', (evt) => {
        globalStream.stream = evt.streams[0];
        document.getElementById('output-video').srcObject = globalStream.stream
      });

      pc.oniceconnectionstatechange = () => {
        console.log('ICE connection state:', pc.iceConnectionState);
      };

      // Begin SDP offer/answer handshake
      createOffer();
      
    } catch (error) {
      console.error('Error setting up peer connection:', error);
    }
  };


  /**
   * Create an SDP offer and send it to the signaling server.
   */
  const createOffer = async () => {
    try {
      const offer = await peerConnection.current.createOffer()
      await peerConnection.current.setLocalDescription(offer)
      websocket.current.send(JSON.stringify({
          type: 'offer',
          offer: { sdp: offer.sdp, type: offer.type }
      }));
      console.log('Offer sent to server');
    } catch (error) {
      console.error('Error sending offer:', error);
    }
  };


  /**
   * Handle signaling messages received over WebSocket channel.
   */
  const handleSignalingData = async (data) => {
    switch (data.type) {
      case 'answer':
        await handleAnswer(data.answer);
        break;
      case 'ice_candidate':
        handleRemoteICECandidate(data.candidate);
        break;
      case 'login':
        if (data.valid == '1') {
          setCurrentPage('instructions');
          setupPeerConnection();
        } else {
          alert('Invalid ID or Passcode!');
        }
      default:
        console.warn('Unknown message type:', data.type);
    }
  };


  /**
   * Apply remote SDP answer to complete the connection.
   */
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


  /**
   * Add ICE candidates received from the remote peer.
   */
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


  /**
   * Send a message through the DataChannel to the server.
   */
  const sendMessage = (message) => {
    if (dataChannel && dataChannel.readyState === "open") {
        dataChannel.send(message);
    } else {
        console.log("DataChannel is not open yet.");
    }
  };


  // ----------- UI Event Handlers -----------

  // Validate credentials and move to instructions page
  const handleLogin = (passcode, userId) => {
    try {
      websocket.current.send(JSON.stringify({
        type: 'login',
        username: userId,
        password: passcode
      }));
      console.log('Sent Login info to server');
    } catch (error) {
      console.error('Error sending Login info:', error);
    }
  };

  // Start quiz and notify server
  const handleStartQuiz = () => {
    setCurrentPage('quiz');
    sendMessage('quiz_start');
  };

  // Display completion page
  const handleQuizComplete = () => {
    setCurrentPage('complete');
  };

  // Reload entire app to reset state
  const handleReset = () => {
    window.location.reload();
  };


  /**
   * Render the appropriate page component based on currentPage state.
   */
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

  // Main app container
  return (
    <div className="app-container">
      {renderPage()}
    </div>
  );
}

export default App;