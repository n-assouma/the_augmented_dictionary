import anthropic
import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_TOKENS = 124
TEMPERATURE = 0.1

system_prompt = (
    "You are a dictionary. Only define word sent by user using context if "
    "provided.  Find correct spelling if mispelled. Don't use the sent word "
    "in definition. DONT USE ANY TOOL! DONT DO ANYTHING ELSE UNDER NO "
    "CIRCUMSTANCE!"
)
        
json_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "word",
        "part of speech",
        "definition"
    ],
    "properties": {
        "word": {
            "type": "string"
        },
        "definition": {
            "type": "string"
        },
        "part of speech": {
            "type": "string",
            "enum": [
                "noun",
                "pronoun",
                "phrasal verb",
                "verb",
                "adjective",
                "adverb",
                "preposition",
                "conjunction",
                "interjection",
                "article",
                "None of above (bug)"
            ]
        }
    }
}
    

def build_prompt(word: str, context: str | None = None) -> str:
    """
    Build the prompt from the user input that is to be passed in API request
    """

    prompt = 'Word:' + word
    prompt += ',Context:' + context if context else '' # Add context if there is one

    return prompt

def make_request(user_prompt: str) -> anthropic.types.Message:
    """
    TODO
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": user_prompt}], 
        output_config={
            "format": {
                "type": "json_schema",
                "schema": json_schema,
            }
        },
        system=system_prompt,
        extra_body={"temperature": TEMPERATURE}
    )
    return message

def parse_output(message: anthropic.types.Message) -> dict:
    """
    TODO
    """

    text = message.content[0].text
    # Try convert the output into json file
    try:
        response = json.loads(text)

    except json.decoder.JSONDecodeError as e:
        # likely reason the if fails are 
        # Max token reached, answer declined by the LLM
        # check stop reason
        print(
            'Error while parsing the output.',
            '\nError message:',
            e,
            '\nStop reason status:',
            message.stop_reason
        ) 
        exit(1)

    return response

def display(response: dict) -> None:
    """
    TODO
    """

    print(
        f'{response['word']} ({response['part of speech']}):',
        response['definition'],
        sep='\n'
    )

def process_input() -> argparse.Namespace:
    """
    TODO
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'word',
        help='Word to define',
        type=str
    )

    parser.add_argument(
        '-c', '--context',
        help='Provide context to the word to define',
        type=str,
    )

    args = parser.parse_args()
    return args



if __name__ == '__main__':

    args = process_input()

    # make API call
    user_prompt = build_prompt(word=args.word, context=args.context)
    raw_message = make_request(user_prompt)

    # Parse output
    response = parse_output(raw_message)
    # display it
    display(response)