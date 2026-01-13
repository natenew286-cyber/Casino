import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name')
        if not self.room_name:
            # Default to 'lobby' if no room name, or handle appropriately
            self.room_name = 'lobby'
            
        self.room_group_name = f'game_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        action = text_data_json.get('action')

        if action == 'create_room':
            # Logic to create room (could be handled via API too)
            pass
        elif action == 'join_room':
            # Logic to join room
            pass
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_message',
                'message': message,
                'sender': self.channel_name
            }
        )

    # Receive message from room group
    async def game_message(self, event):
        message = event['message']
        sender = event.get('sender')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender
        }))
