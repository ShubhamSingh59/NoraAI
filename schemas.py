"""Defining the format of webhook, response and the Lead"""

from pydantic import BaseModel, Field
from typing import List, Optional


# LeadState format which is the part of response
class LeadState(BaseModel):
    phone: Optional[str] = None
    budget_aed: Optional[int] = None
    property_type: Optional[str] = None
    location: Optional[str] = None
    timeline: Optional[str] = None
    purpose: Optional[str] = None
    qualification: str = Field(description="Must be 'hot', 'warm', or 'cold'")
    golden_visa_eligible: bool = False
    matched_property_ids: List[str]


# Agent response
class AgentResponse(BaseModel):
    reply: str
    language: str = Field(description="ISO language code, e.g., 'en', 'hi', 'ar'")
    lead: LeadState


# Message which is the part of the Webhook request
class Message(BaseModel):
    type: str
    text: str


# Webhook request
class WebhookRequest(BaseModel):
    client_id: str
    from_: str = Field(alias="from")  # Handle Python reserved word 'from'
    message: Message
    timestamp: str
