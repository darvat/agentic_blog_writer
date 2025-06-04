from __future__ import annotations
import json
from pathlib import Path
from typing import Any, TypeVar

from app.models.article_schemas import SectionPlans, ResearchNotes, SythesizedArticle, FinalArticle
from app.core.printer import Printer

T = TypeVar('T')


class WorkflowDataManager:
    """
    Handles data persistence and caching for the article creation workflow.
    """

    def __init__(self, data_dir: Path, printer: Printer):
        self.data_dir = data_dir
        self.printer = printer
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_data(self, title_slug: str, phase: str, data: dict | list | Any | None) -> None:
        """Save workflow data to disk with proper serialization"""
        if data is None:
            return
        
        phase_dir = self.data_dir / title_slug
        phase_dir.mkdir(parents=True, exist_ok=True)
        file_path = phase_dir / f"{phase}.json"
        
        with open(file_path, "w") as f:
            if hasattr(data, 'model_dump_json') and callable(data.model_dump_json):
                f.write(data.model_dump_json(indent=2))
            elif isinstance(data, (dict, list)):
                json.dump(data, f, indent=2)
            else:
                f.write(str(data))

    def load_data(self, title_slug: str, phase: str, output_model: type[T] | None = None) -> T | dict | list | None:
        """Load workflow data from disk with proper deserialization"""
        file_path = self.data_dir / title_slug / f"{phase}.json"
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, "r") as f:
                content = json.load(f)
                
                if output_model:
                    if hasattr(output_model, 'model_validate'):
                        return output_model.model_validate(content)
                    elif hasattr(output_model, 'parse_obj'):
                        return output_model.parse_obj(content)
                    else:
                        # Try direct instantiation as fallback
                        try:
                            return output_model(**content)  # type: ignore
                        except Exception:
                            # Log validation error and return None to trigger re-run
                            self.printer.update_item(
                                f"load_error_{phase}", 
                                f"⚠️ Cache validation failed for {phase} - will regenerate", 
                                is_done=True, 
                                hide_checkmark=True
                            )
                            return None
                else:
                    return content
                    
        except Exception:
            # Log loading error and return None to trigger re-run
            self.printer.update_item(
                f"load_error_{phase}", 
                f"⚠️ Cache loading failed for {phase} - will regenerate", 
                is_done=True, 
                hide_checkmark=True
            )
            return None

    def has_cached_data(self, title_slug: str, phase: str) -> bool:
        """Check if cached data exists for a given phase"""
        file_path = self.data_dir / title_slug / f"{phase}.json"
        return file_path.exists()

    def clear_cache(self, title_slug: str, phase: str | None = None) -> None:
        """Clear cached data for a specific phase or all phases"""
        phase_dir = self.data_dir / title_slug
        
        if not phase_dir.exists():
            return
            
        if phase:
            file_path = phase_dir / f"{phase}.json"
            if file_path.exists():
                file_path.unlink()
        else:
            # Clear all cached data for this query
            for file_path in phase_dir.glob("*.json"):
                file_path.unlink()
            if not any(phase_dir.iterdir()):
                phase_dir.rmdir() 