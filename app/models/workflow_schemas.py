from dataclasses import dataclass
from typing import Optional

@dataclass
class ArticleCreationWorkflowConfig:
    title: str
    description: str
    wordcount: int
    article_layout: Optional[str] = None