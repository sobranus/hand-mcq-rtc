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

  const [currentQuestion, setCurrentQuestion] = useState('Question');
  const [imageData, setImageData] = useState(null);

  useEffect(() => {

    if (connectionInitiated.current) {
      console.log('Connection already initiated, skipping');
      return;
    }
    connectionInitiated.current = true;

    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/rtc/`);
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
          { urls: 'stun:stun1.l.google.com:19302' }
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
      // const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      // setLocalStream(stream);
      // document.getElementById('input-video').srcObject = stream;
      // stream.getTracks().forEach((track) => {
      //   pc.addTrack(track, stream);
      // });
      
      pc.onicecandidate = (event) => {
        if (event.candidate) {
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
              candidate: {
                component: component_int.current,
                foundation: event.candidate.foundation,
                address: event.candidate.address,
                port: event.candidate.port,
                priority: event.candidate.priority,
                protocol: event.candidate.protocol,
                type: event.candidate.type,
                sdpMid: event.candidate.sdpMid,
                sdpMLineIndex: event.candidate.sdpMLineIndex,
              },
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
          setCurrentQuestion(quizData);
          setImageData(`data:image/png;base64,${quizData.image}`);
        };
      };

      pc.addEventListener('track', (evt) => {
        globalStream.stream = evt.streams[0];
        document.getElementById('output-video').srcObject = globalStream.stream
      });
      // pc.ontrack = (event) => {
      //   // if (event.track.kind === 'video') {
      //   //   if (event.streams && event.streams[0]) {
      //   //     outputVideoRef.current.srcObject = event.streams[0];
      //   //   }
      //   // }
      //   console.log('ontrack');
      //   event.streams.forEach(stream => {
      //     stream.getTracks().forEach(track => {
      //     });
      //     console.log('displaying remote track');
      //     document.getElementById('output-video').srcObject = stream[0];
      //   });
      // };

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
      
      // await new Promise(resolve => setTimeout(resolve, 100));
        
      //   // Check if local description exists before sending
      // if (peerConnection.current.localDescription) {
      websocket.current.send(JSON.stringify({
          type: 'offer',
          offer: {
              sdp: offer.sdp,
              type: offer.type
          }
      }));
      console.log('Offer sent to server');
    } catch (error) {
      console.error('Error creating offer:', error);
    }
  };

  const handleSignalingData = async (data) => {
    switch (data.type) {
      case 'connected':
        console.log('Server confirmed connection: ', data.message);
        break;
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
        console.log('Successfully set remote description from server answer');
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
        console.log('Added ICE candidate from server');
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
    // Validate passcode (you'd typically do this with backend)
    if (passcode === '1234') {
      setCurrentPage('instructions');
      setupPeerConnection();
    } else {
      alert('Invalid Passcode');
    }
  };

  const handleStartQuiz = (questions) => {
    setCurrentPage('quiz');
    sendMessage('quiz_start');
  };

  const handleQuizComplete = () => {
    setCurrentPage('complete');
  };

  const handleReset = () => {
    setCurrentPage('login');
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
          question={currentQuestion}
          image={imageData}
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