"""
Models for representation of search results
"""

import json
import string

import search.sorting
from xmodule.modulestore import Location

import nltk


class SearchResults:
    """
    This is a collection of all search results to a query.

    In addition to extending all of the standard collection methods (__len__, __getitem__, etc...)
    this lets you use custom sorts and filters on the included search results.
    """

    def __init__(self, response, **kwargs):
        """kwargs should be the GET parameters from the original search request
        filters needs to be a dictionary that maps fields to allowed values"""
        raw_results = json.loads(response.content).get("hits", {"hits": []})["hits"]
        self.query = " ".join(kwargs.get("s", False))
        if not self.query:
            self.entries = []
        else:
            entries = [SearchResult(entry, self.query) for entry in raw_results]
            sort = kwargs.get("sort", "relevance")
            self.entries = search.sorting.sort(entries, sort)

    def get_category(self, category="all"):
        """
        Returns a subset of all results that match the given category

        If you pass in an empty category the default is to return everything
        """

        if category == "all" or category is None:
            return self.entries
        else:
            return [entry for entry in self.entries if entry.category == category]


class SearchResult:
    """
    A single element from the Search Results collection
    """

    def __init__(self, entry, query):
        self.data = entry
        self.category = json.loads(entry["id"])["category"]
        self.url = _return_jump_to_url(entry)
        self.score = entry["_score"]
        if entry["thumbnail"].startswith("/static/"):
            self.thumbnail = _get_content_url(self.data, entry["thumbnail"])
        else:
            self.thumbnail = entry["thumbnail"]
        self.snippets = _snippet_generator(self.data["searchable_text"], query)


def _get_content_url(data, static_url):
    """
    Generates a real content url for problems specified with static urls

    Nobody seems to know how this works, but this hack works for everything I can find.
    """

    base_url = "/c4x/%s/%s/asset" % (json.loads(data["id"])["org"], json.loads(data["id"])["course"])
    addendum = static_url.replace("/static/", "")
    addendum.replace("/", "_")
    current = "/".join([base_url, addendum])
    substring = current[current.find("images/"):].replace("/", "_")
    substring = current[:current.find("images/")] + substring
    return substring


def _snippet_generator(transcript, query, soft_max=50, word_margin=25, bold=True):
    """
    This returns a relevant snippet from a given search item with direct matches highlighted.

    The intention is to break the text up into sentences, identify the first occurence of a search
    term within the text, and start the snippet at the beginning of that sentence.

    e.g: Searching for "history", the start of the snippet for a search result that contains "history"
    would be the first word of the first sentence containing the word "history"

    If no direct match is found the start of the document is used as the snippet.

    The bold flag determines whether or not the matching terms should be wrapped in a tag.

    The soft_max is the number of words at which we stop actively indexing (normally the snippeting works
    on full sentences, so when the soft_max is reached the snippet will stop at the end of that sentence.)

    The word margin is the maximum number of words past the soft max we allow the snippet to go. This might
    result in truncated snippets.
    """

    punkt = nltk.data.load('tokenizers/punkt/english.pickle')
    sentences = punkt.tokenize(transcript)
    substrings = [word.lower() for word in query.split()]
    query_container = lambda sentence: any(substring in sentence.lower() for substring in substrings)
    tripped = False
    response = ""
    for sentence in sentences:
        if not tripped:
            if query_container(sentence):
                tripped = True
                response += sentence
        else:
            if (len(response.split()) + len(sentence.split()) < soft_max):
                response += " " + sentence
            else:
                response += " " + " ".join(sentence.split()[:word_margin])
                break
    # If this is a phonetic match, there might not be a direct text match
    if tripped is False:
        for sentence in sentences:
            if (len(response.split()) + len(sentence.split())) < soft_max:
                response += " " + sentence
            else:
                response += " " + " ".join(sentence.split()[:word_margin])
                break
    if bold:
        response = _match_highlighter(query, response)
    return response


def _match(words):
    """
    Determines whether two words are close enough to each other to be called a "match"

    The check is whether one of the words contains each other and if their lengths are within
    a relatively small tolerance of each other.
    """

    contained = lambda words: (words[0] in words[1]) or (words[1] in words[0])
    near_size = lambda words: abs(len(words[0]) - len(words[1])) < (len(words[0]) + len(words[1])) / 6
    return contained(words) and near_size(words)


def _match_highlighter(query, response, tag="b", css_class="highlight"):
    """
    Highlights all direct matches within given snippet
    """

    wrapping = ("<" + tag + " class=" + css_class + ">", "</" + tag + ">")
    if isinstance(response, unicode):
        punctuation_map = {ord(char): None for char in string.punctuation}
        depunctuation = lambda word: word.translate(punctuation_map)
    else:
        depunctuation = lambda word: word.translate(None, string.punctuation)
    wrap = lambda text: wrapping[0] + text + wrapping[1]
    query_set = set(word.lower() for word in query.split())
    bold_response = ""
    for word in response.split():
        if any(_match((query_word, depunctuation(word.lower()))) for query_word in query_set):
            bold_response += wrap(word) + " "
        else:
            bold_response += word + " "
    return bold_response


def _return_jump_to_url(entry):
    """
    Generates the proper jump_to url for a given entry
    """

    fields = ["tag", "org", "course", "category", "name"]
    location = Location(*[json.loads(entry["id"])[field] for field in fields])
    url = '/courses/{0}/jump_to/{1}'.format(entry["course_id"], location)
    return url
