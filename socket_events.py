from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from app import socketio
from models import Call
import logging

@socketio.on('join_call')
def on_join_call(data):
    if not current_user.is_authenticated:
        disconnect()
        return
    
    try:
        call_id = data.get('call_id')
        if not call_id:
            return
        
        # Verify user has access to this call
        call = Call.query.get(call_id)
        if not call or (call.caller_id != current_user.id and call.recipient_id != current_user.id):
            disconnect()
            return
        
        join_room(f"call_{call_id}")
        emit('user_joined', {'user_id': current_user.id}, to=f"call_{call_id}")
    except Exception as e:
        logging.error(f"Error in join_call: {e}")
        disconnect()

@socketio.on('leave_call')
def on_leave_call(data):
    call_id = data['call_id']
    leave_room(f"call_{call_id}")
    emit('user_left', {'user_id': current_user.id}, to=f"call_{call_id}")

@socketio.on('webrtc_offer')
def on_webrtc_offer(data):
    if not current_user.is_authenticated:
        disconnect()
        return
    
    call_id = data.get('call_id')
    offer = data.get('offer')
    
    if call_id and offer:
        emit('webrtc_offer', {
            'call_id': call_id,
            'offer': offer,
            'sender_id': current_user.id
        }, to=f"call_{call_id}", include_self=False)

@socketio.on('webrtc_answer')
def on_webrtc_answer(data):
    if not current_user.is_authenticated:
        disconnect()
        return
    
    call_id = data.get('call_id')
    answer = data.get('answer')
    
    if call_id and answer:
        emit('webrtc_answer', {
            'call_id': call_id,
            'answer': answer,
            'sender_id': current_user.id
        }, to=f"call_{call_id}", include_self=False)

@socketio.on('webrtc_ice_candidate')
def on_webrtc_ice_candidate(data):
    if not current_user.is_authenticated:
        disconnect()
        return
    
    call_id = data.get('call_id')
    candidate = data.get('candidate')
    
    if call_id and candidate:
        emit('webrtc_ice_candidate', {
            'call_id': call_id,
            'candidate': candidate,
            'sender_id': current_user.id
        }, to=f"call_{call_id}", include_self=False)

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")
        emit('connected', {'user_id': current_user.id})

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        emit('disconnected', {'user_id': current_user.id})
