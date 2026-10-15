import json
import os
from core.utils import get_user_profile, verify_token
from core.content import fetch_batches, fetch_subjects, fetch_topics, fetch_notes, fetch_dpp
from core.tests import (
    fetch_batch_tests,
    fetch_chapter_tests,
    fetch_test_questions,
    fetch_test_syllabus,
    fetch_test_performance,
    generate_test_html,
    generate_test_markdown,
    generate_test_json,
    zip_test_papers,
)
from core.announcer import fetch_announcements

with open("data/token.txt") as f:
    token = f.read().strip()

print("1. Verifying Token...")
v = verify_token(token)
assert v.get("success"), f"Token invalid: {v}"
print("   PASS: Token valid.")

print("2. Extracting User Profile...")
prof = get_user_profile(token)
print(f"   PASS: Welcome {prof['name']} ({prof['initials']}) | Streak: {prof['streak']} | XP: {prof['xp']}")

print("3. Fetching All Batches (Free & Paid)...")
batches = fetch_batches(token, amount="all", fetch_all=True)
assert len(batches) > 0, "No batches found"
free_count = sum(1 for b in batches if b['is_free'])
paid_count = sum(1 for b in batches if not b['is_free'])
print(f"   PASS: Found {len(batches)} batches total ({paid_count} Paid, {free_count} Free).")

# Locate 12-UF292CA
target_batch = None
for b in batches:
    if "12-UF292CA" in b["name"] or "12-uf292ca" in b.get("slug", ""):
        target_batch = b
        break
assert target_batch is not None, "Target batch 12-UF292CA not found!"
batch_id = target_batch["_id"]
batch_slug = target_batch["slug"]
print(f"   PASS: Target batch found: '{target_batch['name']}' (ID: {batch_id})")

print("4. Fetching Batch Tests ('All Tests')...")
b_tests = fetch_batch_tests(token, batch_id)
assert len(b_tests) > 0, "No tests found in batch"
ready_tests = [t for t in b_tests if t.get("attempted")]
print(f"   PASS: Found {len(b_tests)} tests ({len(ready_tests)} attempted/ready to extract).")
sample_test_names = [t['name'] for t in b_tests[:8]]
print(f"   Sample tests: {', '.join(sample_test_names)}")

print("5. Testing Test Extraction & Generation for WT-02...")
wt02 = next((t for t in b_tests if "WT-02" in t["name"]), ready_tests[0])
mapping_id = wt02["mapping_id"]
test_id = wt02["test_id"]

qs = fetch_test_questions(token, mapping_id)
assert len(qs) > 0, f"No questions extracted for {wt02['name']}"
print(f"   PASS: Extracted {len(qs)} questions with choices and solutions!")

# Verify syllabus
syl = fetch_test_syllabus(token, test_id)
assert len(syl) > 0, "Syllabus was empty"
print(f"   PASS: Extracted syllabus ({len(syl)} chars)")

# Verify performance
perf = fetch_test_performance(token, test_id)
assert perf is not None, "Performance was None"
print(f"   PASS: Extracted performance: Score {perf.get('user_score')}/{perf.get('total_score')}, Accuracy {perf.get('accuracy')}%")

# Generate HTML
html_out = generate_test_html(wt02, qs, target_batch["name"])
assert "MathJax" in html_out, "MathJax missing from HTML"
assert wt02["name"] in html_out, "Test name missing from HTML"
print(f"   PASS: Generated HTML paper ({len(html_out)} bytes)")

# Generate Markdown
md_out = generate_test_markdown(wt02, qs)
assert len(md_out) > 0, "Markdown output was empty"
print(f"   PASS: Generated Markdown paper ({len(md_out)} chars)")

# Generate JSON
json_out = generate_test_json(wt02, qs)
assert len(json_out) > 0, "JSON output was empty"
print(f"   PASS: Generated JSON export ({len(json_out)} bytes)")

# Test ZIP bundling
zip_stream = zip_test_papers({
    "wt02.html": html_out,
    "wt02.md": md_out,
    "wt02.json": json_out
})
assert zip_stream.getbuffer().nbytes > 1000, "ZIP buffer too small"
print("6. Testing Universal Extraction on Unattempted Test (UT-03_NEET)...")
ut03 = next((t for t in b_tests if "UT-03" in t["name"]), None)
assert ut03 is not None, "UT-03 test not found in batch"
qs_unattempted = fetch_test_questions(token, mapping_id=ut03.get("mapping_id"), test_id=ut03["test_id"], batch_id=batch_id)
assert len(qs_unattempted) > 0, "Failed to extract questions from unattempted test"
print(f"   PASS: Successfully extracted {len(qs_unattempted)} questions with answer key & solutions from unattempted test!")

print("7. Testing Extraction on Free Batch (MISSION 30 NEET 2026)...")
free_b = next((b for b in batches if "MISSION 30" in b["name"]), None)
if free_b:
    free_tests = fetch_batch_tests(token, free_b["_id"])
    print(f"   PASS: Found {len(free_tests)} tests in free batch '{free_b['name']}'")
    if free_tests:
        ft0 = free_tests[0]
        ft_qs = fetch_test_questions(token, mapping_id=ft0.get("mapping_id"), test_id=ft0["test_id"], batch_id=free_b["_id"])
        assert len(ft_qs) > 0, f"Failed to extract questions from {ft0['name']}"
        print(f"   PASS: Successfully extracted {len(ft_qs)} questions from {ft0['name']} in Free Batch!")

print("8. Testing Features 5, 7, 8 (Booklet, OMR, ICS, Obsidian Vault)...")
from core.tests import (
    generate_two_column_exam_booklet,
    generate_printable_omr_sheet,
    generate_test_ics_calendar,
    export_to_obsidian_vault,
)
from core.pdf_exporter import html_to_pdf, compile_test_curated_pdfs, zip_pdf_papers

booklet_html = generate_two_column_exam_booklet(wt02, qs, target_batch["name"])
assert len(booklet_html) > 0, "Booklet HTML was empty"
print(f"   PASS: Generated Two-Column Booklet HTML ({len(booklet_html)} bytes)")

omr_html = generate_printable_omr_sheet(wt02, len(qs))
assert len(omr_html) > 0, "OMR HTML was empty"
print(f"   PASS: Generated Printable OMR HTML ({len(omr_html)} bytes)")

ics_data = generate_test_ics_calendar(b_tests[:5], target_batch["name"])
assert "BEGIN:VCALENDAR" in ics_data, "ICS calendar invalid"
print(f"   PASS: Generated RFC 5545 ICS Calendar ({len(ics_data)} bytes)")

v_path, v_content = export_to_obsidian_vault(wt02, qs, target_batch["name"])
assert os.path.exists(v_path), f"Obsidian vault file not found at {v_path}"
print(f"   PASS: Exported Obsidian Vault Markdown to {v_path}")

print("9. Testing Curated PDF Compilation Engine...")
curated_pack = compile_test_curated_pdfs(wt02, qs[:10], target_batch["name"])
assert curated_pack["booklet_pdf"] is not None and len(curated_pack["booklet_pdf"]) > 1000, "Booklet PDF empty"
assert curated_pack["solutions_pdf"] is not None and len(curated_pack["solutions_pdf"]) > 1000, "Solutions PDF empty"
assert curated_pack["omr_pdf"] is not None and len(curated_pack["omr_pdf"]) > 1000, "OMR PDF empty"
assert curated_pack["zip_pack"] is not None and curated_pack["zip_pack"].getbuffer().nbytes > 5000, "Curated ZIP empty"
print(f"   PASS: Compiled Booklet PDF ({len(curated_pack['booklet_pdf'])} bytes)")
print(f"   PASS: Compiled Solutions PDF ({len(curated_pack['solutions_pdf'])} bytes)")
print(f"   PASS: Compiled OMR PDF ({len(curated_pack['omr_pdf'])} bytes)")
print(f"   PASS: Compiled Curated PDFs ZIP ({curated_pack['zip_pack'].getbuffer().nbytes} bytes)")

print("\n=== ALL E2E AND PDF VERIFICATION TESTS PASSED SUCCESSFULLY! ===")
