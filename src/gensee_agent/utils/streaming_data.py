import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from pydantic import field_validator
import shortuuid

STREAMING_MESSAGE_TYPES = Literal["status", "assistant", "error", "document", "internal", "user", "metadata"]

class QuestionData(BaseModel):
    id: Optional[str]
    question: str
    options: list[str]
    multiple_choice: bool

class StreamingUserInteraction(BaseModel):
    type: Literal["user_interaction", "user_notification"]
    questions: list[QuestionData]
    buttons: list[str]
    interaction_id: str
    cls_info: Literal["StreamingUserInteraction"] = Field(frozen=True, default="StreamingUserInteraction")

class DocumentAction(BaseModel):
    type: Literal["update_doc"]
    pad_id: Optional[str] = None  # ID of the pad on etherpad
    doc_id: Optional[str] = None  # ID of the document, e.g., "research_report".  Originally called target.
    title: Optional[str] = None
    cls_info: Literal["DocumentAction"] = Field(frozen=True, default="DocumentAction")

class InternalAction(BaseModel):
    type: Literal["hand_over", "append_context"]
    target_agent: str  # e.g., "short_answer_agent", "deep_research_agent"
    params: dict[str, Any] = {}
    cls_info: Literal["InternalAction"] = Field(frozen=True, default="InternalAction")

class StreamingMessage(BaseModel):
    type: STREAMING_MESSAGE_TYPES  # User is used for user messages logged in the session
    delta: str | dict
    datatype: Literal["str", "json"] = "str"
    obj_type: Optional[str] = None  # obj_data can be not None only with "metadata" type.
    action: Optional[StreamingUserInteraction | DocumentAction | InternalAction] = None

    @field_validator('action')
    @classmethod
    def validate_action(cls, v, info):
        if v is not None and info.data.get('type') not in ['assistant', 'document', 'internal']:
            raise ValueError('action can only have values when type is "assistant", "document", or "internal"')
        return v

    # @field_validator('obj_type')
    # @classmethod
    # def validate_obj_type(cls, v, info):
    #     if v is not None and info.data.get('type') not in ['metadata', 'assistant']:
    #         raise ValueError('obj_type can only have a value when type is "metadata"')
    #     return v

def new_conversation() -> str:
    return f"conv.{shortuuid.uuid()}"

class StreamingData(BaseModel):
    type: Literal["start", "delta", "end"]
    session_id: str  # Matches the session_id in the request
    conversation_id: str  # If response belongs to the same conversation (e.g., word tokens), they will share the same conversation_id
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
    message: Optional[StreamingMessage] = None

    @field_validator('message')
    @classmethod
    def validate_message(cls, v, info):
        if v is not None and info.data.get('type') in ['start', 'end']:
            raise ValueError('message must be None when type is "start" or "end"')
        return v

    def to_streaming_output(self) -> str:
        return f"data: {self.model_dump_json(indent=None)}\n\n"

    @classmethod
    def from_streaming_output(cls, data: str) -> "StreamingData":
        if data.startswith("data: "):
            json_str = data[len("data: "):].strip()
            return cls.model_validate_json(json_str)
        else:
            raise ValueError("Invalid streaming output format.")

    @classmethod
    def start(cls, session_id: str, conversation_id: Optional[str] = None) -> "StreamingData":
        if conversation_id is None:
            conversation_id = new_conversation()
        return cls(type="start", session_id=session_id, conversation_id=conversation_id)

    @classmethod
    def end(cls, session_id: str, conversation_id: Optional[str] = None) -> "StreamingData":
        if conversation_id is None:
            conversation_id = new_conversation()
        return cls(type="end", session_id=session_id, conversation_id=conversation_id)

    @classmethod
    def _simple_message(cls, session_id: str, conversation_id: Optional[str], message: str | dict, message_type: STREAMING_MESSAGE_TYPES,
                        obj_type: Optional[str], *, action: Optional[StreamingUserInteraction] = None) -> "StreamingData":
        if conversation_id is None:
            conversation_id = new_conversation()
        if isinstance(message, str):
            return cls(
                type="delta", session_id=session_id, conversation_id=conversation_id,
                message=StreamingMessage(type=message_type, delta=message, datatype="str", obj_type=obj_type, action=action)
            )
        elif isinstance(message, dict):
            return cls(
                type="delta", session_id=session_id, conversation_id=conversation_id,
                message=StreamingMessage(type=message_type, delta=message, datatype="json", obj_type=obj_type, action=action)
            )
        else:
            raise ValueError("Message must be either str or dict.")

    @classmethod
    def status(cls, session_id: str, message: str | dict, conversation_id: Optional[str] = None, obj_type: Optional[str] = None) -> "StreamingData":
        return cls._simple_message(session_id, conversation_id, message, "status", obj_type)

    @classmethod
    def assistant(cls, session_id: str, message: str | dict, conversation_id: Optional[str] = None, obj_type: Optional[str] = None, *, action: Optional[StreamingUserInteraction] = None) -> "StreamingData":
        return cls._simple_message(session_id, conversation_id, message, "assistant", obj_type, action=action)

    @classmethod
    def error(cls, session_id: str, message: str, conversation_id: Optional[str] = None, obj_type: Optional[str] = None) -> "StreamingData":
        return cls._simple_message(session_id, conversation_id, message, "error", obj_type)
    @classmethod
    def document(cls, session_id: str, document_change: str, *, conversation_id: Optional[str] = None, action: Optional[DocumentAction] = None) -> "StreamingData":
        # If document is empty, it means to force an update on the document.
        if conversation_id is None:
            conversation_id = new_conversation()
        return cls(
            type="delta", session_id=session_id, conversation_id=conversation_id, message=StreamingMessage(type="document", delta=document_change, datatype="str", action=action))

    @classmethod
    def user(cls, session_id: str, message: str, conversation_id: Optional[str] = None, obj_type: Optional[str] = None) -> "StreamingData":
        return cls._simple_message(session_id, conversation_id, message, "user", obj_type)

    @classmethod
    def internal(cls, session_id: str, *, conversation_id: Optional[str] = None, action: Optional[InternalAction] = None) -> "StreamingData":
        if conversation_id is None:
            conversation_id = new_conversation()
        return cls(
            type="delta", session_id=session_id, conversation_id=conversation_id, message=StreamingMessage(type="internal", delta="", datatype="str", action=action))

    @classmethod
    def metadata(cls, session_id: str, metadata: dict, conversation_id: Optional[str] = None, obj_type: Optional[str] = None) -> "StreamingData":
        return cls._simple_message(session_id, conversation_id, metadata, "metadata", obj_type)

    # @classmethod
    # def delta_assistant(cls, session_id: str, message: str, action: dict, *, target: Optional[str] = None) -> str:
    #     delta_dict = {
    #         "type": "assistant",
    #         "delta": message,
    #         "action": action
    #     }
    #     if target is not None:
    #         delta_dict["target"] = target
    #     return cls._generate("delta", session_id, delta_dict)

    # @classmethod
    # def action_update_document(cls, pad_id: str) -> dict:
    #     return {"type": "update_document", "pad_id": pad_id}