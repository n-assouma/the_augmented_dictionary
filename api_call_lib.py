import anthropic
import json
import os

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
            return self.message
        else:
            return "Unable to define that word/expression for safety reason"

class UnexpectedAnswerError(Exception):
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        if self.message:
            return self.message

        else:
            return 'An unexpected error occured'

class OutputParsingError(Exception):
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self):
        if self.message:
            return self.message
        else:
            return 'Error while parsing the Ouput'
    

def build_prompt(word: str, context: str | None = None) -> str:
    """
    Build the prompt from the user input that is to be passed in API request
    """

    prompt = 'Word: ' + word
    # Add context if there is one
    prompt += ', Context: ' + context if context else '' 

    return prompt

def make_request(user_prompt: str) -> anthropic.types.Message:
    """
    TODO
    """
    local_system_prompt = SYSTEM_PROMPT
    request_num = 0
    MAX_REQUEST = 2
    complete_answer = False
    while not complete_answer:

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
                local_system_prompt += ' BE EXTREMELY CONCISE!'
                request_num += 1
                if request_num < MAX_REQUEST:
                    continue
                else:
                    raise UnexpectedAnswerError(
                        f"Incomplete answer. Stop reason: {message.stop_reason}"
                    )

            case 'end_turn':
                complete_answer = True

            # Not handled cases
            case _:
                raise UnexpectedAnswerError(
                    f"Unexpected answer. Stop reason: {message.stop_reason}"
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
            f'Error while parsing the output.\n'
            f'Error message: {e} \n'
            f'Stop reason status: {message.stop_reason}'
        ) 
    return response

