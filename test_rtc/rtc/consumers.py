"""
server_consumer.py
Django Channels + aiortc WebRTC quiz server.

- Accepts WebSocket connections from clients.
- Negotiates WebRTC video and data channels.
- Tracks hand gestures in the incoming video stream to run an interactive quiz.
"""

import argparse
import json
import logging
import os
import time
import csv
import cv2
import base64

from asyncio import ensure_future
from .HandTrackingModule import HandDetector # Custom CVZone module for hand detection
from channels.generic.websocket import AsyncWebsocketConsumer
from aiortc import (MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, 
                    RTCIceCandidate, RTCConfiguration, RTCIceServer, RTCIceGatherer,
                    RTCDataChannel)
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRelay
from av import VideoFrame
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)
relay = MediaRelay()


# ----------------------------
# Data class for each question and the answer it gets
# ----------------------------
class Data():
    def __init__(self, data):
        self.question_text = data["question_text"]
        self.question_image = data["question_image"]
        self.choice_type = data["choice_type"]
        self.answer = int(data["answer"])
        self.choice1 = data["choice1"]
        self.choice2 = data["choice2"]
        self.choice3 = data["choice3"]
        self.choice4 = data["choice4"]

        # Updated dynamically when user makes a selection
        self.chosen_answer = None

    def update(self, fingers):
        """
        Update chosen_answer based on finger pattern:
        - Recognizes specific hand/finger combinations to map to answers 1–4 or 'undo' (5).
        """
        if fingers == [0, 1, 0, 0, 0]:
            self.chosen_answer = 1
        elif fingers == [0, 1, 1, 0, 0]:
            self.chosen_answer = 2
        elif fingers == [0, 1, 1, 1, 0]:
            self.chosen_answer = 3
        elif fingers == [0, 1, 1, 1, 1]:
            self.chosen_answer = 4
        elif fingers == [1, 0, 0, 0, 0]:
            self.chosen_answer = 5
        else:
            self.chosen_answer = None


# ----------------------------
# Media track to process incoming video frames and detect gestures
# ----------------------------
class VideoTransformTrack(MediaStreamTrack):
    """
    A custom MediaStreamTrack from client,
    processing the frames and drives quiz progression.
    """
    kind = "video"

    def __init__(self, track, channel, exam_file):
        super().__init__()
        self.detector = HandDetector(maxHands=2) # CVZone hand detection utility
        self.track = track          # Original incoming webrtc track
        self.channel = channel      # Data channel for sending exam events and data to client
        self.frames = 0             # Frame counter
        self.data = []              # List of Data objects (exam questions)
        self.qNo = 0                # Current question index
        self.qTotal = 0             # Total number of questions
        self.score = 0              # Exam score
        
        # Timing and state flags for gesture detection and cooldown
        self.last_execution_time = time.time()  # Time last gesture validated
        self.detection_time = time.time()       # Time of gesture detected first (need to validate)
        self.hands_unseen = float()     # Total duration of time with hands visible != 2
        self.handsin = []               # Timestamps when valid number of hands detected
        self.handsout = []              # Timestamps when invalid number of hands detected
        self.cooldown_period = 1        # Delay before next gesture is accepted (determined)
        self.hands_seen = True          # Valid number of hands (state)
        self.on_cooldown = True
        self.detected_answer = None
        self.double_detection = False   # Is a gesture being validated now?
        self.only_show = True           # True = show video only (to client), no exam processing
        
        # Load quiz data from CSV file
        self.import_quiz_data(exam_file)

    async def recv(self):
        """
        Called for each incoming frame from the client.
        Processes every third frame to reduce load and
        optionally runs gesture detection.
        """
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Mirror effect for user convenience
        img = cv2.flip(img, 1)
        
        # Process every third frame for efficiency
        if self.frames % 3 == 0:
            hands, img= self.detector.findHands(img)
            if not self.only_show:
                await self.processing(hands, img)
            self.frames = 0
        self.frames += 1

        # Return the annotated frame to the client
        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame
    
    def import_quiz_data(self, quiz_name):
        """
        Load quiz questions from a CSV file and create Data objects.
        """
        with open(f'quiz/{quiz_name}', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
        for question in data:
            self.data.append(Data(question))
        self.qTotal = len(data)
    
    async def quiz_start(self):
        """
        Start the quiz: toggle processing and show the first and question page to client.
        """
        self.only_show = not self.only_show
        await self.show_question(self.qNo)
        
    async def show_question(self, qNo):
        """
        Send the current question (text + image) to the client over the webrtc data channel.
        """
        question = self.data[qNo]
        if question.question_image:
            image = cv2.imread(question.question_image)
            _, buffer = cv2.imencode('.png', image)
            b64_str = base64.b64encode(buffer).decode('utf-8')
        else:
            b64_str = None
        
        self.channel.send(json.dumps({"message": 'new_question',
                                     "qNo": f'Question {qNo + 1}',
                                     "question": question.question_text,
                                     "image": b64_str,
                                     "choice1": question.choice1,
                                     "choice2": question.choice2,
                                     "choice3": question.choice3,
                                     "choice4": question.choice4}))
    
    async def processing(self, hands, img):
        """
        Main quiz logic:
        - Detects finger gestures.
        - Validates finger gesture class.
        - Updates current question/answer.
        - Tracks hand visibility for cheating detection.
        - Sends exam progress or completion messages.
        """
        current_time = time.time()
        
        # Handle cooldown to avoid double-counting and accidental gestures
        if self.on_cooldown:
            if current_time - self.last_execution_time >= self.cooldown_period:
                self.on_cooldown = False
            
        elif self.qNo < self.qTotal:
            question = self.data[self.qNo]
            if len(hands) > 0:
                # Finger state (up/down) detection for the latest detected hand
                fingers = self.detector.tipsUp(hands[-1])
                question.update(fingers)
                answer = question.chosen_answer
                
                if answer:
                    # First detection of an answer gesture
                    if not self.double_detection:
                        self.detected_answer = answer
                        self.detection_time = current_time
                        self.double_detection = True
                    
                    # Require a second detection 1 second later for validation
                    elif current_time > self.detection_time + 1:
                        self.double_detection = False
                        if answer == self.detected_answer:
                            if answer == 5:
                                # Undo gesture: go back one question
                                self.data[self.qNo].chosen_answer = None
                                self.qNo = max(self.qNo - 1, 0)
                                self.data[self.qNo].chosen_answer = None
                            else:
                                # Advance to next question
                                self.qNo += 1
                            
                            # Quiz completion
                            if self.qNo == self.qTotal:
                                # Calculate final score
                                self.score = sum(
                                    1 for data in self.data if data.answer == data.chosen_answer
                                )
                                self.score = round((self.score / self.qTotal) * 100, 2)
                                
                                # Update unseen-hand duration
                                if self.hands_seen is False:
                                    self.handsin.append(current_time)
                                    self.hands_seen = True
                                print(self.handsin)
                                print(self.handsout)
                                for i in range(len(self.handsin)):
                                    self.hands_unseen -= self.handsout[i]
                                    self.hands_unseen += self.handsin[i]
                                
                                # Signal client of completion
                                self.channel.send(json.dumps({
                                    "message": 'quiz_finished',
                                    "score": self.score,
                                    "hands_unseen": self.hands_unseen}))
                            else:
                                # Show next question
                                await self.show_question(self.qNo)
                            
                            # Reset cooldown after valid gesture
                            self.on_cooldown = True
                            self.last_execution_time = current_time
                else:
                    self.detected_answer = None
            else:
                self.detected_answer = None
            
            # Track and signal client when number of hands (2) are not valid (possible cheating)
            if len(hands) != 2:
                if self.hands_seen is True:
                    self.channel.send(json.dumps({
                                    "message": 'hand_unseen',
                                    "text": 'Show both hands!',
                                    "color": 'yellow'}))
                    self.handsout.append(current_time)
                    self.hands_seen = False
            else:
                if self.hands_seen is False:
                    self.channel.send(json.dumps({
                                    "message": 'hand_seen',
                                    "text": 'Hands detected',
                                    "color": '#49ff34'}))
                    self.handsin.append(current_time)
                    self.hands_seen = True

# ----------------------------
# WebSocket Consumer: handles signaling and WebRTC setup
# ----------------------------
class ServerConsumer(AsyncWebsocketConsumer):
    """
    Django Channels WebSocket consumer for WebRTC signaling.
    - Handles SDP offer/answer exchange.
    - Sets up RTCPeerConnection with video stream and data channels.
    - Adds the VideoTransformTrack for gesture/quiz processing.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pc = None              # RTCPeerConnection instance
        self.channel = None         # RTCDataChannel to client
        self.video_track = None     # VideoTransformTrack instance
        self.ice_gatherer = None    # For gathering ICE candidates
        self.ice_servers = [        # STUN/TURN servers
            RTCIceServer("stun:stun.l.google.com:19302"),
            RTCIceServer("stun:stun1.l.google.com:19302"),
            RTCIceServer("turn:relay1.expressturn.com:3478", "ef4D0W10T15FXPIADE", "q5aQSKhZ2swakoCM")
        ]
        
        
    async def connect(self):
        """
        Called when a WebSocket connection is opened.
        Initializes RTCPeerConnection and event handlers.
        """
        from .models import Users, Exams
        self.users = Users
        self.exams = Exams
        self.exam_file = 'Electrical.csv'
        await self.accept()
        
        self.pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=self.ice_servers))
        
        self.channel = self.pc.createDataChannel('message')
        
        # Handle incoming media tracks from client
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Track received from client: {track.kind}")
            if track.kind == "video":
                # Wrap incoming video track for processing
                self.video_track = VideoTransformTrack(relay.subscribe(track), self.channel, self.exam_file)
                self.pc.addTrack(self.video_track)

            @track.on("ended")
            async def on_ended():
                logger.info(f"Track: {track.kind} ended")
        
        # Handle incoming data channel from client
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            ensure_future(self.on_datachannel(channel))
        
        # Connection state changes for debugging/logging
        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(f"Connection state: {self.pc.connectionState}")
            
        @self.pc.on("iceconnectionstatechange")
        def on_ice_connection_state_change():
            print(f"ICE connection state changed: {self.pc.iceConnectionState}")
    
    async def disconnect(self):
        """Clean up on WebSocket disconnect."""
        logger.info(f"WebSocket disconnected for client")
        if self.pc:
            await self.pc.close()
    
    async def receive(self, text_data):
        """
        Handle signaling messages from the client:
        - SDP offers
        - Remote ICE candidates
        """
        data = json.loads(text_data)
        
        if data['type'] == 'offer':
            # Set remote description and create/send answer
            offer = RTCSessionDescription(
                sdp=data["offer"]["sdp"],
                type=data["offer"]["type"]
            )
            await self.pc.setRemoteDescription(offer)
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            await self.send(text_data=json.dumps({
                "type": "answer",
                "answer": {
                    "sdp": answer.sdp, #localdesc
                    "type": answer.type #localdesc
                }
            }))
            
            # Gather and send local ICE candidates
            self.ice_gatherer = RTCIceGatherer(iceServers=self.ice_servers)
            await self.ice_gatherer.gather()
            candidates = self.ice_gatherer.getLocalCandidates()
            
            if candidates:
                for candidate in candidates:
                    logger.info(f"SENT: {candidate}")
                    await self.send(text_data=json.dumps({
                        "type": "ice_candidate",
                        "candidate": {
                            "component": candidate.component,
                            "foundation": candidate.foundation,
                            "ip": candidate.ip,
                            "port": candidate.port,
                            "priority": candidate.priority,
                            "protocol": candidate.protocol,
                            "type": candidate.type,
                            "sdpMid": 0,
                            "sdpMLineIndex": 0,
                        }
                    }))
            
        elif data['type'] == 'ice_candidate':
            # Add ICE candidate sent from the client
            logger.info(f"CAND: {data['candidate']}")
            candidate = self.parse_ice_candidate(data['candidate'])
            await self.pc.addIceCandidate(candidate)
        
        elif data['type'] == 'login':
            try:
                username = data['username']
                password = data['password']
                logger.info(f"LOGIN: {username + password}")
                
                if not username or not password:
                    await self.send_error("Username and password are required.")
                    validity = '0'
                else:
                    exam_file_path = await self.authenticate_and_get_exam(username, password)
                    
                if exam_file_path:
                    self.exam_file = exam_file_path
                    validity = '1'
                else:
                    validity = '0'
                await self.send(text_data=json.dumps({
                    'type': 'login',
                    'valid': validity
                }))

            except json.JSONDecodeError:
                await self.send_error("Invalid JSON format.")

            
    @database_sync_to_async
    def authenticate_and_get_exam(self, username, password):
        """
        Synchronous database logic wrapped for async usage.
        1. Finds the user.
        2. Checks the password.
        3. Fetches the corresponding exam file.
        Returns the exam file string on success, or None on failure.
        """
        try:
            user = self.users.objects.get(Username=username)
            if user.Password == password:
                try:
                    exam = self.exams.objects.get(ExamId=user.UserExamId)
                    return exam.ExamFile
                except self.exams.DoesNotExist:
                    return None
            else:
                return None

        except self.users.DoesNotExist:
            return None
            
    def parse_ice_candidate(self, candidate_obj):
        """
        Parse ICE candidate information from client
        into an RTCIceCandidate object usable by aiortc.
        """
        if 'candidate' in candidate_obj:
            candidate_str = candidate_obj['candidate']
            if len(candidate_str) == 0:
                return None
            
            # Remove 'candidate:' prefix if present
            if candidate_str.startswith('candidate:'):
                candidate_str = candidate_str[len('candidate:'):]

            parts = candidate_str.split()

            return RTCIceCandidate(
                foundation=parts[0],
                component=int(parts[1]),
                protocol=parts[2],
                priority=int(parts[3]),
                ip=parts[4],
                port=int(parts[5]),
                type=parts[7],
                sdpMid=candidate_obj['sdpMid'],
                sdpMLineIndex=candidate_obj['sdpMLineIndex']
            )
        
        # Fallback if candidate is already structured
        return RTCIceCandidate(
            foundation=candidate_obj['foundation'],
            component=int(candidate_obj['component']),
            protocol=candidate_obj['protocol'],
            priority=int(candidate_obj['priority']),
            ip=candidate_obj['address'],
            port=int(candidate_obj['port']),
            type=candidate_obj['type'],
            sdpMid=candidate_obj['sdpMid'],
            sdpMLineIndex=candidate_obj['sdpMLineIndex']
        )
            
    async def on_datachannel(self, channel: RTCDataChannel):
        """
        Handle messages from the client's data channel.
        Currently supports starting the quiz.
        """
        @channel.on("message")
        async def on_message(message):
            if message == "quiz_start":
                await self.video_track.quiz_start()