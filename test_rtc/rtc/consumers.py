import argparse
import json
import logging
import os
import time
import csv

import cv2
from asyncio import ensure_future
from HandTrackingModule import HandDetector
from channels.generic.websocket import AsyncWebsocketConsumer
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, RTCConfiguration, RTCIceServer, RTCIceGatherer, RTCDataChannel
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRelay
from av import VideoFrame

logger = logging.getLogger(__name__)
relay = MediaRelay()

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

        self.chosen_answer = None

    def update(self, fingers):
        if fingers == [0, 1, 0, 0, 0]:  # Jika 1 jari diangkat
            self.chosen_answer = 1
        elif fingers == [0, 1, 1, 0, 0]:  # Jika 2 jari diangkat
            self.chosen_answer = 2
        elif fingers == [0, 1, 1, 1, 0]:  # Jika 3 jari diangkat
            self.chosen_answer = 3
        elif fingers == [0, 1, 1, 1, 1]:  # Jika 4 jari diangkat
            self.chosen_answer = 4
        else:  # Jika 5 jari diangkat
            self.chosen_answer = None


class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, channel):
        super().__init__()  # don't forget this!
        self.detector = HandDetector(maxHands=1)
        self.track = track
        self.channel = channel
        self.process = False
        self.frames = 0
        self.data = []
        self.qNo = 0
        self.qTotal = 0
        self.score = 0
        
        self.last_execution_time = time.time()
        self.detection_time = time.time()
        self.hands_unseen = float()
        self.cooldown_period = 1
        self.hands_seen = True
        self.on_cooldown = True
        self.detected_answer = None
        self.double_detection = False
        self.only_show = True
        
        self.import_quiz_data("ELEKTRO")

    async def recv(self):
        print('recv')
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        img = cv2.flip(img, 1)
        
        if self.frames % 3 == 0:
            hands, img= self.detector.findHands(img)
            logger.info(f"only_show: {self.only_show}")
            if self.only_show is False:
                await self.processing(hands, img)
        self.frames += 1

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame
    
    def import_quiz_data(self, quiz_name):
        with open(f'quiz/{quiz_name}.csv', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
        for question in data:
            self.data.append(Data(question))
        self.qTotal = len(data)
    
    async def quiz_start(self):
        self.only_show = not self.only_show
        await self.show_question(self.data[self.qNo])
        
    async def show_question(self, question):
        self.channel.send(json.dumps({"question": question.question_text,
                                     "image": question.question_image,
                                     "choice1": question.choice1,
                                     "choice2": question.choice2,
                                     "choice3": question.choice3,
                                     "choice4": question.choice4}))
    
    async def processing(self, hands, img):
        print('processing frame')
        current_time = time.time()
        if self.on_cooldown:
            if current_time - self.last_execution_time >= self.cooldown_period:
                self.on_cooldown = False
            
        elif self.qNo < self.qTotal:
            question = self.data[self.qNo]
            if len(hands) > 0:
                fingers = self.detector.tipsUp(hands[-1])
                question.update(fingers)
                answer = question.chosen_answer
                
                if answer:
                    if not self.double_detection:
                        self.detected_answer = answer
                        self.detection_time = current_time
                        self.double_detection = True
                    
                    elif current_time > self.detection_time + 1:
                        self.double_detection = False
                        if answer == self.detected_answer:
                            self.qNo += 1
                            print(self.qNo, self.qTotal)
                            if self.qNo != self.qTotal:
                                print('next question')
                                await self.show_question(self.data[self.qNo])
                            self.on_cooldown = True
                            self.last_execution_time = current_time
                else:
                    self.detected_answer = None
            else:
                self.detected_answer = None
                    
            if len(hands) < 2:
                if self.hands_seen is True:
                    self.hands_unseen -= current_time
                    print(self.hands_unseen)
                    self.hands_seen = False
            else:
                if self.hands_seen is False:
                    self.hands_unseen += current_time
                    self.hands_seen = True
        
        self.process = False

class ServerConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pc = None
        self.channel = None
        self.video_track = None
        self.ice_gatherer = None
        self.candidate_received = False
        self.ice_servers = [
            RTCIceServer("stun:stun.l.google.com:19302"),
            RTCIceServer("stun:stun1.l.google.com:19302")
        ]
        
    async def connect(self):
        logger.info("WebSocket connect attempt received")
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Websocket accepted, connected to server",
            }))
        
        self.pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=self.ice_servers))
        
        self.channel = self.pc.createDataChannel('message')
        
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Track received from client: {track.kind}")
            if track.kind == "video":
                self.video_track = VideoTransformTrack(relay.subscribe(track), self.channel)
                self.pc.addTrack(self.video_track)
                logger.info(f"ADDTRACK DONE")

            @track.on("ended")
            async def on_ended():
                logger.info(f"Track: {track.kind} ended")
                
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            ensure_future(self.on_datachannel(channel))
            
        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(f"Connection state: {self.pc.connectionState}")
            
        @self.pc.on("iceconnectionstatechange")
        def on_ice_connection_state_change():
            print(f"ICE connection state changed: {self.pc.iceConnectionState}")
        
        logger.info(f"WebRTC Server's Peer Connection created")
    
    async def disconnect(self):
        logger.info(f"WebSocket disconnected for client")
        if self.pc:
            await self.pc.close()
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data['type'] == 'offer':
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
            logger.info(f"Answer Sent to Client")
            
            self.ice_gatherer = RTCIceGatherer(iceServers=self.ice_servers)
            await self.ice_gatherer.gather()
            candidates = self.ice_gatherer.getLocalCandidates()
            logger.info(f"GATHERED:  {candidates}")
            
            if candidates:
                for candidate in candidates:
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
            candidate = data.get('candidate')
            ice_candidate = RTCIceCandidate(
                candidate['component'],
                candidate['foundation'],
                candidate['address'],
                candidate['port'],
                candidate['priority'],
                candidate['protocol'],
                candidate['type'],
                sdpMid=candidate['sdpMid'],
                sdpMLineIndex=candidate['sdpMLineIndex']
            )
            await self.pc.addIceCandidate(ice_candidate)
            self.candidate_received = True
            logger.info("added ice candidate")
            
    async def on_datachannel(self, channel: RTCDataChannel):
        logger.info(f"DataChannel {channel.label} is open")

        @channel.on("message")
        async def on_message(message):
            if message == "quiz_start":
                await self.video_track.quiz_start()