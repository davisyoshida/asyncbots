"""Module for handling parsing of commands"""
from functools import reduce
from pyparsing import CaselessLiteral, Group, NoMatch, Optional


class SlackParser():
    """Class which manages parsing expressions for all registered bots"""
    def __init__(self, alert='!'):
        self.dm_expr_head = Optional(CaselessLiteral(alert))
        self.expr_head = CaselessLiteral('!')
        self.commands = []
        self.reinit_exprs()

    def reinit_exprs(self):
        """Combines all expressions into a single expression which can be used to match commands."""
        command = reduce(lambda acc, e: acc | e[1], self.commands, NoMatch())
        self.dm_expr = self.dm_expr_head + command
        self.expr = self.expr_head + command

    def parse(self, text, dm=False):
        """
        Attempts to match the text to the set of expressions the parser has.
        Throws pyparsing.ParseException if there is no match.
        """
        return (self.dm_expr if dm else self.expr).parseString(text)

    def add_command(self, expr, name, priority=0):
        """
        Adds a command to the parser.
        Currently insertion of a new command is done in linear time but in practice
        this is not a problem, as the number of handlers is small (< 1000).
        Having a large number of handlers will cause problems in other
        areas before this.
        """
        add_expr = Group(expr).setResultsName(name)
        for i, (p, _) in enumerate(self.commands):
            if priority >= p:
                self.commands.insert(i, (priority, add_expr))
                break
        else:
            self.commands.append((priority, add_expr))
        self.reinit_exprs()
