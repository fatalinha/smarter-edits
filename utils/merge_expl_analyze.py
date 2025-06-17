""" Post-editing translations with automatic error annotations - May 2025
- Merges the source (src), machine translation (mt), and COMET score.
- Aligns the mt and correction using edit distance.
- Identifies which errors were actually changed in the correction.
- Finds and reports additional edits that were not flagged as errors.
- Outputs a structured JSON file for further analysis or evaluation.

Usage: python analyze_and_merge.py <spans_file.txt> <explanations.txt> <output_file.json>
"""
import json
import ast
import sys
import difflib


def load_main_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())

def load_explanations(path):
    explanations = []
    current_errors = []
    current_correction = ""

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        if line.startswith("Explanation for error"):
            explanation = line.split(":", 1)[1].strip()
            current_errors.append(explanation)
        elif line.startswith("Translation correction:"):
            current_correction = line.split(":", 1)[1].strip()
            explanations.append({
                "error_explanations": current_errors,
                "correction": current_correction
            })
            current_errors = []
            current_correction = ""

    return explanations

def get_word_offsets(text):
    """Return the starting character index of each word in the text."""
    words = text.split()
    offsets = []
    idx = 0
    for word in words:
        # Find the next occurrence of the word starting at idx
        start = text.find(word, idx)
        offsets.append(start)
        idx = start + len(word)
    return offsets, words

def get_alignment_words(mt, corr):
    """Compute word-level alignment and map to character-level spans."""
    mt_offsets, mt_words = get_word_offsets(mt)
    corr_offsets, corr_words = get_word_offsets(corr)

    sm = difflib.SequenceMatcher(None, mt_words, corr_words)
    edits = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            orig_start = mt_offsets[i1]
            orig_end = mt_offsets[i2-1] + len(mt_words[i2-1]) if i2 > i1 else mt_offsets[i1]
            edit_start = corr_offsets[j1]
            edit_end = corr_offsets[j2-1] + len(corr_words[j2-1]) if j2 > j1 else corr_offsets[j1]

            edits.append({
                "orig_start": orig_start,
                "orig_end": orig_end,
                "orig_text": mt[orig_start:orig_end],
                "edit_start": edit_start,
                "edit_end": edit_end,
                "edit_text": corr[edit_start:edit_end]
            })

    return edits

def get_alignment(mt, correction):
    sm = difflib.SequenceMatcher(None, mt, correction)
    return sm.get_opcodes()

def map_mt_to_correction(alignment, mt_start, mt_end):
    corr_start = corr_end = None
    for tag, i1, i2, j1, j2 in alignment:
        if i2 <= mt_start:
            continue
        if i1 >= mt_end:
            break
        if tag == "equal" or tag == "replace":
            overlap_start = max(i1, mt_start)
            overlap_end = min(i2, mt_end)
            offset = overlap_start - i1
            length = overlap_end - overlap_start
            if corr_start is None:
                corr_start = j1 + offset
            corr_end = j1 + offset + length
    return corr_start, corr_end

def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or b_end <= a_start)

def merge_and_analyze(main_file, explanation_file, output_file):
    main_data = load_main_data(main_file)
    explanations = load_explanations(explanation_file)

    results = []
    exp_index = 0

    for entries in main_data.values():
        for entry in entries:
            mt = entry["mt"]
            errors = entry.get("errors", [])
            corr = mt  # default fallback if no correction
            processed_errors = []
            edits = []

            # Only consume an explanation block if there are errors
            if errors:
                if exp_index < len(explanations):
                    corr = explanations[exp_index]["correction"]
                    expl_errors = explanations[exp_index]["error_explanations"]
                else:
                    print("Warning: missing explanation for entry with errors.")
                    expl_errors = [""] * len(errors)

                alignment = get_alignment(mt, corr)

                # Process each error
                for i, err in enumerate(errors):
                    mt_seg = mt[err["start"]:err["end"]]
                    corr_start, corr_end = map_mt_to_correction(alignment, err["start"], err["end"])
                    if corr_start is not None and corr_end is not None:
                        corr_seg = corr[corr_start:corr_end]
                        was_edited = 1 if mt_seg != corr_seg else 0
                    else:
                        was_edited = 0
                    processed_errors.append({
                        "start": err["start"],
                        "end": err["end"],
                        "severity": err["severity"],
                        "error_explanation": expl_errors[i] if i < len(expl_errors) else "",
                        "edited": was_edited
                    })

                # Capture non-error edits ##WHY DID I WANT TO DO IT THIS WAY?
                #if all(not overlaps(i1, i2, e["start"], e["end"]) for e in errors):
                # Capture all edits, even if they overlap with errors
                """for tag, i1, i2, j1, j2 in alignment:
                    #if tag != "equal":
                    edits.append({
                        "orig_start": i1,
                        "orig_end": i2,
                        "orig_text": mt[i1:i2],
                        "edit_start": j1,
                        "edit_end": j2,
                        "edit_text": corr[j1:j2]})"""
                try:
                    edits = get_alignment_words(mt, corr) ### Newsweek index out of range
                except IndexError:
                    continue

                exp_index += 1  # consume explanation only when errors exist

            # No errors → just keep mt and empty fields
            results.append({
                "src": entry["src"],
                "mt": mt,
                "COMET": entry["COMET"],
                "correction": corr,
                "errors": processed_errors,
                "edits": edits
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Output written to {output_file}")

# === Run Script ===
if __name__ == "__main__":
    #if len(sys.argv) != 4:
    #    print("Usage: python analyze_and_merge.py <main_file.txt> <explanations.txt> <output.json>")
    #    sys.exit(1)
    #merge_and_analyze(sys.argv[1], sys.argv[2], sys.argv[3])
    main_file =  "02_data/wmt24_spans/test-en-news_newsweek.63908.txt"                # Replace with txt span file
    explanation_file = "02_data/wmt24_explanations/test-en-news_newsweek.63908.txt"     # Replace with txt explanation
    output_file = "02_data/wmt24_merged/test-en-news_newsweek.63908.json"
    merge_and_analyze(main_file, explanation_file, output_file)

