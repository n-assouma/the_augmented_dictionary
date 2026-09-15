import argparse
import sys

from api_call_lib import (
    build_prompt, make_request, parse_output,
    AnswerDeclinedError, UnexpectedAnswerError,
    OutputParsingError
)
from history import load_history, save_search, touch_entry

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
    Parses CLI arguments for three modes:
    - plain lookup: a word is given (optionally with -c/--context)
    - browse history: no word, no --restore
    - restore: -r/--restore ID, reuses a past search, no API call
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'word',
        nargs='?',
        default=None,
        help='Word to define (30 chars max). Omit to browse history.',
        type=str
    )

    parser.add_argument(
        '-c', '--context',
        help="Provide context to the word to define (200 chars max)."
             " Need to specify cannot be used without a word",
        type=str,
    )

    parser.add_argument(
        '-r', '--restore',
        help='Restore a past search from history by its id', 
        type=int,
        default=None,
    )

    args = parser.parse_args()

    # Validation of input:
    if args.restore is not None and (args.word is not None or args.context is not None):
        parser.error('--restore cannot be combined with a word or context.')

    if args.word is None and args.context is not None and args.restore is None:
        parser.error('--context requires a word.')

    # Word must be less than 30 chars
    # The context must be concise as well ~ 200 chars
    word_len = len(args.word) if args.word else 0
    context_len = len(args.context) if isinstance(args.context, str) else 0
    if word_len > 30 or context_len > 200:
        parser.print_help()
        sys.exit()

    return args


if __name__ == '__main__':

    args = process_input()

    if args.restore is not None:
        # Restore mode: reuse a past search from history, no API call
        history = load_history()
        match = next(
            (entry for entry in history if int(entry['id']) == args.restore),
            None
        )
        if match is None:
            print(f'No history entry with id {args.restore}.')
            sys.exit()

        touch_entry(args.restore)
        display({
            'word': match['word'],
            'part of speech': match['part_of_speech'],
            'definition': match['definition'],
        })

    elif args.word is None:
        # Browse mode: no word given, show history instead of searching
        history = load_history()
        if not history:
            print('No history yet.')
        else:
            for entry in history:
                bookmark_tag = ' [bookmarked]' if entry['bookmark'] == 'yes' else ''
                print(
                    f"[{entry['id']}] {entry['word']} "
                    f"({entry['part_of_speech']}) - "
                    f"searched {entry['date_searched']}{bookmark_tag}"
                )

    else:
        # Normal lookup: make API call
        user_prompt = build_prompt(word=args.word, context=args.context)
        try:
            raw_message = make_request(user_prompt)
        except AnswerDeclinedError as e:
            print(e)
            sys.exit()
        except UnexpectedAnswerError as e:
            print(e)
            sys.exit()

        # Parse output
        try:
            response = parse_output(raw_message)
        except OutputParsingError as e:
            print(e)
            sys.exit()

        # display it
        display(response)

        # record the search in history
        save_search(
            word=response['word'],
            part_of_speech=response['part of speech'],
            definition=response['definition'],
            context=args.context,
        )