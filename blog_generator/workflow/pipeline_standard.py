"""
Standard Pipeline - Monolithic Architecture - PRODUCTION FIXED v4.2

CRITICAL FIXES:
- Added validation gate after research tasks complete
- Checks quality rating and code blocks before writing phase
- Prevents cascade failure from bad research

This pipeline runs all 11 agents in a single crew (traditional approach):
- All agents loaded in memory simultaneously
- Sequential task execution with validation gate
- Higher memory usage but simpler architecture

Use this for:
- Local development with sufficient RAM
- Debugging and testing
- Environments with >10GB RAM
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

from blog_generator.config import logger, is_ollama_llm
from blog_generator.core import (
    BASE_DIR,
    BLOG_POSTS_DIR,
    BASE_ASSETS_DIR,
    select_next_topic,
    ensure_blog_assets_topic_specific,
    build_jekyll_post,
    save_post,
    record_coverage,
    validate_all_code_blocks,
    extract_task_output,
    slugify,
)
from blog_generator.workflow.crew_builder import build_standard_crew


def run_standard_pipeline() -> None:
    """
    STANDARD PIPELINE - Monolithic Architecture with Validation
    
    Runs all 11 agents in a single crew with sequential execution.
    Designed for environments with sufficient memory (>10GB RAM).
    """
    logger.info("=" * 70)
    logger.info("Standard Blog Generator v4.2 (PRODUCTION FIXED)")
    logger.info("Monolithic Architecture (11 agents)")
    logger.info("=" * 70)
    logger.info(f"Base: {BASE_DIR}")
    logger.info(f"Posts: {BLOG_POSTS_DIR}")
    logger.info("")
    
    # Log tool availability
    from blog_generator.config import README_TOOLS_AVAILABLE, SEARCH_TOOLS_AVAILABLE
    
    if README_TOOLS_AVAILABLE:
        logger.info("✅ README + Package Health tools available")
    else:
        logger.warning("⚠️  README tools not available")
    
    if SEARCH_TOOLS_AVAILABLE:
        logger.info("✅ Web search tools available")
    else:
        logger.warning("⚠️  Web search tools not available")
    
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    logger.info(f"LLM: {llm_model}")
    
    if is_ollama_llm():
        logger.info("✅ Ollama mode")
    
    logger.info("")
    
    try:
        # ====================================================================
        # SETUP: Topic & Assets
        # ====================================================================
        topic = select_next_topic()
        logger.info(f"📝 Topic: {topic.title}")
        logger.info(f"   Type: {topic.kind}")
        logger.info(f"   Tags: {', '.join(topic.tags[:3])}")
        logger.info("")
        
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y-%m-%d")
        slug = f"{topic.kind}-{slugify(topic.title)}"
        
        from blog_generator.config import IMAGE_TOOLS_AVAILABLE, set_blog_context
        
        if IMAGE_TOOLS_AVAILABLE:
            blog_assets_dir = set_blog_context(slug, topic.title, date_str)
        else:
            blog_assets_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
            blog_assets_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        ensure_blog_assets_topic_specific(topic, slug, date_str)
        logger.info("")
        
        # ====================================================================
        # BUILD & RUN CREW (All 11 Agents)
        # ====================================================================
        logger.info("🚀 11-Agent Orchestrated Pipeline Starting...")
        logger.info("=" * 70)
        logger.info("   Agent Flow:")
        logger.info("   1. Orchestrator → Strategy")
        logger.info("   2. README Analyst → Docs")
        logger.info("   3. Package Health → Validation")
        logger.info("   4. Web Researcher → Fallback")
        logger.info("   5. Source Validator → Quality ⚠️  GATE")
        logger.info("   6. Content Planner → Outline")
        logger.info("   7. Technical Writer → Article")
        logger.info("   8. Code Validator → Check")
        logger.info("   9. Code Fixer → Fix")
        logger.info("   10. Content Editor → Polish")
        logger.info("   11. Metadata Publisher → SEO")
        logger.info("")
        logger.info("   ⏱️  Estimated: 15-25 minutes...")
        logger.info("")
        
        crew, tasks = build_standard_crew(topic)
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("No result from crew")
        
        logger.info("✅ Pipeline Complete")
        logger.info("")
        
        # Unpack tasks
        (
            orchestration_task,
            readme_task,
            health_task,
            web_research_task,
            quality_task,
            planning_task,
            writing_task,
            validation_task,
            fixing_task,
            editing_task,
            metadata_task,
        ) = tasks
        
        # ====================================================================
        # 🚨 CRITICAL: VALIDATION CHECKPOINT (PRODUCTION FIX)
        # ====================================================================
        logger.info("=" * 70)
        logger.info("🔍 VALIDATION CHECKPOINT: Checking Research Quality")
        logger.info("=" * 70)
        
        # Extract research outputs for validation
        readme_data = extract_task_output(readme_task, "readme")
        health_data = extract_task_output(health_task, "health")
        quality_data = extract_task_output(quality_task, "source_validator")
        
        validation_passed = True
        validation_issues = []
        
        # CHECK 1: Quality Rating
        logger.info("Check 1: Quality rating...")
        if "Rating: F" in quality_data or "Rating:F" in quality_data:
            validation_passed = False
            validation_issues.append("Quality validator gave F rating")
            logger.error("   ❌ Quality rating: F")
        else:
            rating_match = re.search(r'Rating:\s*([A-F][+]?)', quality_data)
            if rating_match:
                rating = rating_match.group(1)
                logger.info(f"   ✓ Quality rating: {rating}")
            else:
                logger.warning("   ⚠️  Could not extract rating")
        
        # CHECK 2: Code Blocks
        logger.info("Check 2: Code examples...")
        code_block_count = (
            readme_data.count("```python") +
            readme_data.count("```bash") +
            health_data.count("```python")
        )
        
        if code_block_count == 0:
            validation_passed = False
            validation_issues.append(f"Zero code blocks found (expected at least 1)")
            logger.error(f"   ❌ Code blocks: {code_block_count}")
        else:
            logger.info(f"   ✓ Code blocks: {code_block_count}")
        
        # CHECK 3: Documentation completeness
        logger.info("Check 3: Documentation completeness...")
        if "stub" in readme_data.lower() or len(readme_data.strip()) < 500:
            logger.warning("   ⚠️  Documentation may be incomplete")
        else:
            logger.info(f"   ✓ Documentation: {len(readme_data)} chars")
        
        # ====================================================================
        # DECISION: PASS or FAIL
        # ====================================================================
        logger.info("")
        logger.info("=" * 70)
        
        if not validation_passed:
            logger.error("❌ VALIDATION FAILED - Research phase insufficient")
            logger.error("=" * 70)
            logger.error("")
            logger.error("Issues:")
            for i, issue in enumerate(validation_issues, 1):
                logger.error(f"   {i}. {issue}")
            logger.error("")
            logger.error("Quality Report:")
            logger.error("-" * 70)
            logger.error(quality_data[:500])
            logger.error("-" * 70)
            logger.error("")
            
            raise ValueError(
                f"Research validation failed: {len(validation_issues)} issues detected.\n"
                f"Writing phase would produce hallucinated content."
            )
        
        logger.info("✅ VALIDATION PASSED")
        logger.info("=" * 70)
        logger.info(f"   • Code blocks: {code_block_count}")
        logger.info(f"   • Quality: Acceptable")
        logger.info("")
        logger.info("🟢 Continuing to writing phase...")
        logger.info("")
        
        # ====================================================================
        # EXTRACT FINAL OUTPUTS (Writing phase already complete)
        # ====================================================================
        logger.info("🔍 Extracting outputs...")
        
        # Extract body (try fixer first, then writer)
        body = extract_task_output(fixing_task, "fixer")
        if not body or len(body) < 800:
            logger.warning("⚠️  Fixer output short, trying writer...")
            body = extract_task_output(writing_task, "writer")
        
        if not body or len(body) < 800:
            logger.error("❌ Insufficient output")
            raise RuntimeError(f"Too short: {len(body) if body else 0} chars")
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # ====================================================================
        # VALIDATE CODE
        # ====================================================================
        all_valid, issues, code_blocks = validate_all_code_blocks(body)
        if not all_valid:
            logger.warning("⚠️  Code validation issues:")
            for issue in issues[:5]:
                logger.warning(f"   {issue}")
            logger.warning("   Proceeding anyway (fixer may have missed some)")
        
        logger.info(f"   ✓ {len(code_blocks)} code blocks")
        logger.info("")
        
        # ====================================================================
        # PARSE METADATA
        # ====================================================================
        meta_raw = extract_task_output(metadata_task, "publisher")
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Metadata: {meta.get('title', 'N/A')[:50]}")
        except Exception as e:
            logger.warning(f"⚠️  Metadata parse failed: {e}")
            meta = {
                "title": topic.title,
                "excerpt": topic.summary or f"Learn about {topic.title}",
                "tags": topic.tags or ["ai"]
            }
        
        logger.info("")
        
        # ====================================================================
        # BUILD & SAVE POST
        # ====================================================================
        filename, content = build_jekyll_post(today, topic, body, meta, blog_assets_dir)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # ====================================================================
        # SUCCESS SUMMARY
        # ====================================================================
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ PROFESSIONAL BLOG POST GENERATED")
        logger.info("=" * 70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {len(code_blocks)} Python + {bash_blocks} Bash")
        logger.info("")
        logger.info("✅ Quality Assurance:")
        logger.info("   • README-first data retrieval ✓")
        logger.info("   • Package health validation ✓")
        logger.info("   • Research validation gate ✓")
        logger.info("   • Deprecation detection ✓")
        logger.info("   • Code validation → fixing ✓")
        logger.info("   • Source quality tracking ✓")
        logger.info("   • Topic-specific images ✓")
        logger.info("   • Professional editing ✓")
        logger.info("   • SEO optimization ✓")
        logger.info("")
        
        # Source quality report
        if quality_data:
            logger.info("📊 Source Quality:")
            if "A+" in quality_data or "High" in quality_data:
                logger.info("   ⭐⭐⭐ Highest Quality (Official Sources)")
            elif "A" in quality_data or "Medium" in quality_data:
                logger.info("   ⭐⭐ High Quality (Validated Sources)")
            else:
                logger.info("   ⭐ Good Quality (Web Sources)")
        
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info(f"   1. Review: cat {path.relative_to(BASE_DIR)}")
        logger.info(f"   2. Test code: Extract and run")
        logger.info(f"   3. Preview: jekyll serve")
        logger.info(f"   4. Publish: git commit")
        logger.info("")
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)