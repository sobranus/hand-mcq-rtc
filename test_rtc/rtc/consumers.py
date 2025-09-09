import argparse
import json
import logging
import os
import time
import csv
import cv2
import base64

from asyncio import ensure_future
from HandTrackingModule import HandDetector
from channels.generic.websocket import AsyncWebsocketConsumer
from aiortc import (MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, 
                    RTCIceCandidate, RTCConfiguration, RTCIceServer, RTCIceGatherer,
                    RTCDataChannel)
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


class VideoTransformTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, track, channel):
        super().__init__()
        self.detector = HandDetector(maxHands=2)
        self.track = track
        self.channel = channel
        self.frames = 0
        self.data = []
        self.qNo = 0
        self.qTotal = 0
        self.score = 0
        
        self.last_execution_time = time.time()
        self.detection_time = time.time()
        self.hands_unseen = float()
        self.handsin = []
        self.handsout = []
        self.cooldown_period = 1
        self.hands_seen = True
        self.on_cooldown = True
        self.detected_answer = None
        self.double_detection = False
        self.only_show = True
        
        self.import_quiz_data("ELEKTRO")

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        img = cv2.flip(img, 1)
        
        if self.frames % 3 == 0:
            hands, img= self.detector.findHands(img)
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
        await self.show_question(self.qNo)
        
    async def show_question(self, qNo):
        question = self.data[qNo]
        image = cv2.imread(question.question_image)
        _, buffer = cv2.imencode('.png', image)
        b64_str = base64.b64encode(buffer).decode('utf-8')
        
        self.channel.send(json.dumps({"message": 'new_question',
                                     "qNo": f'Question No. {qNo + 1}',
                                     "question": question.question_text,
                                     "image": b64_str,
                                     "choice1": question.choice1,
                                     "choice2": question.choice2,
                                     "choice3": question.choice3,
                                     "choice4": question.choice4}))
    
    async def processing(self, hands, img):
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
                            if answer == 5:
                                self.data[self.qNo].chosen_answer = None
                                self.qNo = max(self.qNo - 1, 0)
                                self.data[self.qNo].chosen_answer = None
                            else:
                                self.qNo += 1
                                
                            if self.qNo == self.qTotal:
                                self.score = sum(1 for data in self.data if data.answer == data.chosen_answer)
                                self.score = round((self.score / self.qTotal) * 100, 2)
                                if self.hands_seen is False:
                                    self.handsin.append(current_time)
                                    self.hands_seen = True
                                print(self.handsin)
                                print(self.handsout)
                                for i in range(len(self.handsin)):
                                    self.hands_unseen -= self.handsout[i]
                                    self.hands_unseen += self.handsin[i]
                                self.channel.send(json.dumps({
                                    "message": 'quiz_finished',
                                    "score": self.score,
                                    "hands_unseen": self.hands_unseen}))
                            else:
                                await self.show_question(self.qNo)
                            self.on_cooldown = True
                            self.last_execution_time = current_time
                else:
                    self.detected_answer = None
            else:
                self.detected_answer = None
                    
            if len(hands) < 2:
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

class ServerConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pc = None
        self.channel = None
        self.video_track = None
        self.ice_gatherer = None
        self.ice_servers = [
            RTCIceServer("stun:stun.l.google.com:19302"),
            RTCIceServer("stun:stun1.l.google.com:19302"),
            RTCIceServer("turn:relay1.expressturn.com:3478", "ef4D0W10T15FXPIADE", "q5aQSKhZ2swakoCM")
        ]
        
        
    async def connect(self):
        await self.accept()
        
        self.pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=self.ice_servers))
        
        self.channel = self.pc.createDataChannel('message')
        
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Track received from client: {track.kind}")
            if track.kind == "video":
                self.video_track = VideoTransformTrack(relay.subscribe(track), self.channel)
                self.pc.addTrack(self.video_track)

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
            logger.info(f"CAND: {data['candidate']}")
            candidate = self.parse_ice_candidate(data['candidate'])
            await self.pc.addIceCandidate(candidate)
            
    def parse_ice_candidate(self, candidate_obj):
        if 'candidate' in candidate_obj:
            candidate_str = candidate_obj['candidate']
            if len(candidate_str) == 0:
                return None
            
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
        @channel.on("message")
        async def on_message(message):
            if message == "quiz_start":
                await self.video_track.quiz_start()