from dataclasses import dataclass
from typing import Optional

@dataclass
class ArticleCreationWorkflowConfig:
    query: str
    article_layout: Optional[str] = None