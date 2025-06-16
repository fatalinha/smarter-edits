""" Post-editing translations with automatic error annotations - June 2025
- compares error spans between the human edits and the automatic ones word-by-word
- computes prec, rec, F1, average precision and AUC
Usage: python precision-auc.py <human-spans> <automatic-spans>
"""
import re
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, auc, roc_auc_score

def extract_labels(text):
    """Return list of (word, label) from a tagged sentence."""
    tokens = []
    label = 0
    text = text.replace("<major>", "<start>").replace("</major>", "<end>")
    text = text.replace("<minor>", "<start>").replace("</minor>", "<end>")

    parts = re.split(r"(<start>|<end>)", text)
    for part in parts:
        if part == "<start>":
            label = 1
        elif part == "<end>":
            label = 0
        else:
            words = part.strip().split()
            tokens.extend([(w, label) for w in words])
    return tokens

# File paths
human_file = "clin35/main_eng-nld_doc10_oracle_input.txt"
auto_file = "clin35/main_eng-nld_doc10_supervised_input.txt"

y_true = []
y_pred = []

with open(human_file, "r", encoding="utf-8") as hf, \
     open(auto_file, "r", encoding="utf-8") as af:

    for human_line, auto_line in zip(hf, af):
        try:
            _, human_target = map(str.strip, human_line.split("|||", 1))
            _, auto_target = map(str.strip, auto_line.split("|||", 1))
        except ValueError:
            continue  # skip malformed lines

        human_tokens = extract_labels(human_target)
        auto_tokens = extract_labels(auto_target)

        # Align by word (simple: assume same tokenization)
        words_human = [w for w, _ in human_tokens]
        words_auto = [w for w, _ in auto_tokens]

        if words_human != words_auto:
            continue  # skip misaligned lines

        y_true.extend([lbl for _, lbl in human_tokens])
        y_pred.extend([lbl for _, lbl in auto_tokens])

# Metrics
precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)
avg_precision = average_precision_score(y_true, y_pred)
auc = roc_auc_score(y_true, y_pred)

print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")
print(f"F1 Score:  {f1:.3f}")
print(f"Avg Precision:  {avg_precision:.3f}")
print(f"AUC:       {auc:.3f}")
