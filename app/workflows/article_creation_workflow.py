from __future__ import annotations
import asyncio


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

    def __init__(self) -> None:
        self.printer = Printer(console)

    async def run(self, query: str) -> None:
        trace_id = gen_trace_id()
        with trace("Article Creation Workflow Trace", trace_id=trace_id):
            # self.printer.update_item(
            #     "trace_id",
            #     f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}",
            #     is_done=True,
            #     hide_checkmark=True,
            # )
            # self.printer.update_item("start", f"Starting article creation for query: {query}", is_done=True)

            # Step 1: Plan the article sections and brief
            section_plans = await self._plan_article(query)

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
                
            self.printer.update_item("final_output", "Article plan and research complete.", is_done=True)
            self.printer.end()



    async def _plan_article(self, query: str) -> SectionPlans | None:
        self.printer.update_item("planning", "Planning article structure and brief...")
        try:
            # The planner_agent now takes the raw query.
            # Its output_type is SectionPlans, which includes the ArticleBrief.
            result = await Runner.run(planner_agent, query)
            section_plans_output = result.final_output_as(SectionPlans)
            self.printer.update_item(
                "planning",
                f"Planning complete. Generated {len(section_plans_output.section_plans)} sections.",
                is_done=True,
            )
            return section_plans_output
        except Exception as e:
            self.printer.update_item("planning", f"Error during planning: {e}", is_done=True)
            # Consider how to handle errors - raise, return None, or a default error object
            return None

    async def _research_sections(self, section_plans: SectionPlans | None) -> ResearchNotes | None:
        if not section_plans:
            self.printer.update_item("researching", "Skipping research due to no section plan.", is_done=True)
            return None

        self.printer.update_item("researching", f"Starting research for {len(section_plans.section_plans)} sections...")
        try:
            # The research_agent expects SectionPlans as input.
            # Its output_type is ResearchNotes.
            # The research agent internally handles iterating through sections and queries.
            result = await Runner.run(research_agent, section_plans.model_dump_json()) # Pass the SectionPlans object as a string
            research_notes_output = result.final_output_as(ResearchNotes)
            self.printer.update_item(
                "researching",
                f"Research complete. Found notes for {len(research_notes_output.notes_by_section)} sections.",
                is_done=True,
            )
            return research_notes_output
        except Exception as e:
            self.printer.update_item("researching", f"Error during research: {e}", is_done=True)
            return None
        
if __name__ == "__main__":
    workflow = ArticleCreationWorkflow()
    asyncio.run(workflow.run("Write an article about the latest trends in AI"))