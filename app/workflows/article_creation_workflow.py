from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from slugify import slugify
import re


from agents import Runner, gen_trace_id, trace
from app.agents.planner_agent import agent as planner_agent
from app.agents.research_agent import agent as research_agent
from app.agents.section_synthesizer_agent import agent as section_synthesizer_agent
from app.agents.article_synthesizer_agent import agent as article_synthesizer_agent
from app.models.article_schemas import SectionPlans, ResearchNotes, SythesizedArticle, SythesizedSection, SectionPlanWithResearch, FinalArticle
from app.core.printer import Printer
from app.core.console_config import console
from crawl4ai import AsyncWebCrawler
from crawl4ai import CrawlResult


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

            print("\n\n=====INITIAL RESEARCH NOTES=====\n\n")
            if research_notes:
                for section_note in research_notes.notes_by_section:
                    print(f"Section ID: {section_note.section_id}")
                    print(f"  Summary: {section_note.summary}")
                    for finding in section_note.findings:
                        print(f"    - Snippet: {finding.snippet[:100]}... (Source: {finding.source_url})") # Truncate snippet
            else:
                print("No initial research notes generated.")
                # self.printer.end() # If no research notes, subsequent steps might be skipped.
                # return # Decided to let it flow, _scrape_web_content handles None input.
                
            # Step 3: Scrape web content and integrate into research notes
            final_research_notes = await self._scrape_web_content(research_notes)

            print("\n\n=====AUGMENTED RESEARCH NOTES (WITH SCRAPED CONTENT)=====\n\n")
            if final_research_notes:
                for section_note in final_research_notes.notes_by_section:
                    print(f"Section ID: {section_note.section_id}")
                    print(f"  Summary: {section_note.summary}")
                    for finding in section_note.findings:
                        print(f"    - Snippet: {finding.snippet[:60]}... (Source: {finding.source_url})")
                        if finding.scraped_content:
                            print(f"      Scraped Content: {finding.scraped_content[:100]}...")
                        else:
                            print(f"      Scraped Content: Not available or not scraped.")
            # Print summary per section: sectionid - Sum(urls_scraped)
            print("\n\n=====SUMMARY: URLS SCRAPED PER SECTION=====\n")
            if final_research_notes:
                for section_note in final_research_notes.notes_by_section:
                    urls_scraped = sum(1 for finding in section_note.findings if finding.scraped_content)
                    print(f"Section {section_note.section_id} - {urls_scraped} URL(s) scraped")

            else:
                # This case covers if research_notes was None, or _scrape_web_content returned None
                print("No augmented research notes available (scraping might have been skipped, failed, or no initial notes).")

            # Step 4: Synthesize sections
            synthesized_article = await self._synthesize_sections(section_plans, final_research_notes)

            print("\n\n=====SYNTHESIZED ARTICLE=====\n\n")
            if synthesized_article:
                for section in synthesized_article.sections:
                    print(f"Section ID: {section.section_id}")
                    print(f"Title: {section.title}")
                    print(f"Content: {section.content[:200]}...") # Truncate content for display
                if synthesized_article.full_text_for_editing:
                    print("\nFull text for editing available.")
            else:
                print("Article synthesis failed or was skipped.")

            # Step 5: Create final article
            final_article = await self._create_final_article(synthesized_article, final_research_notes)

            print("\n\n=====FINAL ARTICLE=====\n\n")
            if final_article:
                print(f"Title: {final_article.title}")
                print(f"Meta Description: {final_article.meta_description}")
                print(f"Meta Keywords: {final_article.meta_keywords}")
                print(f"TL;DR: {final_article.tldr}")
                if final_article.table_of_contents:
                    print(f"Table of Contents: {final_article.table_of_contents}")
                print(f"Article Body: {final_article.article_body[:300]}...") # Truncate for display
                if final_article.conclusion:
                    print(f"Conclusion: {final_article.conclusion[:200]}...")
                if final_article.references:
                    print(f"References: {len(final_article.references)} reference(s)")
            else:
                print("Final article creation failed or was skipped.")

            self.printer.update_item("final_output", "Complete article creation workflow finished.", is_done=True)
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

    async def _scrape_web_content(self, original_research_notes: ResearchNotes | None) -> ResearchNotes | None:
        phase_name = "scrape_web_content"

        if not original_research_notes:
            self.printer.update_item(phase_name, "Skipping web content integration due to no initial research notes.", is_done=True, hide_checkmark=True)
            return None

        loaded_data = self._load_data(self.query_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "Loaded existing research notes with scraped content.", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "Starting web scraping and integration into research notes...")

        urls_to_scrape = set()
        if original_research_notes.notes_by_section:
            for section_note in original_research_notes.notes_by_section:
                for finding in section_note.findings:
                    if finding.source_url:
                        urls_to_scrape.add(finding.source_url)
        
        if not urls_to_scrape:
            self.printer.update_item(phase_name, "No URLs found in research notes to scrape. Saving original notes as augmented.", is_done=True)
            self._save_data(self.query_slug, phase_name, original_research_notes)
            return original_research_notes
        
        unique_urls_list = list(urls_to_scrape)
        self.printer.update_item(f"{phase_name}_progress", f"Identified {len(unique_urls_list)} unique URLs for scraping.", hide_checkmark=True)

        # Deep copy the original notes to avoid modifying them directly if they were from a cache,
        # until the augmented version is successfully created and saved.
        notes_to_augment = original_research_notes.model_copy(deep=True)

        scraped_content_map = {}
        try:
            async with AsyncWebCrawler() as crawler:
                crawl_results: list[CrawlResult] = await crawler.arun_many(urls=unique_urls_list)
            
            successful_scrapes = 0
            for result in crawl_results:
                if result.success and result.markdown:
                    content = result.markdown.fit_markdown if result.markdown.fit_markdown else result.markdown.raw_markdown
                    if content: # Ensure content is not empty
                        # Remove markdown image links: ![alt text](url)
                        content_no_images = re.sub(r"!\[.*?\]\(.*?\)", "", content)
                        # Remove HTML img tags: <img src="..." alt="...">
                        content_no_images = re.sub(r"<img .*?>", "", content_no_images)
                        # Remove HTTP links within parentheses: (http*) -> ()
                        content_no_images = re.sub(r"\(http[^)]*\)", "()", content_no_images)
                        # Remove empty markdown links: [   ]()
                        content_no_images = re.sub(r"\[\s*\]\(\)", "", content_no_images)
                        # Replace multiple newlines with single newline
                        content_no_images = re.sub(r"\n{2,}", "\n", content_no_images)
                        scraped_content_map[result.url] = content_no_images
                        successful_scrapes += 1
                else:
                    self.printer.update_item(f"scrape_url_fail_{slugify(result.url)}", f"Failed to scrape {result.url}: {result.error_message or 'No markdown content'}", is_done=True, hide_checkmark=True)
            
            self.printer.update_item(f"{phase_name}_progress", f"Scraping complete. Successfully scraped {successful_scrapes}/{len(unique_urls_list)} URLs. Integrating content...", hide_checkmark=True)

            updated_findings_count = 0
            if notes_to_augment.notes_by_section:
                for section_note in notes_to_augment.notes_by_section:
                    for finding in section_note.findings:
                        if finding.source_url and finding.source_url in scraped_content_map:
                            finding.scraped_content = scraped_content_map[finding.source_url]
                            updated_findings_count +=1
            
            self._save_data(self.query_slug, phase_name, notes_to_augment)
            self.printer.update_item(
                phase_name,
                f"Web scraping and integration complete. Updated {updated_findings_count} findings with scraped content.",
                is_done=True,
            )
            return notes_to_augment
        except Exception as e:
            self.printer.update_item(phase_name, f"Error during web scraping/integration: {e}", is_done=True)
            # Return the original notes if augmentation fails, so the workflow can potentially continue.
            return original_research_notes
        
    async def _synthesize_sections(
        self, 
        section_plans: SectionPlans | None, 
        research_notes: ResearchNotes | None
    ) -> SythesizedArticle | None:
        phase_name = "synthesize_sections"

        if not section_plans or not research_notes:
            self.printer.update_item(phase_name, "Skipping section synthesis due to missing plans or research notes.", is_done=True, hide_checkmark=True)
            return None

        loaded_data = self._load_data(self.query_slug, phase_name, SythesizedArticle)
        if loaded_data:
            self.printer.update_item(phase_name, "Loaded existing synthesized article.", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, f"Starting synthesis for {len(section_plans.section_plans)} sections...")

        # Prepare inputs for each section synthesis task
        synthesis_tasks = []
        research_notes_map = {note.section_id: note for note in research_notes.notes_by_section}

        for plan in section_plans.section_plans:
            section_id_str = str(plan.section_id) # Ensure section_id is string for map lookup
            if section_id_str in research_notes_map:
                section_specific_research = research_notes_map[section_id_str]
                
                # Create the combined input model for the agent
                agent_input = SectionPlanWithResearch(
                    section_plan=plan,
                    research_notes=section_specific_research
                )
                # Note: The section_synthesizer_agent.py expects a SythesizedArticle as output_type.
                # This might need adjustment if we want individual SythesizedSection from each agent run.
                # For now, we assume the agent is structured to take SectionPlanWithResearch and internally handles
                # the synthesis for that section, and the Runner will somehow give us back a SythesizedSection.
                # This is a potential mismatch to address if errors occur.
                # A more robust approach would be for the agent to output SythesizedSection, and we collect them.
                synthesis_tasks.append(
                    Runner.run(section_synthesizer_agent, agent_input.model_dump_json())
                )
            else:
                self.printer.update_item(f"{phase_name}_skip_section_{plan.section_id}", f"Skipping synthesis for section {plan.section_id} due to missing research notes.", is_done=True, hide_checkmark=True)

        if not synthesis_tasks:
            self.printer.update_item(phase_name, "No sections to synthesize.", is_done=True)
            return None

        try:
            self.printer.update_item(f"{phase_name}_progress", f"Running {len(synthesis_tasks)} synthesis tasks in parallel...", hide_checkmark=True)
            # Run all synthesis tasks concurrently
            results = await asyncio.gather(*synthesis_tasks)
            
            synthesized_sections: list[SythesizedSection] = []
            failed_syntheses = 0

            for i, result in enumerate(results):
                # Assuming the result.final_output_as(SythesizedSection) is the correct way to get the section
                # This depends on how the section_synthesizer_agent is truly structured and what Runner.run returns.
                # If section_synthesizer_agent returns SythesizedArticle, this will need adjustment.
                # For now, let's assume it returns a SythesizedSection or can be adapted to.
                # The original agent definition had output_type=SythesizedArticle.
                # Let's try to get SythesizedSection from the result.
                try:
                    # This is an assumption. The agent is defined to output SythesizedArticle.
                    # If it's called per section, it should logically output SythesizedSection.
                    # We will need to adjust the section_synthesizer_agent.py
                    section_output = result.final_output_as(SythesizedSection)
                    synthesized_sections.append(section_output)
                except Exception as e:
                    failed_syntheses += 1
                    # Find corresponding plan to log which section failed
                    original_plan = section_plans.section_plans[i] # This assumes order is maintained
                    self.printer.update_item(f"{phase_name}_section_fail_{original_plan.section_id}", f"Failed to synthesize section {original_plan.section_id}: {e}", is_done=True)


            if failed_syntheses > 0:
                 self.printer.update_item(f"{phase_name}_failures", f"{failed_syntheses} section(s) failed to synthesize.", is_done=True, hide_checkmark=True)
            
            if not synthesized_sections:
                self.printer.update_item(phase_name, "No sections were successfully synthesized.", is_done=True)
                return None

            # Create the final SythesizedArticle object
            final_article = SythesizedArticle(sections=synthesized_sections)
            # Optionally, generate a full text version for editing
            final_article.full_text_for_editing = "\n\n---\n\n".join(
                f"{s.content}" for s in synthesized_sections
            )

            self._save_data(self.query_slug, phase_name, final_article)
            self.printer.update_item(
                phase_name,
                f"Section synthesis complete. Successfully synthesized {len(synthesized_sections)} sections.",
                is_done=True,
            )
            return final_article

        except Exception as e:
            self.printer.update_item(phase_name, f"Error during section synthesis: {e}", is_done=True)
            return None

    async def _create_final_article(self, synthesized_article: SythesizedArticle | None, final_research_notes: ResearchNotes | None) -> FinalArticle | None:
        phase_name = "final_article_creation"

        if not synthesized_article or not synthesized_article.full_text_for_editing:
            self.printer.update_item(phase_name, "Skipping final article creation due to missing synthesized article or full text content.", is_done=True, hide_checkmark=True)
            return None

        loaded_data = self._load_data(self.query_slug, phase_name, FinalArticle)
        if loaded_data:
            self.printer.update_item(phase_name, "Loaded existing final article.", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "Starting final article creation and optimization...")
        
        # Extract source URLs from research notes if available
        source_urls = set()
        if final_research_notes and final_research_notes.notes_by_section:
            for section_note in final_research_notes.notes_by_section:
                for finding in section_note.findings:
                    if finding.source_url:
                        source_urls.add(finding.source_url)
        
        if not source_urls:
            self.printer.update_item(f"{phase_name}_sources", "No source URLs found in research notes.", is_done=True, hide_checkmark=True)
        else:
            self.printer.update_item(f"{phase_name}_sources", f"Found {len(source_urls)} unique source URLs as references.", is_done=True, hide_checkmark=True)

        try:
            # Prepare combined input for the agent including both content and research sources
            agent_input = {
                "synthesized_content": synthesized_article.full_text_for_editing,
                "source_urls": list(source_urls)
            }
            
            # Use the article_synthesizer_agent to create the final article
            result = await Runner.run(
                article_synthesizer_agent, 
                json.dumps(agent_input, indent=2)
            )
            final_article_output = result.final_output_as(FinalArticle)
            
            self._save_data(self.query_slug, phase_name, final_article_output)
            self.printer.update_item(
                phase_name,
                f"Final article creation complete. Created SEO-optimized article with all metadata and references.",
                is_done=True,
            )
            return final_article_output

        except Exception as e:
            self.printer.update_item(phase_name, f"Error during final article creation: {e}", is_done=True)
            return None

if __name__ == "__main__":
    workflow = ArticleCreationWorkflow("Write an article about the latest trends in AI")
    asyncio.run(workflow.run())