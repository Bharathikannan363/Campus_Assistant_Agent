"""Shared data models and structured schemas for AI Campus Assistant."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Source:
    """Citation metadata for web-derived or college content."""
    title: str
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "url": self.url}


@dataclass
class ToolResult:
    """Standardized result returned by agent tools."""
    success: bool
    data: Any = None
    sources: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "sources": self.sources,
            "error": self.error,
        }


@dataclass
class CampusLocation:
    id: Optional[int]
    name: str
    building: str
    floor: Optional[int] = None
    room: Optional[str] = None
    landmark: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimetableEntry:
    id: Optional[int]
    student_id: int
    course: str
    day: str
    time: str
    room: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoomBooking:
    id: Optional[int]
    booking_id: str
    student_id: int
    room_name: str
    booking_date: str
    start_time: str
    end_time: str
    purpose: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
