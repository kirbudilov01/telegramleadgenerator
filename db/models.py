from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, ForeignKey, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.session import Base
from datetime import datetime


class Account(Base):
    """Telegram account metadata"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    phone_number = Column(String, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_synced = Column(DateTime, nullable=True)
    
    chats = relationship("Chat", back_populates="account")
    messages = relationship("Message", back_populates="account")


class Contact(Base):
    """Telegram contacts (people in personal chats)"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_bot = Column(Boolean, default=False)
    is_self = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Chat(Base):
    """Personal dialogs (1-on-1 conversations)"""
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)  # Telegram chat ID
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    contact_username = Column(String, nullable=True)
    is_user = Column(Boolean, default=True)  # True for private chats, False for saved messages
    last_message_id = Column(BigInteger, nullable=True)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    account = relationship("Account", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('account_id', 'chat_id'),
    )


class Message(Base):
    """Telegram messages from personal chats"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)  # Telegram message ID
    sender_id = Column(BigInteger, nullable=False)  # Who sent the message
    text = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    
    # Media metadata (only metadata, not the files themselves)
    has_media = Column(Boolean, default=False)
    media_type = Column(String, nullable=True)  # 'photo', 'document', 'audio', 'video', etc.
    media_file_id = Column(String, nullable=True)  # Telegram file_id for reference
    media_size = Column(Integer, nullable=True)  # File size in bytes
    media_local_path = Column(String, nullable=True)  # Local path if file was downloaded
    
    # Message attributes
    is_edited = Column(Boolean, default=False)
    is_forwarded = Column(Boolean, default=False)
    reply_to_msg_id = Column(BigInteger, nullable=True)  # If it's a reply
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    account = relationship("Account", back_populates="messages")
    chat = relationship("Chat", back_populates="messages")
    
    __table_args__ = (
        UniqueConstraint('account_id', 'chat_id', 'message_id'),
    )
