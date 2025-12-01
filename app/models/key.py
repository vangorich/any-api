from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

import tiktoken
from sqlalchemy import UniqueConstraint
from typing import List, Dict, Any

# --- Tokenizer Utility ---
#
# Consider moving this to a separate utility file if it grows.
# For now, keeping it here for simplicity.

_cached_encoders = {}

def get_tokenizer(model_name: str = "gpt-3.5-turbo"):
    """
    Returns a tiktoken encoder for the given model name.
    Caches encoders to avoid re-initializing them.
    """
    if model_name not in _cached_encoders:
        try:
            _cached_encoders[model_name] = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback for models not explicitly supported by tiktoken
            _cached_encoders[model_name] = tiktoken.get_encoding("cl100k_base")
    return _cached_encoders[model_name]

def count_tokens_for_messages(messages: List[Dict[str, Any]], model_name: str = "gpt-3.5-turbo") -> int:
    """
    Calculates the number of tokens for a list of messages based on OpenAI's format.
    """
    tokenizer = get_tokenizer(model_name)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            if value:
                num_tokens += len(tokenizer.encode(str(value)))
            if key == "name":
                num_tokens -= 1  # if there's a name, the role is omitted
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens

# --- Models ---

class OfficialKey(Base):
    __tablename__ = "official_keys"
    __table_args__ = (
        UniqueConstraint('key', 'user_id', 'channel_id', name='_user_channel_key_uc'),
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    usage_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    last_status = Column(String, default="active")
    last_status_code = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    channel = relationship("Channel")

class ExclusiveKey(Base):
    __tablename__ = "exclusive_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False) # gapi-...
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    enable_regex = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    preset = relationship("Preset")
    channel = relationship("Channel")
