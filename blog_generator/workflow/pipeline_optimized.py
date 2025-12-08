"""
Memory-Optimized Pipeline - Split-Crew Architecture - PRODUCTION v4.4.1

CRITICAL CHANGES v4.4.1:
✅ ALWAYS PUBLISH MODE - Never aborts, only warns
✅ Quality scoring system (A/B/C/D/F) with metadata
✅ Quality warnings passed to Phase 2 writers
✅ Low-quality disclaimer added to posts automatically
✅ Enhanced debugging for data loss detection

PREVIOUS FIXES:
- v4.3.1: Automatic web search fallback when README insufficient
- v4.2: Validation gate between phases

This pipeline splits the 11-agent workflow into two phases:
- Phase 1: Research (Agents 1-5) → Extract context string
- VALIDATION GATE: Check research quality (ALWAYS CONTINUES with warnings)
- Memory Cleanup: Garbage collection
- Phase 2: Writing (Agents 6-11) → Use context string + quality metadata

Memory savings: ~40% reduction in peak RAM usage
Quality assurance: Always publishes with appropriate warnings
"""
import gc
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any

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
from blog_generator.workflow.crew_builder import (
    build_research_crew_optimized,
    build_writing_crew_optimized,
    cleanup_phase_memory,
)


def calculate_quality_score(
    total_code_blocks: int,
    readme_length: int,
    web_length: int,
    has_version: bool,
    validator_rating: str,
    validator_abort: bool
) -> Tuple[str, List[str], List[str]]:
    """
    Calculate quality score and generate warnings/issues
    
    Returns:
        Tuple of (quality_score, critical_issues, warnings)
    """
    critical_issues = []
    warnings = []
    
    # Score calculation logic
    if total_code_blocks == 0:
        quality_score = "F"
        critical_issues.append("⚠️ CRITICAL: Zero code examples found in all sources")
    elif total_code_blocks < 2:
        quality_score = "D"
        warnings.append(f"Only {total_code_blocks} code example found - limited practical value")
    elif total_code_blocks < 3:
        quality_score = "C"
        warnings.append(f"Limited code examples ({total_code_blocks}) - may lack depth")
    elif total_code_blocks < 5:
        quality_score = "B"
        warnings.append(f"Moderate code examples ({total_code_blocks}) - acceptable quality")
    else:
        quality_score = "A"
    
    # Documentation checks
    total_content = readme_length + web_length
    if total_content < 500:
        critical_issues.append("Very limited documentation (<500 chars)")
        if quality_score not in ["F"]:
            quality_score = "D"
    elif total_content < 1000:
        warnings.append(f"Limited documentation ({total_content} chars)")
        if quality_score == "A":
            quality_score = "B"
    
    # Version check
    if not has_version:
        warnings.append("Version information missing or unclear")
        if quality_score == "A":
            quality_score = "B"
    
    # Validator override (only if suggests abort)
    if validator_abort and quality_score not in ["F", "D"]:
        warnings.append("Quality validator suggested concerns")
        if quality_score == "A":
            quality_score = "B"
    
    return quality_score, critical_issues, warnings


def generate_quality_disclaimer(quality_score: str, issues: List[str], warnings: List[str]) -> str:
    """
    Generate disclaimer text based on quality score
    """
    if quality_score in ["A", "B"]:
        return ""  # No disclaimer needed
    
    disclaimer_map = {
        "F": """
> **⚠️ QUALITY NOTICE**: This post was generated with **very limited source material**.
> Code examples may be synthesized or incomplete. Please verify all code before use.
> Consider consulting the [official documentation](official_docs_link_here) for production use.
""",
        "D": """
> **⚠️ QUALITY NOTICE**: This post was generated with **limited code examples** from source material.
> Some examples may be simplified or conceptual. Verify code before production use.
""",
        "C": """
> **📝 Note**: This post includes examples from multiple sources. Some code examples may need adaptation for your specific use case.
"""
    }
    
    return disclaimer_map.get(quality_score, "")


def run_optimized_pipeline() -> None:
    """
    MEMORY-OPTIMIZED PIPELINE - Split-Crew Architecture
    
    v4.4.1: ALWAYS PUBLISHES with quality warnings
    Designed for GitHub workflows with 7GB RAM limit
    """
    logger.info("=" * 70)
    logger.info("Memory-Optimized Blog Generator v4.4.1 (ALWAYS PUBLISH MODE)")
    logger.info("Split-Crew Architecture (5+6 agents)")
    logger.info("=" * 70)
    logger.info(f"Base: {BASE_DIR}")
    logger.info(f"Posts: {BLOG_POSTS_DIR}")
    logger.info("")
    
    # Log tool availability
    from blog_generator.config import (
        README_TOOLS_AVAILABLE, 
        SEARCH_TOOLS_AVAILABLE,
        DEEP_FIND_TOOLS_AVAILABLE
    )
    
    if README_TOOLS_AVAILABLE:
        logger.info("✅ README + Package Health tools available")
    else:
        logger.warning("⚠️  README tools not available")
    
    if SEARCH_TOOLS_AVAILABLE:
        logger.info("✅ Web search tools available")
    else:
        logger.warning("⚠️  Web search tools not available")
    
    if DEEP_FIND_TOOLS_AVAILABLE:
        logger.info("✅ Deep documentation finder available")
    else:
        logger.info("ℹ️  Deep finder not available (optional)")
    
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    logger.info(f"LLM: {llm_model}")
    
    if is_ollama_llm():
        logger.info("✅ Ollama mode - Memory optimized")
    
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
        # PHASE 1: RESEARCH (Agents 1-5)
        # ====================================================================
        logger.info("🚀 PHASE 1: RESEARCH CREW")
        logger.info("=" * 70)
        logger.info("   Agents: 1-5")
        logger.info("   1. Orchestrator → Strategy")
        logger.info("   2. README Analyst → Docs")
        logger.info("   3. Package Health → Validation")
        logger.info("   4. Web Researcher → Fallback + Deep Search")
        logger.info("   5. Source Validator → Quality")
        logger.info("")
        logger.info("   ⏱️  Est: 5-8 minutes...")
        logger.info("")
        
        research_crew, research_tasks = build_research_crew_optimized(topic)
        research_result = research_crew.kickoff()
        
        if not research_result:
            raise RuntimeError("No result from research crew")
        
        logger.info("✅ Phase 1 Complete")
        logger.info("")
        
        # Extract research data as strings
        orchestration_data = extract_task_output(research_tasks["orchestration"], "orchestrator")
        readme_data = extract_task_output(research_tasks["readme"], "readme")
        health_data = extract_task_output(research_tasks["health"], "health")
        web_data = extract_task_output(research_tasks["web"], "web")
        quality_data = extract_task_output(research_tasks["quality"], "quality")
        
        # ====================================================================
        # 🔍 DEBUG: DATA LOSS DETECTION (v4.4.1)
        # ====================================================================
        logger.info("=" * 70)
        logger.info("🔍 DEBUG: Data Extraction Analysis")
        logger.info("=" * 70)
        logger.info(f"README output: {len(readme_data)} chars")
        logger.info(f"  - Contains '```': {readme_data.count('```')} fences")
        logger.info(f"  - Contains 'python': {readme_data.lower().count('python')}")
        logger.info(f"Health output: {len(health_data)} chars")
        logger.info(f"  - Contains '```': {health_data.count('```')} fences")
        logger.info(f"Web output: {len(web_data)} chars")
        logger.info(f"  - Contains '```': {web_data.count('```')} fences")
        logger.info(f"  - Contains 'deep search': {'yes' if 'deep' in web_data.lower() else 'no'}")
        logger.info("")
        
        # ====================================================================
        # 🚨 VALIDATION GATE (v4.4.1 - ALWAYS CONTINUES)
        # ====================================================================
        logger.info("=" * 70)
        logger.info("🔍 QUALITY ASSESSMENT: Analyzing Phase 1 Research")
        logger.info("=" * 70)
        
        validation_issues = []
        validation_warnings = []
        
        # CHECK 1: Quality Rating
        logger.info("Check 1: Quality rating...")
        validator_rating = "Unknown"
        validator_abort = False
        
        rating_match = re.search(r'Quality\s+Rating:\s*([A-F][+]?)', quality_data, re.IGNORECASE)
        if rating_match:
            validator_rating = rating_match.group(1)
            logger.info(f"   Validator rating: {validator_rating}")
        else:
            logger.warning("   ⚠️  Could not extract validator rating")
        
        if "ABORT" in quality_data:
            validator_abort = True
            logger.warning("   ⚠️  Validator suggested ABORT")
        
        # CHECK 2: Code Blocks Count (from ALL sources)
        logger.info("Check 2: Code examples...")
        
        # Count code blocks with multiple patterns
        readme_code_count = (
            readme_data.count("```python") +
            readme_data.count("```py") +
            readme_data.count("```bash") +
            readme_data.count("```sh") +
            readme_data.count("```console")
        )
        health_code_count = (
            health_data.count("```python") +
            health_data.count("```py") +
            health_data.count("```bash") +
            health_data.count("```console")
        )
        web_code_count = (
            web_data.count("```python") +
            web_data.count("```py") +
            web_data.count("```bash") +
            web_data.count("```sh") +
            web_data.count("```console")
        )
        
        total_code_blocks = readme_code_count + health_code_count + web_code_count
        
        logger.info(f"   README: {readme_code_count} blocks")
        logger.info(f"   Health: {health_code_count} blocks")
        logger.info(f"   Web: {web_code_count} blocks")
        logger.info(f"   📊 TOTAL: {total_code_blocks} code blocks")
        
        # CHECK 3: Version Information
        logger.info("Check 3: Version data...")
        has_version = False
        
        version_patterns = [
            r'version[:\s]+(\d+\.\d+\.?\d*)',
            r'v(\d+\.\d+\.?\d*)',
            r'(\d+\.\d+\.?\d*)',
        ]
        
        for pattern in version_patterns:
            if re.search(pattern, readme_data, re.IGNORECASE) or re.search(pattern, health_data, re.IGNORECASE):
                has_version = True
                break
        
        if has_version:
            logger.info("   ✓ Version information found")
        else:
            logger.warning("   ⚠️  Version information unclear")
        
        # CHECK 4: Documentation Completeness
        logger.info("Check 4: Documentation completeness...")
        readme_length = len(readme_data.strip())
        web_length = len(web_data.strip())
        total_content = readme_length + web_length
        
        logger.info(f"   README: {readme_length} chars")
        logger.info(f"   Web: {web_length} chars")
        logger.info(f"   Total: {total_content} chars")
        
        if readme_length < 500 and web_length > 1000:
            logger.warning(f"   ⚠️  README short, using web-sourced content")
        elif total_content < 1000:
            logger.warning(f"   ⚠️  Limited total documentation")
        
        # ====================================================================
        # 🎯 QUALITY SCORING (v4.4.1 - NON-BLOCKING)
        # ====================================================================
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎯 CALCULATING QUALITY SCORE")
        logger.info("=" * 70)
        
        quality_score, critical_issues, quality_warnings = calculate_quality_score(
            total_code_blocks=total_code_blocks,
            readme_length=readme_length,
            web_length=web_length,
            has_version=has_version,
            validator_rating=validator_rating,
            validator_abort=validator_abort
        )
        
        logger.info(f"📊 Quality Score: {quality_score}")
        logger.info("")
        
        if critical_issues:
            logger.error("❌ CRITICAL ISSUES:")
            for issue in critical_issues:
                logger.error(f"   {issue}")
            logger.error("")
        
        if quality_warnings:
            logger.warning("⚠️  QUALITY WARNINGS:")
            for warning in quality_warnings:
                logger.warning(f"   {warning}")
            logger.warning("")
        
        # Quality interpretation
        quality_messages = {
            "A": "🟢 HIGH QUALITY - Excellent source material with comprehensive examples",
            "B": "🟡 GOOD QUALITY - Acceptable source material with adequate examples",
            "C": "🟠 MODERATE QUALITY - Limited examples, proceed with caution",
            "D": "🔴 LOW QUALITY - Very limited examples, synthesized content expected",
            "F": "⚫ MINIMAL QUALITY - No code examples, conceptual content only"
        }
        
        logger.info(quality_messages.get(quality_score, "Unknown quality"))
        logger.info("")
        
        # ====================================================================
        # ✅ ALWAYS PROCEED (v4.4.1)
        # ====================================================================
        logger.info("=" * 70)
        logger.info("✅ PROCEEDING TO PHASE 2 (ALWAYS PUBLISH MODE)")
        logger.info("=" * 70)
        logger.info("")
        
        if quality_score in ["F", "D"]:
            logger.warning("⚠️  LOW QUALITY DETECTED - Writers will be instructed to:")
            logger.warning("   • Synthesize conceptual explanations from prose")
            logger.warning("   • Create illustrative pseudo-code where needed")
            logger.warning("   • Add quality disclaimer to post")
            logger.warning("   • Focus on educational value over code examples")
            logger.warning("")
        elif quality_score == "C":
            logger.info("ℹ️  MODERATE QUALITY - Writers will work with available examples")
            logger.info("")
        
        # ====================================================================
        # COMBINE RESEARCH CONTEXT (with quality metadata)
        # ====================================================================
        
        # Generate disclaimer if needed
        quality_disclaimer = generate_quality_disclaimer(quality_score, critical_issues, quality_warnings)
        
        # Determine primary source
        if readme_code_count > web_code_count:
            primary_source = "README (official documentation)"
        elif web_code_count > 0:
            primary_source = "Web search (community resources)"
        else:
            primary_source = "Conceptual synthesis (limited source material)"
        
        full_research_context = f"""
# RESEARCH CONTEXT: {topic.title}

## QUALITY METADATA (v4.4.1)
**Quality Score**: {quality_score}/A
**Primary Source**: {primary_source}
**Code Examples Available**: {total_code_blocks}
**Documentation Completeness**: {total_content} characters
**Version Info**: {'Available' if has_version else 'Limited'}

### Quality Instructions for Writers:
{f"⚠️ CRITICAL: Only {total_code_blocks} code examples available." if total_code_blocks < 3 else ""}
{f"⚠️ Synthesize conceptual explanations from available prose." if quality_score in ["F", "D"] else ""}
{f"✓ Use {total_code_blocks} code examples as primary material." if total_code_blocks >= 3 else ""}
{f"✓ Web-sourced content is primary - README insufficient." if web_code_count > readme_code_count else ""}

### Quality Disclaimer (system note – do NOT copy into article)
{(
    "[No disclaimer needed - quality acceptable]"
    if not quality_disclaimer
    else "A short quality notice will be added AUTOMATICALLY before the article by the system if needed. "
         "Do NOT write any quality notice or warning blockquote in the article body."
)}


## Strategy & Orchestration
{orchestration_data}

## README Analysis
{readme_data}

## Package Health Validation
{health_data}

## Web Research & Deep Search
{web_data}

## Source Quality Assessment
{quality_data}

---
WRITING INSTRUCTIONS:
- Quality level: {quality_score}
- If code examples are limited, focus on conceptual understanding
- Synthesize from available prose descriptions
- Create illustrative pseudo-code if needed
- Be transparent about limitations in the content
- Ensure post provides educational value regardless of code quantity
---

END OF RESEARCH CONTEXT
"""
        
        logger.info(f"📊 Research Context: {len(full_research_context)} chars")
        logger.info(f"   • Quality score: {quality_score}")
        logger.info(f"   • Code blocks: {total_code_blocks}")
        logger.info(f"   • Primary source: {primary_source}")
        logger.info("")
        
        # ====================================================================
        # MEMORY CLEANUP (CRITICAL)
        # ====================================================================
        collected = cleanup_phase_memory(research_crew, research_tasks, research_result)
        
        # Delete local variables explicitly
        del orchestration_data, readme_data, health_data, web_data, quality_data
        
        # Additional garbage collection
        collected += gc.collect()
        
        logger.info(f"   ✓ Total cleanup: {collected} objects")
        logger.info(f"   ✓ Retained: Research context string + quality metadata")
        logger.info("")
        
        # ====================================================================
        # PHASE 2: WRITING (Agents 6-11)
        # ====================================================================
        logger.info("🚀 PHASE 2: WRITING CREW")
        logger.info("=" * 70)
        logger.info("   Agents: 6-11")
        logger.info("   6. Content Planner → Outline")
        logger.info("   7. Technical Writer → Article")
        logger.info("   8. Code Validator → Check")
        logger.info("   9. Code Fixer → Fix")
        logger.info("   10. Content Editor → Polish")
        logger.info("   11. Metadata Publisher → SEO")
        logger.info("")
        logger.info(f"   Quality Context: {quality_score} level content")
        logger.info("   ⏱️  Est: 10-15 minutes...")
        logger.info("")
        
        writing_crew, writing_tasks = build_writing_crew_optimized(topic, full_research_context)
        writing_result = writing_crew.kickoff()
        
        if not writing_result:
            raise RuntimeError("No result from writing crew")
        
        logger.info("✅ Phase 2 Complete")
        logger.info("")
        logger.info("🔍 Extracting outputs...")
        
        # Extract final outputs
        body = extract_task_output(writing_tasks["fixing"], "fixer")
        if not body or len(body) < 800:
            logger.warning("⚠️  Fixer output short, trying writer...")
            body = extract_task_output(writing_tasks["writing"], "writer")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Writer output short, trying editor...")
            body = extract_task_output(writing_tasks["editing"], "editor")
        
        if not body or len(body) < 500:
            logger.error("❌ Insufficient output from all agents")
            logger.error(f"   Final length: {len(body) if body else 0} chars")
            # Still continue - better to have something than nothing
            if not body:
                body = f"# {topic.title}\n\nContent generation encountered issues. Please refer to official documentation."
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # Add quality disclaimer if needed
        if quality_disclaimer:
            body = quality_disclaimer + "\n\n" + body
            logger.info("   ✓ Added quality disclaimer to post")
        
        # Final validation
        all_valid, issues, code_blocks = validate_all_code_blocks(body)
        if not all_valid:
            logger.warning("⚠️  Code validation issues:")
            for issue in issues[:5]:
                logger.warning(f"   {issue}")
        
        logger.info(f"   ✓ {len(code_blocks)} code blocks in final post")
        logger.info("")
        
        # Parse metadata
        meta_raw = extract_task_output(writing_tasks["metadata"], "publisher")
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
        
        # Add quality indicator to metadata
        if quality_score in ["F", "D", "C"]:
            if "tags" not in meta:
                meta["tags"] = []
            meta["tags"].append(f"quality-{quality_score.lower()}")
        
        logger.info("")
        
        # Build and save
        filename, content = build_jekyll_post(today, topic, body, meta, blog_assets_dir)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Success summary
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ BLOG POST PUBLISHED (ALWAYS PUBLISH MODE)")
        logger.info("=" * 70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {len(code_blocks)} Python + {bash_blocks} Bash")
        logger.info(f"   Quality: {quality_score}/A")
        logger.info("")
        
        if quality_score in ["F", "D"]:
            logger.warning("⚠️  LOW QUALITY POST - Review recommended:")
            logger.warning(f"   • Quality score: {quality_score}")
            logger.warning(f"   • Code examples: {total_code_blocks}")
            logger.warning(f"   • Consider manual enhancement")
            logger.warning("")
        
        logger.info("🧠 Memory Optimization:")
        logger.info("   • Split-crew architecture ✓")
        logger.info("   • Quality assessment (non-blocking) ✓")
        logger.info("   • Phase 1 GC completed ✓")
        logger.info("   • Context string transfer ✓")
        logger.info("   • Peak RAM reduced ~40% ✓")
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info(f"   1. Review: cat {path.relative_to(BASE_DIR)}")
        if quality_score in ["F", "D", "C"]:
            logger.info(f"   2. ⚠️  QUALITY CHECK: Verify content accuracy")
            logger.info(f"   3. Consider: Manual code example additions")
        logger.info(f"   4. Test code: Extract and run")
        logger.info(f"   5. Preview: jekyll serve")
        logger.info(f"   6. Publish: git commit")
        logger.info("")
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_optimized_pipeline()