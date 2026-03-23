# Smarter edits? Post-editing translations with automatic error annotations and corrections

## Data description
data.csv

- PET: translator ID	(1-8)
- TEXT: Text number in experiment order (1-8)
- text_name: Original name of the file
- condition: 1 for simple PE, 2 for PE with error annotations, 3 PE with simplified error annotations, 4 PE with translation suggestions	
- domain: news and medical	
- Sent_id: sentence ID	
- keystrokes: total number of keystrokes in sentence	
- time: total time to edit the sentence in seconds	
- num_major: number of major errors in sentence (cond 2-4)
- num_minor: number of minor errors in sentence (cond 2-4)
- num_characters: number of characters in sentence
- highlight_ratio: number of highlighted characters over total number of characters (cond 2-4)
- prc_sugg_accepted: percentage of suggestions accepted (cond 4)	
- tags_edited: strings of annotated text that were edited	
- prc_crit_err_fixed: percentage of manually inserted critical errors that were edited by the translator (per text)
- How difficult to translate was the source text?: perceived text difficulty (self reported)
- How good was the quality of MT?: perceived MT quality (self reported)
- How useful were the error annotations?: perceived annotation usefulness (self reported) (cond 2-4)	
- How accurate were the error annotations?: perceived annotation accuracy (self reported) (cond 2-4) 	
- How useful were the translation suggestions?: perceived suggestion usefulness (self reported) (cond 4) 	
- How accurate were the translation suggestions?: perceived suggestion accuracy (self reported) (cond 4) 	 
- MT_DA: Direct assessment of raw MT quality per sentence
- MT_spans: list of ESA annotated error spans
- MT_severity: list of severity of error annotated spans
- HT_DA: Direct assessment of PE quality per sentence	
- HT_spans: list of ESA annotated error spans
HT_severity: list of severity of error annotated spans

