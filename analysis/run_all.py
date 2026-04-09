import os
import glob
import csv
import re
from analyse_log_module import analyze_log, load_sentences_from_file
import sys
import pandas as pd


DATA_DIR = sys.argv[1] #'/data'
OUTPUT_FILE = sys.argv[2] #'/data/results.csv'
ratings = sys.argv[3]

# Map actual text number to real filename
TEXT_NAMES = {
    1: 'news_pa.5274',
    2: 'doc13',
    3: 'news_scotsman.87462',
    4: 'doc18',
    5: 'news_seattle_times.799809',
    6: 'doc20',
    7: 'news_seattle_times.800119',
    8: 'doc34'
}

ratings_df = pd.read_csv(ratings)

def get_actual_text(pet_num, text_num):
    return ((text_num - 1 - (pet_num - 1) * 2) % 8) + 1


def get_condition(actual_text):  #TODO: actual or text_num
    return (text_num - 1) // 2 + 1


def get_domain(actual_text):
    return 'news' if actual_text % 2 != 0 else 'medical'

print(ratings_df.columns.tolist())

RATING_COLUMNS = [
    'How difficult to translate was the source text?',
    'How good was the quality of MT?',
    'How useful were the error annotations? ',
    'How accurate were the error annotations? ',
    'How useful were the translation suggestions? ',
    'How accurate were the translation suggestions? '
]

ratings_lookup = {}
for _, row in ratings_df.iterrows():
    key = (str(row["Translator's Code"]).strip(), str(int(row['Text number'])))
    ratings_lookup[key] = {col: row[col] for col in RATING_COLUMNS}

all_rows = []


# Find all log CSV files - sorted
log_files = sorted(
    glob.glob(os.path.join(DATA_DIR, 'PET_*', 'deliverables', 'log_Text*_PET_*.csv')),
    key=lambda f: (
        int(re.search(r'PET_(\d+)', f).group(1)),
        int(re.search(r'Text (\d+)', f).group(1))
    )
)

for log_file in log_files:
    # Extract PET number and Text number from filename
    filename = os.path.basename(log_file)
    print(filename)
    match = re.match(r'log_Text (\d+)_PET_(\d+)\.csv', filename)
    if not match:
        print(f"Skipping unrecognized filename: {filename}")
        continue

    text_num = int(match.group(1))
    pet_num = int(match.group(2))

    # Compute actual text, condition, domain
    actual_text = get_actual_text(pet_num, text_num)
    condition = get_condition(actual_text)
    domain = get_domain(actual_text)
    text_name = TEXT_NAMES.get(actual_text, 'unknown')  #

    # Build path to original txt file using actual text number !! Use original number
    txt_file = os.path.join(DATA_DIR, f'PET_{pet_num}', 'workfiles', f'Text {text_num}.txt')
    ###NO::::txt_file = os.path.join(DATA_DIR, f'PET_{pet_num}', 'workfiles', f'Text {actual_text}.txt')

    if not os.path.exists(txt_file):
        print(f"Warning: txt file not found: {txt_file}")
        continue

    # Run analysis
    rows = analyze_log(log_file, txt_file)

    # Get productivity from existing rows (same for all rows in file)
    productivity = rows[0]['productivity'] if rows else 0

    # Check which sentences are missing from the log - Some sentences were not edited by the transaltors
    sentences = load_sentences_from_file(txt_file)
    existing_sent_ids = {row['Sent_id'] for row in rows}

    for sent_id in range(len(sentences)):
        if (sent_id + 1) not in existing_sent_ids:
            # Add missing sentence with 0 keystrokes/time
            original_sentence = sentences[sent_id]
            num_major = len(re.findall(r'<major>.*?</major>', original_sentence))
            num_minor = len(re.findall(r'<minor>.*?</minor>', original_sentence))
            clean_sentence = re.sub(r'</?(?:major|minor)>|\{[^}]*\}', '', original_sentence)
            num_characters = len(clean_sentence)

            major_content = ''.join(re.findall(r'<major>(.*?)</major>', original_sentence))
            minor_content = ''.join(re.findall(r'<minor>(.*?)</minor>', original_sentence))
            highlighted_chars = len(major_content) + len(minor_content)
            highlight_ratio = round(highlighted_chars / num_characters, 4) if num_characters > 0 else 0.0

            rows.append({
                'PET': pet_num,
                'TEXT': 'Text ' + str(text_num),
                'text_name': text_name,
                'condition': condition,
                'domain': domain,
                'Sent_id': sent_id + 1,
                'keystrokes': 0,
                'time': 0,
                'productivity': productivity,
                'num_major': num_major,
                'num_minor': num_minor,
                'num_characters': num_characters,
                'highlight_ratio': highlight_ratio,
                'prc_sugg_accepted': 100 if condition == 4 else 'N/A',
                'tags_edited': ''
            })

    pet_code = f'PET_{pet_num}'  # adjust if Translator's Code has a different format
    #rating_key = (pet_code, str(text_num))
    rating_key = (f'PET_{pet_num}', str(text_num))  #TODO: ACTUAL_text oR TEXT_NUM???
    rating_data = ratings_lookup.get(rating_key, {col: '' for col in RATING_COLUMNS})

    # Add extra columns to each row
    for row in rows:
        row['condition'] = condition
        row['domain'] = domain
        row['text_name'] = text_name
        row.update(rating_data)

    all_rows.extend(rows)

    #print(f"Processing: PET {pet_num}, assigned text {text_num}, actual text {actual_text}")
    #print(f"Looking for txt file: {txt_file}")
    #print(f"Txt file exists: {os.path.exists(txt_file)}")


# Write combined CSV
if all_rows:
    fieldnames = ['PET', 'TEXT', 'text_name', 'condition', 'domain', 'Sent_id',
                  'keystrokes', 'time','productivity', 'num_major', 'num_minor', 'num_characters', 'highlight_ratio', 'prc_sugg_accepted', 'tags_edited'] + RATING_COLUMNS
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Done. Results written to {OUTPUT_FILE}")
else:
    print("No data found.")
