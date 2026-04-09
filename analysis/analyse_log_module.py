import pandas as pd
import argparse
import re
import difflib
import os
import csv


def get_tag_edit_list(tagged_sent, untagged_sent):
    """
    Compares a tagged sentence to an untagged one using an index map
    and difflib to correctly identify if edits occurred within a tag.
    This version correctly handles insert, delete, and replace operations.
    """
    tags_info = []
    clean_sent_parts = []
    last_idx = 0

    # Find all tag occurrences to process them sequentially
    for i, match in enumerate(re.finditer(r'<(minor|major)>(.*?)</\1>', tagged_sent)):
        tags_info.append({'id': i + 1, 'content': match.group(2)})
        clean_sent_parts.append({'type': 'text', 'content': tagged_sent[last_idx:match.start()]})
        clean_sent_parts.append({'type': 'tag', 'content': match.group(2), 'id': i + 1})
        last_idx = match.end()

    clean_sent_parts.append({'type': 'text', 'content': tagged_sent[last_idx:]})

    # return empty if no tags
    if not tags_info:
        return [], []

    # Step 1: Create the clean sentence and the index map
    clean_sentence = ""
    index_map = []
    for part in clean_sent_parts:
        content = part['content']
        clean_sentence += content
        tag_id_to_map = part.get('id', 0)
        index_map.extend([tag_id_to_map] * len(content))

    # Step 2: Use difflib and initialize results
    matcher = difflib.SequenceMatcher(a=clean_sentence, b=untagged_sent, autojunk=False)
    edit_results = [0] * len(tags_info)

    # Step 3: Analyze opcodes with corrected logic
    for code, i1, i2, j1, j2 in matcher.get_opcodes():
        if code == 'equal':
            continue

        if code == 'replace' or code == 'delete':
            # Check the range of characters that were replaced or deleted
            for i in range(i1, i2):
                if index_map[i] > 0:
                    tag_id = index_map[i]
                    edit_results[tag_id - 1] = 1
        elif code == 'insert':
            tag_to_edit = 0
            # An insert happens *before* index i1. We check the character
            # immediately preceding and at the insertion point.
            if i1 > 0 and index_map[i1 - 1] > 0:
                tag_to_edit = index_map[i1 - 1]
            elif i1 < len(index_map) and index_map[i1] > 0:
                tag_to_edit = index_map[i1]

            if tag_to_edit > 0:
                # Mark the corresponding tag as edited
                edit_results[tag_to_edit - 1] = 1

    return edit_results, tags_info


def load_sentences_from_file(file_path):
    """Load sentences from the text file and return them as a list."""
    try:
        for encoding in ['utf-8', 'latin-1', 'unicode_escape']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        else:
            print(f"Warning: Could not decode file '{file_path}' with any known encoding.")
            return []

        sentences = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Split by ||| to get source and target
            parts = line.split('|||')
            if len(parts) == 2:
                target_sentence = parts[1].strip()
                sentences.append(target_sentence)
            else:
                print(f"Warning: Line doesn't have exactly 2 parts: {line}")

        return sentences
    except FileNotFoundError:
        print(f"Warning: Could not find text file '{file_path}' for tag analysis.")
        return []


def analyze_log(file_path, txt_file):
    """
    Analyzes a log file to calculate keystrokes and time spent per sentence.

    Args:
        file_path (str): The path to the log CSV file.
    """
    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(file_path, on_bad_lines='warn', engine='python')
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return

    # Convert the 'time' column to datetime objects for calculations
    df['time'] = pd.to_datetime(df['time'])

    # Filter out rows with empty text_id, as they are not sentence-specific
    df_filtered = df[df['text_id'].notna() & (df['text_id'] != ' ')]

    # Get the unique sentence identifiers
    sentence_ids = df_filtered['text_id'].unique()

    # Load corresponding text file for tag analysis
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # Remove log_ prefix and _admin suffix to get the base filename
    if base_name.startswith('log_'):
        base_name = base_name[4:]
    if base_name.endswith('_admin'):
        base_name = base_name[:-6]

    text_file_path = txt_file  # os.path.join(os.path.dirname(file_path), base_name + '.txt')
    if text_file_path:
        print("file found" + txt_file)  # base_name)
    else:
        print("txt file not found")
    sentences = load_sentences_from_file(text_file_path)

    # Total number of suggestions in file
    total_suggestions_in_file = sum(len(re.findall(r'\{[^}]*\}', s)) for s in sentences)  # *Allow for empty sugg

    # Calculate total file time (first to last timestamp)
    if not df.empty:
        total_file_time = (df['time'].max() - df['time'].min()).total_seconds()
    else:
        total_file_time = 0

    # Calculate total characters in file
    total_characters = sum(len(re.sub(r'</?(?:major|minor)>|\{[^}]*\}', '', s)) for s in sentences)

    # Calculate productivity
    productivity = round(total_characters / total_file_time, 4) if total_file_time > 0 else 0

    # Extract PET and TEXT from filename
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if base_name.startswith('log_'):
        base_name = base_name[4:]

    # Split to get TEXT and PET
    parts = base_name.split('_')
    if len(parts) >= 3:
        text_name = '_'.join(parts[:-2])  # Everything except last 2 parts
        pet_name = parts[-1]  # Last part is PET
    else:
        text_name = base_name
        pet_name = "unknown"

    # Prepare output file path
    rows = []
    # --- Group by text_id to process each sentence ---
    grouped = df_filtered.groupby('text_id')

    for text_id, group in grouped:
        # 1. Calculate Keystrokes
        keystroke_events = group[group['event_type'].isin(['change', 'suggestion'])]
        num_keystrokes = len(keystroke_events)

        # 2. Calculate suggestions
        suggestion_events = group[group['event_type'] == 'suggestion']
        num_accepted = len(suggestion_events)

        sentence_idx = int(text_id)
        # * ALlow for empty suggestions {}
        suggestions_in_sentence = len(re.findall(r'\{[^}]*\}', sentences[sentence_idx])) if sentence_idx < len(sentences) else 0

        #print(f"DEBUG - text_id={text_id}, sentence_idx={sentence_idx}, num_accepted={num_accepted}, suggestions_in_sentence={suggestions_in_sentence}")
        #if num_accepted > suggestions_in_sentence:
        #    print(f"DEBUG - Sentence content: {sentences[sentence_idx]}")
        # 3. Tag edit analysis
        tags_edited_str = ''

        # Count major and minor errors, characters, and highlight ratio
        num_major = 0
        num_minor = 0
        num_characters = 0
        highlight_ratio = 0.0

        try:
            sentence_idx = int(text_id)
            if sentence_idx >= 0 and sentence_idx < len(sentences):
                original_sentence = sentences[sentence_idx]
                num_major = len(re.findall(r'<major>.*?</major>', original_sentence))
                num_minor = len(re.findall(r'<minor>.*?</minor>', original_sentence))

                # Count total characters (excluding tags and suggestions)
                # Remove tags and suggestion brackets
                clean_sentence = re.sub(r'</?(?:major|minor)>', '', original_sentence)
                clean_sentence = re.sub(r'\{[^}]*\}', '', clean_sentence)
                num_characters = len(clean_sentence)

                # Count characters inside tags
                major_content = ''.join(re.findall(r'<major>(.*?)</major>', original_sentence))
                minor_content = ''.join(re.findall(r'<minor>(.*?)</minor>', original_sentence))
                highlighted_chars = len(major_content) + len(minor_content)

                # Calculate highlight ratio
                if num_characters > 0:
                    highlight_ratio = round(highlighted_chars / num_characters, 4)
        except (ValueError, IndexError):
            pass

        try:
            sentence_idx = int(text_id)
            if sentence_idx >= 0 and sentence_idx < len(sentences):
                original_sentence = sentences[sentence_idx]

                # Get the final edited text from the last exit event
                exit_events = group[group['event_type'] == 'exit']
                if not exit_events.empty:
                    final_text = exit_events.iloc[-1]['text']

                    # Analyze tag edits
                    edit_results, tags_info = get_tag_edit_list(original_sentence, final_text)

                    if tags_info:
                        edited_tags = []
                        for i, was_edited in enumerate(edit_results):
                            if was_edited:
                                # edited_tags.append(f"Tag {i + 1}: '{tags_info[i]['content']}'")
                                edited_tags.append(f"'{tags_info[i]['content']}'")

                        if edited_tags:
                            tags_edited_str = '; '.join(edited_tags)
                        else:
                            tags_edited_str = ''  # None
                    else:
                        tags_edited_str = ''  # No tags found
        except (ValueError, IndexError):
            tags_edited_str = ''

        # 4. Calculate Time Taken (sum of all enter-exit pairs)
        enter_events = group[group['event_type'] == 'enter'].sort_values('time')
        exit_events = group[group['event_type'] == 'exit'].sort_values('time')

        time_seconds = 0
        if not enter_events.empty and not exit_events.empty:
            enter_times = enter_events['time'].values
            exit_times = exit_events['time'].values

            num_pairs = min(len(enter_times), len(exit_times))
            for i in range(num_pairs):
                duration = pd.Timestamp(exit_times[i]) - pd.Timestamp(enter_times[i])
                time_seconds += duration.total_seconds()

        rows.append({
            'PET': pet_name,
            'TEXT': text_name,
            'Sent_id': int(text_id) + 1,
            'keystrokes': num_keystrokes,
            'time': time_seconds,
            'productivity': productivity,
            'num_major': num_major,
            'num_minor': num_minor,
            'num_characters': num_characters,
            'highlight_ratio': highlight_ratio,
            'prc_sugg_accepted': round((num_accepted / suggestions_in_sentence) * 100, 2) if suggestions_in_sentence > 0 else 'N/A',
            'tags_edited': tags_edited_str
        })

    print(f"Analysis complete.")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(...)
    parser.add_argument("file_path", ...)
    parser.add_argument("txt_file", ...)
    args = parser.parse_args()

    rows = analyze_log(args.file_path, args.txt_file)
    if rows:
        output_file = args.file_path.replace('.csv', '_analysis.csv')
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Analysis complete. Output written to: {output_file}")
#rows = analyze_log("data/log_Text 7_PET_5.csv", "data/Text 7.txt")