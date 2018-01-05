"""Definitions of a few commonly used symbols for convenience."""
from pyparsing import alphanums, nums, CaselessLiteral,\
        CharsNotIn, delimitedList, OneOrMore,\
        originalTextFor, printables, QuotedString,\
        quotedString, Regex, removeQuotes,\
        Suppress, White, Word

emoji = Regex(':[\\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')


def tail(name):
    """Match any amount of characters"""
    return Suppress(White(max=1)) + CharsNotIn('').setResultsName(name)

channel_name = Word(alphanums + '-').setResultsName('channel')

user_name = Word(alphanums + '-_.')

mention = Regex('<@(U[0-9A-Z]{8})>')

link = Word(printables)

int_num = Word(nums)

single_quotes = QuotedString("‘", endQuoteChar="’", escChar="\\")
double_quotes = QuotedString("“", endQuoteChar="”", escChar="\\")
quotedString.addParseAction(removeQuotes)
comma_list = delimitedList((single_quotes | double_quotes | quotedString
                            | originalTextFor(OneOrMore(Word(printables, excludeChars=","))))).setResultsName('comma_list')

alphanum_word = Word(alphanums)

def flag(name):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name).setResultsName(name)


def flag_with_arg(name, argtype):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name) + argtype.setResultsName(name)
