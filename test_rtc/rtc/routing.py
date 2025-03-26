from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/rtc/', consumers.ServerConsumer.as_asgi()),
]