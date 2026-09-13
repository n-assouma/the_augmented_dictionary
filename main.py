import anthropic
import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_TOKENS = 124
TEMPERATURE = 0.1

SYSTEM_PROMPT = (
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

class AnswerDeclinedError(Exception):
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        if self.message:
            print(self.message)
        else:
            print("Unable to define that word/expression for safety reason")

class UnexpectedAnswerError(Exception):
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        if self.message:
            print(self.message)

        else:
            print('An unexpected error occured')

class OutputParsingError(Exception):
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        if self.message:
            print(self.message)
        else:
            print('Error while parsing the Ouput')
    

def build_prompt(word: str, context: str | None = None) -> str:
    """
    Build the prompt from the user input that is to be passed in API request
    """

    prompt = 'Word: ' + word
    prompt += ', Context: ' + context if context else '' # Add context if there is one

    return prompt

def make_request(user_prompt: str) -> anthropic.types.Message:
    """
    TODO
    """
    local_system_prompt = SYSTEM_PROMPT
    request_num = 0
    MAX_REQUEST = 2
    complete_answer = False
    while not complete_answer and request_num < MAX_REQUEST:

        # Make API call
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
            system=local_system_prompt,
            extra_body={"temperature": TEMPERATURE}
        )

        # Check stop reason to ensure LLM response is complete
        match message.stop_reason:
            case 'refusal':
                raise AnswerDeclinedError

            case 'max_tokens':
                local_system_prompt += 'BE EXTREMLY CONCISE!'
                request_num += 1
                continue

            case 'end_turn':
                complete_answer = True

            # None handled cases
            case _:
                raise UnexpectedAnswerError(
                    "Incomplete answer. Stop reason:", message.stop_reason
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
        # likely reason it fails are 
        # Max token reached, answer declined by the LLM
        # check stop reason
        raise OutputParsingError(
            'Error while parsing the output.',
            '\nError message:',
            e,
            '\nStop reason status:',
            message.stop_reason
        ) 
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
        help='Word to define (30 chars max)',
        type=str
    )

    parser.add_argument(
        '-c', '--context',
        help='Provide context to the word to define (200 chars max)',
        type=str,
    )

    args = parser.parse_args()

    # Validation of input:
    # Word must be less than 30 chars
    # The context must be concise as well ~ 200 chars
    word_len = len(args.word)
    context_len = len(args.context) if isinstance(args.context, str) else 0
    if word_len > 30 or context_len > 200:
        parser.print_help()
        sys.exit()

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