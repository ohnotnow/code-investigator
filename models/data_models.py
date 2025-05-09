"""
This module contains data models used across the application.
"""

from pydantic import BaseModel
from typing import List, Optional


class FileSummary(BaseModel):
    """Model for file summary information."""
    files: List[str]
    implementation_summary: str


class ProjectType(BaseModel):
    """Model for project type information."""
    language: str
    framework: Optional[str] = None
