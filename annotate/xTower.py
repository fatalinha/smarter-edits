""" Post-editing translations with automatic error annotations - May 2025
Given an xCOMET output file, run xTower to obtain translation explanations """
from vllm import LLM
from transformers import pipeline
import ast
import sys

def get_discrete_quality_score(score):
    """
    Discretizes a given quality score into categories.

    Args:
        score (float): The quality score to be discretized.

    Returns:
        str: The discrete quality category ('weak', 'moderate', 'good', 'excellent', 'best').
    """
    if score < 0.6:
        return 'weak'
    elif score < 0.8:
        return 'moderate'
    elif score < 0.94:
        return 'good'
    elif score < 0.98:
        return 'excellent'
    else:
        return 'best'


def annotate_translation_with_error_spans(translation, error_spans):
    """
    Annotates a translation string with error spans.

    Args:
        translation (str): The translation text to be annotated.
        error_spans (list of dict): A list of error spans, where each span is a dictionary
                                    with 'start', 'end', and 'severity' keys.

    Returns:
        str: The annotated translation text with error tags.
    """
    annotated_translation = str(translation)
    error_spans = list(sorted(error_spans, key=lambda x: x['start']))
    # Iterate over the error spans in reverse order
    for i, span in enumerate(error_spans[::-1]):
        error_id = len(error_spans) - i  # Assign a unique error ID based on the reverse index
        start, end, severity = span['start'], span['end'], span['severity'].lower()
        # Insert error tags around the specified span in the translation
        annotated_translation = (
            annotated_translation[:start].strip() +
            f" <error{error_id} severity='{severity}'>" +
            annotated_translation[start:end].strip() +
            f"</error{error_id}> " +
            annotated_translation[end:]
        )
    # Trim potential double spaces around error tags
    return annotated_translation.replace('  <', ' <').replace('>  ', '> ').strip()


def create_prompt(sample, src_lang, mt_lang):
    """
    Creates a prompt for translation quality assessment.

    Args:
        sample (dict): A dictionary containing the translation data.
        src_lang (str): The source language (e.g., "English).
        mt_lang (str): The machine translation language (e.g., "German).

    Returns:
        str: The generated prompt for translation quality assessment.
    """
    prompt = "<|im_start|>user"
    prompt += "\n"
    prompt += "You are provided with a Source, Translation, Translation quality analysis, and Translation quality score (weak, moderate, good, excellent, best). "
    prompt += "The Translation quality analysis contain a translation with marked error spans with different levels of severity (minor or major). "
    #prompt += "Additionally, we may provide a **reference translation**. "
    prompt += "Given this information, generate a short explanation for each error and a fully correct translation."
    prompt += "\n\n"
    prompt += f"{src_lang} source: {sample['src']}"
    prompt += "\n"
    prompt += f"{mt_lang} translation: {sample['mt']}"
    prompt += "\n"
    #if 'ref' in sample.keys():
    #    prompt += f"{mt_lang} reference: {sample['ref']}"
    #    prompt += "\n"
    prompt += f"Translation quality analysis: {sample['annotated_mt']}"
    prompt += "\n"
    prompt += f"Translation quality score: {sample['discrete_score']}"
    prompt += "<|im_end|>\n<|im_start|>assistant\n"
    return prompt


def load_xtower(generate_lib='vllm'):
    """
    Loads the xTower model using either VLLM (recommended) or Huggingface pipeline.

    Args:
        generate_lib (str): The library to use for loading the model ('vllm' or 'huggingface').

    Returns:
        object: The loaded language model.
    """
    if generate_lib == 'vllm':
        llm = LLM(model="sardinelab/xTower13B",
            tensor_parallel_size=1,
            enforce_eager=True, dtype="half"
        )

    else:
        llm = pipeline("text-generation",
            model="sardinelab/xTower13B",
            device_map="auto"
        )

    return llm


def prompt_xtower(prompts, llm):
    """
    Generates outputs based on the provided prompts using the selected library.

    Args:
        prompts (list of str): A list of prompts to generate responses for.
        llm (object): The loaded language model.

    Returns:
        list of str: The generated outputs for each prompt.
    """
    if isinstance(llm, LLM):
        from vllm import SamplingParams
        sampling_params = SamplingParams(temperature=0, max_tokens=1024, stop=["</s>"])
        responses = llm.generate(prompts, sampling_params)
        outputs = [response.outputs[0].text.strip() for response in responses]

    else:
        outputs = llm(prompts, max_new_tokens=1024, do_sample=False)

    return outputs


# read data
def read_data(input_file):
    """ Reads the data from file and returns lists of outputs.
    Args:
        input_file (file): Input file in txt.

    Returns:
        scores: A list of COMET scores
        translation_data: A list of dicts with "src" and "mt" as keys
        error_spans: A list of dicts with "start", "end" and "severity" as keys
    """
    with open(infile, "r") as f:
        content = f.read()

        # Convert string content to Python dictionary
        data = ast.literal_eval(content)

        # Prepare the processed data list
        translation_data = []
        scores = []
        error_spans = []
        for entries in data.values():
            for entry in entries:
                translation = {
                    "src": entry["src"],
                    "mt": entry["mt"]}
                error_span= [
                        {"start": err["start"],
                            "end": err["end"],
                            "severity": err["severity"]}
                        for err in entry.get("errors", [])
                    ]

                scores.append(entry["COMET"])
                translation_data.append(translation)
                error_spans.append(error_span)
    return scores, translation_data, error_spans


### MAIN
infile = sys.argv[1]  #"test-en-news_beverly_press.3585.txt"
outfile = sys.argv[2] 

# annotate the samples with error spans
scores, translation_data, error_spans = read_data(infile)
prompts = []
for i, e in enumerate(translation_data):
    sample = translation_data[i]
    score = scores[i]
    errors = error_spans[i]
    if errors:
        sample['annotated_mt'] = annotate_translation_with_error_spans(sample['mt'], errors)
        sample['discrete_score'] = get_discrete_quality_score(score)

        # create prompts
        prompt = create_prompt(sample, src_lang='English', mt_lang='Dutch')
        prompts.append(prompt)
print("Done creating the prompts.")

# Load Tower and generate outputs
xtower_llm = load_xtower(generate_lib='vllm')
outputs = prompt_xtower(prompts=prompts, llm=xtower_llm)
print("Done generating explanations")

# write outputs to file
with open(outfile, "w") as out:
    for output in outputs:
        out.write(output + "\n")
print("Explanations written in " + outfile)
