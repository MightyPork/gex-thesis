#!/usr/bin/env python2

import subprocess
import sys
import re
import inspect
import datetime
import string
from collections import defaultdict, Counter
import nltk
try:
    nltk.pos_tag('Just trying to see if the NLTK dataset is installed')
except LookupError:
    nltk.download('maxent_treebank_pos_tagger')
try:
    nltk.word_tokenize('test')
except LookupError:
    nltk.download('punkt')

try:
    from clint.textui import colored
except:
    class Passthrough(object):
        def __getattr__(self, name):
            return lambda x: x

    colored = Passthrough()
    print "=== For colored output, install clint (via 'sudo pip install clint') ==="

PREPOSITIONS = ["a", "abaft", "aboard", "about", "above", "absent",
    "across", "afore", "after", "against", "along", "alongside", "amid",
    "amidst", "among", "amongst", "an", "apropos", "around", "as", "aside",
    "astride", "at", "athwart", "atop", "barring", "before", "behind", "below",
    "beneath", "beside", "besides", "between", "betwixt", "beyond", "but", "by",
    "circa", "concerning", "despite", "down", "during", "except", "excluding",
    "failing", "following", "for", "from", "given", "in", "including", "inside",
    "into", "lest", "like", "mid", "midst", "minus", "modulo", "near", "next",
    "notwithstanding", "of", "off", "on", "onto", "opposite", "out", "outside",
    "over", "pace", "past", "per", "plus", "pro", "qua", "regarding", "round",
    "sans", "save", "since", "than", "through,", "throughout,", "till", "times",
    "to", "toward", "towards", "under", "underneath", "unlike", "until", "unto",
    "up", "upon", "versus", "via", "vice", "with", "within", "without",
    "worth", "through"]

# Obtained with (avoiding the dependency):
# from nltk.corpus import stopwords
# stopwords.words("english")
STOPWORDS = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they',
'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom',
'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be',
'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while',
'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will',
'just', 'don', 'should', 'now']


CONJUNCTIONS = ["and", "but", "or", "yet", "for", "nor", "so"]


class Paper(object):

    ##########################################################################
    # INTERNAL STUFF  (you can ignore these functions)
    ##########################################################################

    def __init__(self, filenames):
        self.__filenames = filenames
        self.errors = 0
        self.__clear_caches()

    def __clear_caches(self):
        self.__text = {}
        self.__latex_text = None

    @staticmethod
    def __flatten_paragraphs(text):
        '''Given a text where paragraphs are separated by one or more
           empty lines, it puts every paragraph in a single, separate line.
           Example:

           I like sushi
           and pie.

           I ride
           horses.

           Becomes:
           I like sushi and pie.
           I ride horses '''
        return '\n'.join(paragraph.replace('\n', ' ')
                        for paragraph in re.split("\n(\s*\n)+", text)
                        if paragraph.strip())

    def __run_all_with_prefix(self, prefix):
        # Switch filename and clear caches
        for filename in self.__filenames:
            self.filename = filename
            self.__clear_caches()

            # Call all functions
            for name in filter(lambda n: n.startswith(prefix), dir(self)):
                attribute = getattr(self, name)
                if inspect.ismethod(attribute):
                        attribute()

    def _run_all_checks(self):
        self.__run_all_with_prefix('check_')

    def _run_all_tests(self):
        self.__filenames = ["TEST"]
        self.__run_all_with_prefix('test_')

    def _format_re_match(self, m, text):
        start_of_sentence = max(text.rfind('\n', 0, m.start()) + 1, 0)
        end_of_sentence = text.find('\n', m.end()), len(text)
        if end_of_sentence == -1:
            end_of_sentence = len(text)
        a_string_start = max(start_of_sentence, m.start() - 10)
        a_string_end = min(end_of_sentence, m.end() + 10)
        a_string = text[a_string_start : m.start()]
        a_string += colored.yellow(text[m.start() : m.end()])
        a_string += text[m.end() : a_string_end]
        to_return =  a_string.split('\n', 1)[0]
        return to_return.replace('\r',' ').replace('\n',' ')

    ##########################################################################
    # FUCTIONS THAT ARE RELEVANT FOR CHECKS WRITERS
    ##########################################################################

    def get_latex_text(self):
        ''' Returns the complete paper, with each paragraph on a single
            line. No latex/tex command is stripped '''
        if self.__latex_text != None:
            return self.__latex_text
        else:
            with open(self.filename) as f:
                text = f.read()
            self.__latex_text = self.__flatten_paragraphs(text)
            return self.__latex_text

    _IGNORED_ENVIRONMENTS = ("array",
                             "eqnarray",
                             "equation",
                             "figure",
                             "mathmatica",
                             "picture",
                             "table",
                             "verbatim",
                             "lstlisting")

    def get_text(self, ignored_environments=None):
        ''' Returns the textual content of the tex files, with latex/tex
        enviroments stripped. You can control the enviroments to strip via
        the 'ignored_environments' argument: if you don't, the default ones
        will be stripped'''
        if ignored_environments == None:
            ignored_environments = Paper._IGNORED_ENVIRONMENTS
        try:
            return self.__text[ignored_environments]
        except:
            # Cleanup annoying things
            text = self.get_latex_text()
            text = re.sub(r'\\cite{[^}]*}', '', text)
            text = re.sub(r'\\-', '', text)
            # Run it through detex
            p = subprocess.Popen(["detex",
                                  "-l",
                                  "-n",
                                  "-e",
                                  ','.join(ignored_environments)],
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
            p.stdin.write(text)
            text = p.communicate()[0]
            p.stdin.close()
            self.__text[ignored_environments] = self.__flatten_paragraphs(
                text)
            return self.__text[ignored_environments]


    def perform_test(self, function, expected_errors_num):
        self.errors = 0
        function()
        assert expected_errors_num == self.errors

    def print_issue(self, message, match=None, text=None):
        if text == None:
            text = self.get_text()
        message = colored.red(message)
        if match and text:
            example = self._format_re_match(match, text)
        else:
            example = ''
        print "%30s - %s: %s" % (colored.green(self.filename),
                                 colored.red(message),
                                 example)

    ##########################################################################
    # CHECKS
    ##########################################################################

    def check_exempli_gratia_without_comma(self):
        for m in re.finditer(r'e\.g\.[^,]',
                             self.get_text(),
                             re.MULTILINE):
            self.print_issue("E.G. without comma", m)
            self.errors += 1

    def test__check_exempli_gratia_without_comma(self):
        self.get_text = lambda: "e.g. a pony \n e.g. what?, e.g., cool!"
        self.perform_test(self.check_exempli_gratia_without_comma, 2)

    ##########################################################################

    def check_id_est_without_comma(self):
        for m in re.finditer(r'i\.e\.[^,]',
                             self.get_text(),
                             re.MULTILINE):
            self.print_issue("I.E. without comma", m)
            self.errors += 1

    def test__check_id_est_without_comma(self):
        self.get_text = lambda: "i.e. a pony \n i.e. what?, i.e., cool!"
        self.perform_test(self.check_id_est_without_comma, 2)

    ##########################################################################

    def check_quotes(self):
        for m in re.finditer(r'"',
                             self.get_text(),
                             re.MULTILINE):
            self.print_issue('"hello" should be ``hello\'\'', m)
            self.errors += 1

    def test__check_quotes(self):
        self.get_text = lambda: '"this is not ok" ``but this is\'\''
        self.perform_test(self.check_quotes, 2)

    ##########################################################################

    def check_citing_with_unbreakeable_spaces(self):
        for keyword in ["cite", "ref"]:
            for m in re.finditer(r'(\W?)(^|\s)+\\' + keyword + r'\s*{',
                                 self.get_latex_text(),
                                 re.MULTILINE):
                if m.group(1) in [',', '&']:
                    continue
                self.print_issue('use hello~\%s{ instead of hello \%s{' % (keyword,
                                                                 keyword),
                                m, self.get_latex_text())
                self.errors += 1

    def test__check_citing_with_unbreakeable_spaces(self):
        self.get_latex_text = lambda: r'citing: wrong \cite{ciao} - right~\cite{ciao}'
        self.perform_test(self.check_citing_with_unbreakeable_spaces, 1)
        self.get_latex_text = lambda: r'refs done wrong \ref{ciao} - right~\ref{ciao}'
        self.perform_test(self.check_citing_with_unbreakeable_spaces, 1)
        self.get_latex_text = lambda: r'hello& \cite{ciao}'
        self.perform_test(self.check_citing_with_unbreakeable_spaces, 0)
        self.get_latex_text = lambda: r', \ref{ciao}'
        self.perform_test(self.check_citing_with_unbreakeable_spaces, 0)

    ##########################################################################

    def check_variations_of_word_spellings(self):
        words = defaultdict(Counter)
        for word in re.findall(r'\b\S+\b', self.get_text(), re.MULTILINE):
            word_alphanum = re.sub("[^a-zA-Z0-9_']+", '', word).lower()
            words[word_alphanum].update([word])
        for _, spellings_counter in words.iteritems():
            variations = len(spellings_counter.keys())
            total_appereances = sum(spellings_counter.values())
            if variations > 1:
                if len(set(w[1:] for w in spellings_counter.keys())) == 1:
                    # FIXME: for now, if it's just a case mismatch on the first
                    # letter, skip
                    continue
                normalized_word = spellings_counter.keys()[0].lower()
                if normalized_word in STOPWORDS + PREPOSITIONS + CONJUNCTIONS:
                    # Ignore common words
                    continue
                # Ignore numbers
                try:
                    float(normalized_word)
                    continue
                except ValueError:
                    pass
                self.print_issue('This word has multiple spellings: %s' % (
                    dict(spellings_counter)), None)
                self.errors += 1

    def test__check_variations_of_word_spellings(self):
        self.get_text = lambda: (r'I has a cybercriminal. I had a cyber-criminal. '
                                       r'or was it a CyberCriminal?')
        self.perform_test(self.check_variations_of_word_spellings, 1)
        self.get_text = lambda: (r'no strange words here, however put. '
                                       r'However, is that true?')
        self.perform_test(self.check_variations_of_word_spellings, 0)
        self.get_text = lambda: (r'It matters the it factor ')
        self.perform_test(self.check_variations_of_word_spellings, 0)
        self.get_text = lambda: (r'1.6 16 and other fancy numbers.')
        self.perform_test(self.check_variations_of_word_spellings, 0)

    ##########################################################################

    def check_commas_in_numbers(self):
        # We also check in tables
        text = self.get_text(ignored_environments=tuple(
                set(Paper._IGNORED_ENVIRONMENTS) - set('table')))
        for m in re.finditer('(^|[^\w\-])\d{4}', text, re.MULTILINE):
            if text[m.start():m.start() + 1] in string.punctuation:
                continue
            try:
                number = int(text[m.start():m.end()])
            except:
                number = 0
            if number not in range(1990, datetime.date.today().year + 2):
                self.errors += 1
                self.print_issue('Put commas in numbers over 1,000', m)

        # This is the correct rule, but nobody follows it
        # for m in re.finditer('(^|[^\w\-])\d{5}', text, re.MULTILINE):
        #     self.print_issue('Put commas in numbers over 10,000', m)
        #     self.errors += 1
        # for m in re.finditer('[^\d]\d,\d{3}[^,]', text, re.MULTILINE):
        #     self.print_issue("Don't put commas in numbers under 10,000", m)
        #     self.errors += 1

    def test__check_commas_in_numbers(self):
        def get_text(*args, **kwargs): return text
        self.get_text = get_text
        text = r'10000 cats eat 10,000 mice'
        self.perform_test(self.check_commas_in_numbers, 1)
        text = r'9999 cats eat 9,999 mice'
        self.perform_test(self.check_commas_in_numbers, 1)
        text = r'1000 cats eat 999,999 mice'
        self.perform_test(self.check_commas_in_numbers, 1)
        text = r'project N10000, grant CNS-20000'
        self.perform_test(self.check_commas_in_numbers, 0)
        text = r'In 2001, we ate spaghetti'
        self.perform_test(self.check_commas_in_numbers, 0)

    ##########################################################################

    def check_commas_after_quotes(self):
        for m in re.finditer("''\s*,",
                             self.get_text(),
                             re.MULTILINE):
            self.print_issue("Convert ``hello'', => ``hello,''", m)
            self.errors += 1

    def test__check_commas_after_quotes(self):
        self.get_text = lambda: r"``flower'', should be ``flower,''"
        self.perform_test(self.check_commas_after_quotes, 1)

    ##########################################################################

    def check_always_capitalize(self):

        for reg in ["internet", "javascript"]:
            for m in re.finditer(r"\b{0}".format(reg),
                                 self.get_text(),
                                 re.MULTILINE):
                self.print_issue("Always capitalize", m)
                self.errors += 1

    def test__check_always_capitalize(self):
        self.get_text = lambda: r"internet"
        self.perform_test(self.check_always_capitalize, 1)

        self.get_text = lambda: r"testinternet"
        self.perform_test(self.check_always_capitalize, 0)
    ##########################################################################
    #
    # def check_comma_before_that(self):
    #     for m in re.finditer(",\s+that",
    #                          self.get_text(),
    #                          re.MULTILINE):
    #         phrase_start = max([
    #             self.get_text().rfind(c, 0, m.start())
    #             for c in ['\n', '.', ':', ';']
    #         ] + [0])
    #         phrase = self.get_text()[phrase_start:m.start() + 1]
    #         if len([c for c in phrase if c == ',']) % 2 == 0:
    #             # An even number of commas found, skipping
    #             continue
    #         self.print_issue("Do not put a comma before 'that'", m)
    #         self.errors += 1
    #
    # def test__check_comma_before_that(self):
    #     self.get_text = lambda: r"I like cats, that eat mice"
    #     self.perform_test(self.check_comma_before_that, 1)
    #     self.get_text = lambda: r"I like cats that eat mice"
    #     self.perform_test(self.check_comma_before_that, 0)
    #
    # ##########################################################################
    #
    # def check_comma_before_which(self):
    #     for m in re.finditer("[^,'*\s]\s+which",
    #                          self.get_text(),
    #                          re.MULTILINE):
    #         word_before_start = self.get_text().rfind(' ', 0, m.start())
    #         word_before = re.search("\w+", self.get_text()[
    #                                             word_before_start + 1:
    #                                             m.start() + 1]).group()
    #         if word_before in PREPOSITIONS + CONJUNCTIONS:
    #             continue
    #         if word_before.endswith('ing') or word_before.endswith('ly'):
    #             continue
    #         # More expensive analysis: is the word before a verb?
    #         phrase_start = max([
    #             self.get_text().rfind(c, 0, m.start())
    #             for c in ['\n', '.', ':', ';']
    #         ] + [0])
    #         phrase = self.get_text()[phrase_start:m.start() + 1]
    #         word_before_kind = filter(lambda x: x[0] == word_before, nltk.pos_tag(
    #                                               nltk.word_tokenize(phrase)))[0][1]
    #         if word_before_kind.startswith('VB'):
    #             continue
    #         self.print_issue("Put a comma before 'which'", m)
    #         self.errors += 1
    #
    # def test__check_comma_before_which(self):
    #     self.get_text = lambda: r"I like that cat, which eat mice"
    #     self.perform_test(self.check_comma_before_which, 0)
    #     self.get_text = lambda: r"I like that cat which eat mice"
    #     self.perform_test(self.check_comma_before_which, 1)
    #     self.get_text = lambda: r"I know which cat eat mice"
    #     self.perform_test(self.check_comma_before_which, 0)

    ##########################################################################

    def check_word_before_ref_is_capitalized(self):
        text = self.get_latex_text()
        for m in re.finditer('\\\\ref', text, re.MULTILINE):
            word_before_start = max(text.rfind(' ', 0, m.start() - 2),
                                    text.rfind('~', 0, m.start() - 2))
            word_before = re.findall("\w+", text[word_before_start + 1:
                                                m.start() + 1])[-1]
            if not word_before in ["and"] and not word_before[0].isupper():
                self.print_issue(r'Capitalize the word before \ref', m, text)
                self.errors += 1

    def test__check_word_before_ref_is_capitalized(self):
        self.get_latex_text = lambda: "in Section \\ref{sec}, see Figure \\ref{fig}"
        self.perform_test(self.check_word_before_ref_is_capitalized, 0)
        self.get_latex_text = lambda: "in section \\ref{sec}, see figure \\ref{fig}"
        self.perform_test(self.check_word_before_ref_is_capitalized, 2)
        self.get_latex_text = lambda: "section \\ref{sec}"
        self.perform_test(self.check_word_before_ref_is_capitalized, 1)

    ##########################################################################

    def check_british_spelling(self):
        british_spellings = {"acknowledgement": "acknowledgment", "afterwards": "afterward", "arse": "ass", "backwards": "backward",
                             "cancelling": "canceling", "catalogue": "catalog", "centre": "center", "cheque": "check", "colour": "color", "dialogue": "dialog",
                             "favour": "favor", "flavour": "flavor", "forwards": "forward", "grey": "gray", "judgement": "judgment", "labour": "labor",
                             "lustre": "luster", "modelled": "modeled", "revelled": "raveled", "shovelled": "shoveled", "snivelled": "sniveled",
                             "theatre": "theater", "towards": "toward", "travelling": "traveling", "yodelling": "yodeling"}
        for british, american in british_spellings.iteritems():
            for m in re.finditer("[^\w]+" + british + "[^\w]+", self.get_text()):
                self.print_issue("Don't spell like a bugger (that's british english) -" \
                    " it's ' "+ american + " ' , not", m)
                self.errors += 1

    def test__check_british_spelling(self):
        self.get_text = lambda: r"Go to the (centre) of town to pick up the best flavour colour."
        self.perform_test(self.check_british_spelling, 3)
        self.get_text = lambda: r"I am an American, therefore I am"
        self.perform_test(self.check_british_spelling, 0)
        self.get_text = lambda: r"This cheque, right here, is unacceptable. I'll have to cheque with my manager."
        self.perform_test(self.check_british_spelling, 2)
        self.get_text = lambda: r"It is hard to parse this sentence."
        self.perform_test(self.check_british_spelling, 0)

    ##########################################################################

    def check_slang_and_gergal_terms(self):
        gergal = ['basically']
        for w in gergal:
            for m in re.finditer(w, self.get_text(),
                                 re.IGNORECASE):
                self.print_issue(
                    "This word doesn't sound like it should be in a paper: "
                    + w, m)
                self.errors += 1

    def test__check_slang_and_gergal_terms(self):
        self.get_text = lambda: r"Basically, this is wat we do"
        self.perform_test(self.check_slang_and_gergal_terms, 1)

    ##########################################################################

    def check_misplelled_standard_phrases(self):
        mispellings = {"in more details": "in more detail"}
        for wrong, right in mispellings.iteritems():
            for m in re.finditer("[^\w]+" + wrong + "[^\w]+", self.get_text()):
                self.print_issue("Mispelled standard phrase - ' %s ' "
                        "should be ' %s' in" % (wrong, right), m)
                self.errors += 1

    def test__check_misplelled_standard_phrases(self):
        self.get_text = lambda: r"I'll discuss this in more details in section"
        self.perform_test(self.check_misplelled_standard_phrases, 1)

    ##########################################################################

    def check_banned_words(self):
        banned_words = ["is[\s]+comprised[\s]+of",
                        "doesn't",
                        "beside",
                        "won't",
                        "can't"]
        for banned_word in banned_words:
            for m in re.finditer("([^\w]+|^)" + banned_word + "[^\w]+",
                                 self.get_text(), flags=re.IGNORECASE):
                self.print_issue("Don't use %s" % banned_word, m)
                self.errors += 1

    def test__check_banned_words(self):
        self.get_text = lambda: r"Adam is comprised of a brain and a stomach."
        self.perform_test(self.check_banned_words, 1)
        self.get_text = lambda: r"Adam comprises a brain and a stomach."
        self.perform_test(self.check_banned_words, 0)
        self.get_text = lambda: r"You don't know what that is. Comprised. Of."
        self.perform_test(self.check_banned_words, 0)
        self.get_text = lambda: r"Is comprised of blah and bloop."
        self.perform_test(self.check_banned_words, 1)
        self.get_text = lambda: r"Adam is awesome. Is comprised of blah and bloop."
        self.perform_test(self.check_banned_words, 1)
        self.get_text = lambda: r"Don't do this. I won't, tell anybody."
        self.perform_test(self.check_banned_words, 1)

    ##########################################################################

    def check_repeated_words(self):
        for m in re.finditer(r"\b(\w+)\W+\1\b",
                             self.get_text(), flags=re.IGNORECASE):
            if m.group(1).isdigit():
                continue
            self.print_issue("Repeated word '%s'" % m.group(1), m)
            self.errors += 1

    def test__check_repeated_words(self):
        self.get_text = lambda: r"We use this this and that."
        self.perform_test(self.check_repeated_words, 1)
        self.get_text = lambda: r"We use this and that, and this and that too."
        self.perform_test(self.check_repeated_words, 0)
        self.get_text = lambda: r"This. This is a sentence Sentence."
        self.perform_test(self.check_repeated_words, 2)
        self.get_text = lambda: r"Version 4.4."
        self.perform_test(self.check_repeated_words, 0)



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print """Usage:
 - chrisper *.tex

 - chrisper test
      Runs the test suite.
        """
        sys.exit(0)

    if sys.argv[1] == "test":
        Paper(sys.argv[2:])._run_all_tests()
        print colored.green("\n=== ALL TESTS PASSED ===")
    else:
        paper = Paper(sys.argv[1:])
        paper._run_all_checks()
        if paper.errors == 0:
            print colored.green('=== IT LOOKS GOOD TO ME. CONGRATS! ===')
        else:
            print colored.yellow("\n=== I'VE FOUND %d ISSUES ===" %
                    paper.errors)
            sys.exit(1)
