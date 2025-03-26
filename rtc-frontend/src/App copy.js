import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [localStream, setLocalStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [connectionState, setConnectionState] = useState('disconnected');
  const inputVideoRef = useRef(null);
  const outputVideoRef = useRef(null);

  const peerConnection = useRef(null);
  const websocket = useRef(null);
  const connectionInitiated = useRef(false);
  let component_int = useRef(1);

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
      setConnectionState('socket_connected');
      setupPeerConnection();
      return () => {
        if (websocket.current) {
          websocket.current.close();
        }
      };
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleSignalingData(data);
    };
    
    socket.onclose = () => {
      console.log('WebSocket connection closed');
      setConnectionState('disconnected');
      connectionInitiated.current = false;
    };

    // return () => {
    //   if (websocket.current) {
    //     websocket.current.close();
    //   }
    // };
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
      
      await navigator.mediaDevices.getUserMedia({ video: true, audio: false }).then((stream) => {
        document.getElementById('input-video').srcObject = stream;
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


      pc.addEventListener('track', (evt) => {
        document.getElementById('output-video').srcObject = evt.streams[0];
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
        setConnectionState(pc.iceConnectionState);
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

  return (
    <div className="video-container">
      <div className="video-frames">
        <div className="video-frame">
          <h3>Camera Input</h3>
          <video 
            id="input-video"
            autoPlay
            playsInline
          />
        </div>
        
        <div className="video-frame">
          <h3>Processed Output</h3>
          <video 
            id="output-video"
            autoPlay 
            playsInline
          />
        </div>
      </div>
      
      <button 
        className="start-button" 
        onClick={setupPeerConnection}
      >
        Start
      </button>
    </div>
  );
}

export default App;
