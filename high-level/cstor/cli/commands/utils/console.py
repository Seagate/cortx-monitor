#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing table implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.


class ConsoleTable(object):
    def __init__(self, title=None):
        self.__title = title
        self.__rows = []
        self.__headers = {}
        self.__align = {}
        self.__max_field_size = {}

    def __calc_field_sizes(self, kv):
        """Calculate max size of each field.

        :param kv: dictionary of field -> value
        """
        for field, value in kv.items():
            cur = self.__max_field_size.get(field, 0)
            new = len(str(value))
            if cur < new:
                self.__max_field_size[field] = new

    def set_header(self, **hmap):
        """Set header map.

        :param hmap: pairs of filed -> description
        """
        self.__headers = hmap.copy()
        self.__calc_field_sizes(self.__headers)

    def append(self, **fields):
        """Append a new row to a table.

        :param fields: pairs of field -> value
        """
        row = dict([(name, str(value)) for name, value in fields.items()])
        self.__rows.append(row)
        self.__calc_field_sizes(row)

        # prepare header
        if not self.__headers:
            hmap = dict([(n, n.title()) for n in row.keys()])
            self.set_header(**hmap)

    append_row = append

    def append_separator(self):
        self.__rows.append('-')

    def set_align(self, **kwargs):
        """Setup align for each field.

        Key is a name of field.
        Align value can be '<', '^', '>'.
        """
        for name, align in kwargs.items():
            self.__align[name] = align

    def __build_pattern(self, seq):
        pattern = ' '
        line_width = 1
        for field in seq:
            width = self.__max_field_size.get(field, 0)
            pattern += "{%s:%s%ds}  " % (field, self.__align.get(field, '<'),
                                         width)
            line_width += width + 2
        return line_width, pattern

    def __check_fields(self, row, fields):
        wrong = []
        for field in fields:
            if field not in row:
                wrong.append(field)
        if wrong:
            raise ValueError('Cannot build table, found unknown field(s): %s'
                             % wrong)

    def build(self, *seq):
        """Return list of lines to print out.

        :param seq: sequence of fields
        :return: list
        """
        lines = [self.__title] if self.__title else []
        if not self.__rows:
            lines.append('empty')
            return lines

        width, pattern = self.__build_pattern(seq)
        sep_line = '-' * width
        lines.extend([sep_line, pattern.format(**self.__headers), sep_line])
        for row in self.__rows:
            if type(row) is str and row == '-':
                lines.append(sep_line)
                continue
            self.__check_fields(row, seq)
            lines.append(pattern.format(**row))
        lines.append(sep_line)
        return lines
