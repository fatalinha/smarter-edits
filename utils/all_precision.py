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

directory_path = "." # Assuming files are in the current directory for this example

# --- Oracle vs Gemba ---
y_true_gemba = []
y_pred_gemba = []

oracle_files = sorted([f for f in os.listdir(directory_path) if f.endswith("_oracle_input.txt")])
gemba_files = sorted([f for f in os.listdir(directory_path) if f.endswith(".gemba")])

file_pairs_gemba = []
for oracle_file in oracle_files:
    base_name = oracle_file.replace("_oracle_input.txt", "")
    gemba_file = base_name + ".gemba"
    if gemba_file in gemba_files:
        file_pairs_gemba.append((os.path.join(directory_path, oracle_file), os.path.join(directory_path, gemba_file)))
    else:
        print(f"Warning: No matching .gemba file found for {oracle_file}")

if not file_pairs_gemba:
    print("No matching file pairs found for gemba. Please ensure your directory contains _oracle_input.txt and .gemba files.")
else:
    for human_file_path, auto_file_path in file_pairs_gemba:
        print(f"Processing (oracle vs gemba): {os.path.basename(human_file_path)} and {os.path.basename(auto_file_path)}")
        try:
            with open(human_file_path, "r", encoding="utf-8") as hf, \
                 open(auto_file_path, "r", encoding="utf-8") as af:
                for human_line, auto_line in zip(hf, af):
                    try:
                        _, human_target = map(str.strip, human_line.split("|||", 1))
                        _, auto_target = map(str.strip, auto_line.split("|||", 1))
                    except ValueError:
                        continue
                    human_tokens = extract_labels(human_target)
                    auto_tokens = extract_labels(auto_target)
                    words_human = [w for w, _ in human_tokens]
                    words_auto = [w for w, _ in auto_tokens]
                    if words_human != words_auto:
                        continue
                    y_true_gemba.extend([lbl for _, lbl in human_tokens])
                    y_pred_gemba.extend([lbl for _, lbl in auto_tokens])
        except FileNotFoundError:
            print(f"Error: One of the files not found - {human_file_path} or {auto_file_path}")
        except Exception as e:
            print(f"An error occurred while processing {human_file_path} and {auto_file_path}: {e}")

compute_metrics(y_true_gemba, y_pred_gemba, "oracle vs gemba")

# --- Oracle vs Supervised ---
y_true_sup = []
y_pred_sup = []

supervised_files = sorted([f for f in os.listdir(directory_path) if f.endswith("_supervised_input.txt")])

file_pairs_sup = []
for oracle_file in oracle_files:
    base_name = oracle_file.replace("_oracle_input.txt", "")
    sup_file = base_name + "_supervised_input.txt"
    if sup_file in supervised_files:
        file_pairs_sup.append((os.path.join(directory_path, oracle_file), os.path.join(directory_path, sup_file)))
    else:
        print(f"Warning: No matching _supervised_input.txt file found for {oracle_file}")

if not file_pairs_sup:
    print("No matching file pairs found for supervised. Please ensure your directory contains _oracle_input.txt and _supervised_input.txt files.")
else:
    for human_file_path, sup_file_path in file_pairs_sup:
        print(f"Processing (oracle vs supervised): {os.path.basename(human_file_path)} and {os.path.basename(sup_file_path)}")
        try:
            with open(human_file_path, "r", encoding="utf-8") as hf, \
                 open(sup_file_path, "r", encoding="utf-8") as sf:
                for human_line, sup_line in zip(hf, sf):
                    try:
                        _, human_target = map(str.strip, human_line.split("|||", 1))
                        _, sup_target = map(str.strip, sup_line.split("|||", 1))
                    except ValueError:
                        continue
                    human_tokens = extract_labels(human_target)
                    sup_tokens = extract_labels(sup_target)
                    words_human = [w for w, _ in human_tokens]
                    words_sup = [w for w, _ in sup_tokens]
                    if words_human != words_sup:
                        continue
                    y_true_sup.extend([lbl for _, lbl in human_tokens])
                    y_pred_sup.extend([lbl for _, lbl in sup_tokens])
        except FileNotFoundError:
            print(f"Error: One of the files not found - {human_file_path} or {sup_file_path}")
        except Exception as e:
            print(f"An error occurred while processing {human_file_path} and {sup_file_path}: {e}")

compute_metrics(y_true_sup, y_pred_sup, "oracle vs supervised")