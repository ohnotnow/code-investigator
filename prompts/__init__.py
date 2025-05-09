"""
This module contains the prompt templates for all agents.
"""

from prompts.doc_agent_prompt import DOCS_PROMPT
from prompts.code_agent_prompt import CODE_PROMPT
from prompts.mermaid_agent_prompt import MERMAID_PROMPT
from prompts.testing_agent_prompt import TESTING_PROMPT

__all__ = ['DOCS_PROMPT', 'CODE_PROMPT', 'MERMAID_PROMPT', 'TESTING_PROMPT']
