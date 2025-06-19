import re
import os
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score

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

def compute_metrics(y_true, y_pred, label):
    if not y_true:
        print(f"No labels extracted for {label}. Cannot compute metrics.")
        return
    from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    avg_precision = average_precision_score(y_true, y_pred)
    if len(set(y_true)) > 1:
        auc_score = roc_auc_score(y_true, y_pred)
    else:
        auc_score = float('nan')
    print(f"\n--- Overall Metrics ({label}) ---")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1 Score:  {f1:.3f}")
    print(f"Avg Precision:  {avg_precision:.3f}")
    print(f"AUC:       {auc_score:.3f}")

directory_path_oracle = "human_spans/human_spans/"
import sys
directory_path_gemba = "output"

# --- Oracle vs Various Prediction Files ---
y_true_dict = {}
y_pred_dict = {}
file_types = [
    ("_all.txt", "all"),
    ("_all_long.txt", "all_long"),
    ("_edits.txt", "edits"),
    ("_edited_errors.txt", "edited_errors"),
]

oracle_files = sorted([f for f in os.listdir(directory_path_oracle) if f.endswith("_oracle_input.txt")])

for suffix, label in file_types:
    y_true = []
    y_pred = []
    pred_files = sorted([f for f in os.listdir(directory_path_gemba) if f.endswith(suffix)])
    file_pairs = []
    for oracle_file in oracle_files:
        base_name = oracle_file.replace("_oracle_input.txt", "")
        pred_file = base_name + suffix
        if pred_file in pred_files:
            file_pairs.append((os.path.join(directory_path_oracle, oracle_file), os.path.join(directory_path_gemba, pred_file)))
    if not file_pairs:
        print(f"No matching file pairs found for {label}. Please ensure your directory contains _oracle_input.txt and {suffix} files.")
        continue
    for human_file_path, pred_file_path in file_pairs:
        try:
            with open(human_file_path, "r", encoding="utf-8") as hf, \
                 open(pred_file_path, "r", encoding="utf-8") as pf:
                for human_line, pred_line in zip(hf, pf):
                    try:
                        _, human_target = map(str.strip, human_line.split("|||", 1))
                        _, pred_target = map(str.strip, pred_line.split("|||", 1))
                    except ValueError:
                        continue
                    human_tokens = extract_labels(human_target)
                    pred_tokens = extract_labels(pred_target)
                    words_human = [w for w, _ in human_tokens]
                    words_pred = [w for w, _ in pred_tokens]
                    if words_human != words_pred:
                        continue
                    y_true.extend([lbl for _, lbl in human_tokens])
                    y_pred.extend([lbl for _, lbl in pred_tokens])
        except FileNotFoundError:
            print(f"Error: One of the files not found - {human_file_path} or {pred_file_path}")
        except Exception as e:
            print(f"An error occurred while processing {human_file_path} and {pred_file_path}: {e}")
    compute_metrics(y_true, y_pred, f"oracle vs {label}")

