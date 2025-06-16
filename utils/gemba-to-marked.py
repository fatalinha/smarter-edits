""" Post-editing translations with automatic error annotations - May 2025
Given the output of GEMBA, generate marked texts. """
import re
import ast
import sys

# File paths
sentence_file = sys.argv[1]  #"main_eng-nld_doc10_no_highlight_input.txt"
error_file = sys.argv[2]  #"main_eng-nld_doc10.gemba"
output_file = sys.argv[3]  #"main_eng-nld_doc10.txt.gemba"

def parse_error_dict(line):
    """Convert a defaultdict line into a real dictionary."""
    match = re.search(r"defaultdict\(.*?, (.*)\)$", line)
    if match:
        dict_str = match.group(1)
        try:
            return ast.literal_eval(dict_str)
        except Exception:
            return {}
    return {}

with open(sentence_file, "r", encoding="utf-8") as sent_f, \
     open(error_file, "r", encoding="utf-8") as err_f, \
     open(output_file, "w", encoding="utf-8") as out_f:

    for sent_line, err_line in zip(sent_f, err_f):
        sent_line = sent_line.strip()
        err_line = err_line.strip()

        if not sent_line:
            out_f.write("\n")
            continue

        # Parse sentence line
        try:
            source, target = map(str.strip, sent_line.split("|||", 1))
        except ValueError:
            out_f.write(sent_line + "\n")
            continue

        errors = parse_error_dict(err_line)

        for severity, messages in errors.items():
            tag = "major" if severity == "critical" or "major" else "minor"
            for msg in messages:
                # Extract quoted phrases from error message
                phrases = re.findall(r'"([^"]+)"', msg)
                for phrase in phrases:
                    if phrase in target.lower():
                        #target = target.replace(phrase, f"<{tag}>{phrase}</{tag}>", 1)
                        # Case-insensitive search with original casing preserved
                        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                        match = pattern.search(target)
                        if match:
                            original = match.group(0)
                            tagged = f"<{tag}>{original}</{tag}>"
                            target = target[:match.start()] + tagged + target[match.end():]
                            break  # only replace first match

        out_f.write(f"{source} ||| {target}\n")
