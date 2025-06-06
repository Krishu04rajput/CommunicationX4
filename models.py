from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, Index, text

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    username = db.Column(db.String(64), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='online')  # online, away, busy, invisible
    location = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    owned_servers = db.relationship('Server', backref='owner', lazy=True)
    messages = db.relationship('Message', backref='author', lazy=True)
    direct_messages_sent = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    direct_messages_received = db.relationship('DirectMessage', foreign_keys='DirectMessage.recipient_id', backref='recipient', lazy=True)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String, nullable=True)
    owner_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=True)  # Public servers auto-add all users
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    channels = db.relationship('Channel', backref='server', lazy=True, cascade='all, delete-orphan')
    memberships = db.relationship('ServerMembership', backref='server', lazy=True, cascade='all, delete-orphan')

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    messages = db.relationship('Message', backref='channel', lazy=True, cascade='all, delete-orphan')

class ServerMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='server_memberships')

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.BigInteger, primary_key=True)  # BigInt for large-scale storage
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True, nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    is_pinned = db.Column(db.Boolean, default=False, index=True)  # Index for pinned message queries
    reply_to_id = db.Column(db.BigInteger, nullable=True, index=True)  # Remove FK constraint for partitioning
    message_type = db.Column(db.String(20), default='text', index=True)  # Index for message type filtering
    audio_url = db.Column(db.String, nullable=True)  # For audio messages
    file_data = db.Column(db.LargeBinary, nullable=True)  # For file attachments
    
    # Relationships (without FK constraint for reply_to due to partitioning)
    reactions = db.relationship('MessageReaction', backref='message', cascade='all, delete-orphan')
    reports = db.relationship('MessageReport', backref='message', cascade='all, delete-orphan')
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_channel_created_at', 'channel_id', 'created_at'),  # For chronological message retrieval
        Index('idx_author_created_at', 'author_id', 'created_at'),    # For user message history
        Index('idx_channel_type_created', 'channel_id', 'message_type', 'created_at'),  # For filtered message queries
        Index('idx_pinned_channel', 'is_pinned', 'channel_id'),       # For pinned messages
        Index('idx_reply_lookup', 'reply_to_id', 'created_at'),       # For reply lookups
    )

class DirectMessage(db.Model):
    __tablename__ = 'direct_messages'
    
    id = db.Column(db.BigInteger, primary_key=True)  # BigInt for large-scale storage
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Composite indexes for efficient DM queries
    __table_args__ = (
        Index('idx_dm_conversation', 'sender_id', 'recipient_id', 'created_at'),  # For conversation threads
        Index('idx_dm_recipient_unread', 'recipient_id', 'read_at', 'created_at'),  # For unread messages
        Index('idx_dm_user_timeline', 'sender_id', 'created_at'),  # For user message timeline
    )

class Call(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caller_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)  # For server calls
    call_type = db.Column(db.String(10), nullable=False)  # 'audio' or 'video'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'ended', 'declined'
    started_at = db.Column(db.DateTime, default=datetime.now)
    ended_at = db.Column(db.DateTime, nullable=True)
    voicemail_url = db.Column(db.String, nullable=True)  # For voicemail recordings
    
    # Relationships
    caller = db.relationship('User', foreign_keys=[caller_id], backref='calls_made')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='calls_received')
    server = db.relationship('Server', backref='server_calls')

class CallMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('call.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    call = db.relationship('Call', backref='call_messages')
    user = db.relationship('User', backref='call_messages')

class SharedFile(db.Model):
    __tablename__ = 'shared_files'
    
    id = db.Column(db.BigInteger, primary_key=True)  # BigInt for large-scale storage
    filename = db.Column(db.String(255), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=True)  # Store large files externally for 1TB+ support
    file_path = db.Column(db.String(500), nullable=True)  # External file storage path
    file_size = db.Column(db.BigInteger, nullable=False, index=True)  # BigInt for large files
    mime_type = db.Column(db.String(100), nullable=False, index=True)
    uploader_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    is_compressed = db.Column(db.Boolean, default=False)  # Track compression status
    checksum = db.Column(db.String(64), nullable=True)  # File integrity verification
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_files')
    server = db.relationship('Server', backref='shared_files')
    channel = db.relationship('Channel', backref='shared_files')
    
    # Indexes for efficient file queries
    __table_args__ = (
        Index('idx_file_type_size', 'mime_type', 'file_size'),  # For file type and size filtering
        Index('idx_server_files', 'server_id', 'created_at'),  # For server file listings
        Index('idx_channel_files', 'channel_id', 'created_at'),  # For channel file listings
        Index('idx_user_uploads', 'uploader_id', 'created_at'),  # For user upload history
    )

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    inviter_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    uses_left = db.Column(db.Integer, default=1)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    inviter = db.relationship('User', backref='invitations_sent')

class Voicemail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    audio_url = db.Column(db.String, nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # in seconds
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='voicemails_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='voicemails_received')

class MessageReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.BigInteger, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='reactions')
    
    # Unique constraint to prevent duplicate reactions
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_message_user_emoji'),)

class MessageReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.BigInteger, db.ForeignKey('messages.id'), nullable=False)
    reporter_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    reporter = db.relationship('User', backref='message_reports')
