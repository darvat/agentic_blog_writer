from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from slugify import slugify


from agents import Runner, gen_trace_id, trace
from app.agents.planner_agent import agent as planner_agent
from app.agents.research_agent import agent as research_agent
from app.models.article_schemas import SectionPlans, ResearchNotes
from app.core.printer import Printer
from app.core.console_config import console


class ArticleCreationWorkflow:
    """
    Orchestrates the article creation flow: planning and researching.
    """
    DATA_DIR = Path("data")

    def __init__(self, query: str) -> None:
        self.query = query
        self.query_slug = self._get_query_slug(self.query)
        self.printer = Printer(console)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _get_query_slug(self, query: str) -> str:
        return slugify(query)

    def _save_data(self, query_slug: str, phase: str, data: dict | list | None) -> None:
        if data is None:
            return
        phase_dir = self.DATA_DIR / query_slug
        phase_dir.mkdir(parents=True, exist_ok=True)
        file_path = phase_dir / f"{phase}.json"
        with open(file_path, "w") as f:
            if hasattr(data, 'model_dump_json') and callable(data.model_dump_json):
                f.write(data.model_dump_json(indent=2))
            elif isinstance(data, (dict, list)):
                 json.dump(data, f, indent=2)
            else:
                f.write(str(data))
        self.printer.update_item(f"save_{phase}", f"Saved {phase} data to {file_path}", is_done=True, hide_checkmark=True)


    def _load_data(self, query_slug: str, phase: str, output_model: type = None) -> SectionPlans | ResearchNotes | dict | list | None:
        file_path = self.DATA_DIR / query_slug / f"{phase}.json"
        if file_path.exists():
            with open(file_path, "r") as f:
                try:
                    content = json.load(f)
                    if output_model:
                        if hasattr(output_model, 'model_validate'):
                            loaded_data = output_model.model_validate(content)
                        elif hasattr(output_model, 'parse_obj'):
                            loaded_data = output_model.parse_obj(content)
                        else:
                            self.printer.update_item(f"load_{phase}", f"Warning: output_model for {phase} does not have a known Pydantic validation method (model_validate or parse_obj). Trying direct instantiation.", is_done=True, hide_checkmark=True)
                            try:
                                loaded_data = output_model(**content) # type: ignore
                            except Exception as val_err:
                                self.printer.update_item(f"load_{phase}", f"Error instantiating {output_model.__name__} for {phase} data from {file_path}: {val_err}. Will re-run phase.", is_done=True, hide_checkmark=True)
                                return None 
                    else:
                        loaded_data = content
                    self.printer.update_item(f"load_{phase}", f"Loaded {phase} data from {file_path}", is_done=True, hide_checkmark=True)
                    return loaded_data
                except Exception as e:
                    self.printer.update_item(f"load_{phase}", f"Error loading/validating {phase} data from {file_path}: {e}. Will re-run phase.", is_done=True, hide_checkmark=True)
                    return None
        return None

    async def run(self) -> None:
        trace_id = gen_trace_id()
        with trace("Article Creation Workflow Trace", trace_id=trace_id):
            # self.printer.update_item(
            #     "trace_id",
            #     f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}",
            #     is_done=True,
            #     hide_checkmark=True,
            # )
            # self.printer.update_item("start", f"Starting article creation for query: {self.query}", is_done=True)

            # Step 1: Plan the article sections and brief
            section_plans = await self._plan_article()

            # Print to stdout
            print("\n\n=====ARTICLE PLAN=====\n\n")
            # Assuming SectionPlans has a nice string representation or we print fields
            if section_plans:
                print(f"Article Topic: {section_plans.article_brief.topic}")
                print(f"Target Audience: {section_plans.article_brief.target_audience}")
                print(f"Keywords: {section_plans.article_brief.keywords}")
                print("\nSections:")
                for plan in section_plans.section_plans:
                    print(f"  ID: {plan.section_id}, Title: {plan.title}")
                    print(f"    Key Points: {plan.key_points}")
                    if plan.research_queries:
                        print(f"    Research Queries: {plan.research_queries}")
            else:
                print("No section plans generated.")
                self.printer.end()
                return
                
            # Step 2: Perform research based on the plan
            research_notes = await self._research_sections(section_plans)

            print("\n\n=====RESEARCH NOTES=====\n\n")
            if research_notes:
                for section_note in research_notes.notes_by_section:
                    print(f"Section ID: {section_note.section_id}")
                    print(f"  Summary: {section_note.summary}")
                    for finding in section_note.findings:
                        print(f"    - Snippet: {finding.snippet[:100]}... (Source: {finding.source_url})") # Truncate snippet
                if research_notes.general_findings:
                    print("\nGeneral Findings:")
                    for finding in research_notes.general_findings:
                        print(f"    - Snippet: {finding.snippet[:100]}... (Source: {finding.source_url})")
            else:
                print("No research notes generated.")
                self.printer.end()
                return
                
            self.printer.update_item("final_output", "Article plan and research complete.", is_done=True)
            self.printer.end()



    async def _plan_article(self) -> SectionPlans | None:
        phase_name = "planning"
        loaded_data = self._load_data(self.query_slug, phase_name, SectionPlans)
        if loaded_data:
            self.printer.update_item(phase_name, "Loaded existing article plan.", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "Planning article structure and brief...")
        try:
            # The planner_agent now takes the raw query.
            # Its output_type is SectionPlans, which includes the ArticleBrief.
            result = await Runner.run(planner_agent, self.query)
            section_plans_output = result.final_output_as(SectionPlans)
            self._save_data(self.query_slug, phase_name, section_plans_output)
            self.printer.update_item(
                phase_name,
                f"Planning complete. Generated {len(section_plans_output.section_plans)} sections.",
                is_done=True,
            )
            return section_plans_output
        except Exception as e:
            self.printer.update_item(phase_name, f"Error during planning: {e}", is_done=True)
            # Consider how to handle errors - raise, return None, or a default error object
            return None

    async def _research_sections(self, section_plans: SectionPlans | None) -> ResearchNotes | None:
        phase_name = "researching"
        if not section_plans:
            self.printer.update_item(phase_name, "Skipping research due to no section plan.", is_done=True)
            return None

        loaded_data = self._load_data(self.query_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "Loaded existing research notes.", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, f"Starting research for {len(section_plans.section_plans)} sections...")
        try:
            # The research_agent expects SectionPlans as input.
            # Its output_type is ResearchNotes.
            # The research agent internally handles iterating through sections and queries.
            result = await Runner.run(research_agent, section_plans.model_dump_json(), max_turns=100) # Pass the SectionPlans object as a string
            research_notes_output = result.final_output_as(ResearchNotes)
            self._save_data(self.query_slug, phase_name, research_notes_output)
            self.printer.update_item(
                phase_name,
                f"Research complete. Found notes for {len(research_notes_output.notes_by_section)} sections.",
                is_done=True,
            )
            return research_notes_output
        except Exception as e:
            self.printer.update_item(phase_name, f"Error during research: {e}", is_done=True)
            return None
        
if __name__ == "__main__":
    workflow = ArticleCreationWorkflow("Write an article about the latest trends in AI")
    asyncio.run(workflow.run())