#!/usr/bin/env python3
"""Main pipeline orchestrator — crawl → summarize → generate site."""

import logging
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import crawler
import summarizer
import site_generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("pipeline")


def run():
    log.info("=== AstroAxis Pipeline Start ===")

    # Step 1: Crawl
    log.info("--- Step 1: Crawling feeds ---")
    new_count = crawler.crawl()
    log.info("Crawled %d new articles", new_count)

    if new_count == 0:
        log.info("No new articles, checking if summarization needed")

    # Step 2: Summarize
    log.info("--- Step 2: Summarizing ---")
    summarized = summarizer.run()
    log.info("Summarized %d articles", summarized)

    # Step 3: Generate site
    log.info("--- Step 3: Generating site ---")
    output = site_generator.generate()
    
    if output:
        log.info("=== Pipeline Complete: %s ===", output)
    else:
        log.warning("=== Pipeline Complete: no output generated ===")
    
    return output


if __name__ == "__main__":
    output_path = run()
    if output_path:
        print(f"SITE_OUTPUT={output_path}")
