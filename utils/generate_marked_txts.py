""" Post-editing translations with automatic error annotations - May 2025
Given a file containing errors, explanations and the corrected translation, generates files with marked errors:
- all_errors
- only errors edited by xTower
- no errors, only spans edited by xTower
- all errors but merged to match word boundaries

Usage: python generate_marked_txts.py <error_explanations_file.json> """
import json
import os
import re

def insert_tags(text, tag_spans):
    """
    Insert start and end tags for error spans.
    If a span starts with a space, move the space before the opening tag.
    tag_spans: list of tuples (start, end, tag)
    Returns the new text with properly placed tags.
    """
    # Sort spans by start index
    tag_spans = sorted(tag_spans, key=lambda x: x[0])
    result = []
    last_idx = 0

    for start, end, tag in tag_spans:
        # Add text up to the start of this span
        result.append(text[last_idx:start])

        span_text = text[start:end]
        # If the span starts with a space and doesn't cross word boundaries
        if span_text.startswith(" "):
            # Move the leading space outside the tag
            result.append(" ")
            span_text = span_text[1:]

        result.append(f"<{tag}>{span_text}</{tag}>")
        last_idx = end

    # Add the rest of the text
    result.append(text[last_idx:])

    return ''.join(result)

def build_error_highlighted_text(src, mt, errors, edited_only=False):
    tagged_spans = []
    for err in errors:
        if edited_only and not err.get("edited"):
            continue
        tag = err["severity"]
        tagged_spans.append((err["start"], err["end"], tag))

    mt_tagged = insert_tags(mt, tagged_spans)
    return f"{src} ||| {mt_tagged}"

def build_edit_highlighted_text(src, mt, edits):
    """Insert <edit> tags and append new text after each edit."""
    offset = 0
    segments = []
    for edit in sorted(edits, key=lambda x: x["orig_start"]):
        start = edit["orig_start"] + offset
        end = edit["orig_end"] + offset
        orig = mt[start:end]
        edit_markup = f"<minor>{orig}</minor>{{{edit['edit_text']}}}" ### <edit> </edit>
        mt = mt[:start] + edit_markup + mt[end:]
        offset += len(edit_markup) - (end - start)
    return f"{src} ||| {mt}"

def merge_error_spans_into_words(mt, errors):
    """ For each error span:
        - If it already spans multiple words, leave it untouched.
        - If it’s fully inside a single word, expand it to cover the full word.
        - Collapse multiple error spans inside a word using the first tag."""
    # Convert errors into sorted spans
    spans = sorted(
        [{"start": e["start"], "end": e["end"], "tag": e["severity"]} for e in errors],
        key=lambda x: x["start"]
    )

    # Merge overlapping/adjacent spans, using the first tag
    merged = []
    if spans:
        curr = spans[0]
        for span in spans[1:]:
            if span["start"] <= curr["end"]:
                curr["end"] = max(curr["end"], span["end"])
                # keep curr["tag"]
            else:
                merged.append(curr)
                curr = span
        merged.append(curr)

    # Expand merged spans to word boundaries  ##TODO: exclude words ending in punctuation
    word_boundaries = [(m.start(), m.end()) for m in re.finditer(r"\S+", mt)]
    expanded = []
    for m in merged:
        new_start, new_end = m["start"], m["end"]
        for w_start, w_end in word_boundaries:
            if w_start <= m["start"] < w_end:
                new_start = w_start
            if w_start < m["end"] <= w_end:
                new_end = w_end
        expanded.append({"start": new_start, "end": new_end, "tag": m["tag"]})

    # Final re-merge to remove any overlap/duplicates created during expansion
    final = []
    if expanded:
        curr = expanded[0]
        for span in expanded[1:]:
            if span["start"] <= curr["end"]:
                curr["end"] = max(curr["end"], span["end"])
                # keep curr["tag"]
            else:
                final.append(curr)
                curr = span
        final.append(curr)

    # Insert tags
    tagged_spans = [(s["start"], s["end"], s["tag"]) for s in final]
    return insert_tags(mt, tagged_spans)

def generate_files(json_file_path, out_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    base_name = os.path.splitext(os.path.basename(json_file_path))[0]
    all_errors_path = out_path + f"{base_name}_all.txt"
    edited_errors_path = out_path + f"{base_name}_edited_errors.txt"
    edits_only_path = out_path + f"{base_name}_edits.txt"
    merged_path = out_path + f"{base_name}_all_long.txt"

    with open(all_errors_path, "w", encoding="utf-8") as all_f, \
         open(edited_errors_path, "w", encoding="utf-8") as edited_f, \
         open(edits_only_path, "w", encoding="utf-8") as edits_f, \
            open(merged_path, "w", encoding="utf-8") as merged_f:

        for entry in entries:
            src = entry["src"]
            mt = entry["mt"]
            errors = entry.get("errors", [])
            edits = entry.get("edits", [])

            # 1. All errors
            all_line = build_error_highlighted_text(src, mt, errors, edited_only=False)
            all_f.write(all_line + "\n")

            # 2. Edited errors only
            edited_line = build_error_highlighted_text(src, mt, errors, edited_only=True)
            edited_f.write(edited_line + "\n")

            # 3. Edits only
            edit_line = build_edit_highlighted_text(src, mt, edits)
            edits_f.write(edit_line + "\n")

            # 4. Merged word-level tags
            merged_line = f"{src} ||| {merge_error_spans_into_words(mt, errors)}"
            merged_f.write(merged_line + "\n")

    print("Files generated:")
    print(f"- {all_errors_path}")
    print(f"- {edited_errors_path}")
    print(f"- {edits_only_path}")
    print(f"- {merged_path}")

# === Run Example ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python generate_txt_outputs.py <input_json> <output_path")
        sys.exit(1)

    infile = sys.argv[1]
    outpath = sys.argv[2]
    generate_files(infile, outpath)
    #generate_files("doc1_output.json", "/home/alina/PycharmProjects/EAMT25/02_data/wmt_devsets/")