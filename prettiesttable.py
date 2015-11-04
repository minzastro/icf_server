#!/usr/bin/python
"""
Created on Tue Jan 20 16:41:39 2015
@author: mints
"""
from prettytable import PrettyTable, ALL, FRAME
import sys
py3k = sys.version_info[0] >= 3
if py3k and sys.version_info[1] >= 2:
    from html import escape
else:
    from cgi import escape


def from_db_cursor(cursor, **kwargs):
    if cursor.description:
        table = PrettiestTable(**kwargs)
        table.field_names = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            table.add_row(row)
        return table


class PrettiestTable(PrettyTable):
    """
    Extend prettytable with Unescape.
    """
    def __init__(self, field_names=None, **kwargs):
        PrettyTable.__init__(self, field_names, **kwargs)
        self._options.append('unescape')
        if 'unescape' in kwargs:
            self.self._validate_all_field_names('unescape', kwargs['unescape'])
        else:
            kwargs['unescape'] = None
        self._unescape = kwargs['unescape'] or []

    def _validate_option(self, option, val):
        if option == 'unescape':
            self._validate_all_field_names('unescape', val)
        else:
            super(PrettiestTable, self)._validate_option(option, val)

    def _get_unescape(self):
        return self._unescape

    def _set_unescape(self, val):
        self._validate_option("unescape", val)
        self._unescape = val
    unescape = property(_get_unescape, _set_unescape)

    def _format_value(self, field, value):
        if isinstance(value, int) and field in self._int_format:
            value = self._unicode(("%%%s" % self._int_format[field]) % value)
        elif isinstance(value, float) and field in self._float_format:
            value = self._unicode(("%%%s" % self._float_format[field]) % value)
        return self._unicode(value)

    def _get_html_header(self, options, lpad=None, rpad=''):
        lines = []
        if options["xhtml"]:
            linebreak = "<br/>"
        else:
            linebreak = "<br>"
        # Headers
        if options["header"]:
            lines.append("    <thead>")
            lines.append("    <tr>")
            for field in self._field_names:
                if options["fields"] and field not in options["fields"]:
                    continue
                if lpad is None:
                    lines.append("        <th id='%s'>%s</th>" % (field, escape(field).replace("\n", linebreak)))
                else:
                    lines.append("        <th style=\"padding-left: %dem; padding-right: %dem; text-align: center\">%s</th>" % (lpad, rpad, escape(field).replace("\n", linebreak)))
            lines.append("    </tr>")
            lines.append("    </thead>")
        return lines

    def _get_simple_html_string(self, options):
        lines = []
        if options["xhtml"]:
            linebreak = "<br/>"
        else:
            linebreak = "<br>"
        open_tag = []
        open_tag.append("<table")
        if options["attributes"]:
            for attr_name in options["attributes"]:
                open_tag.append(" %s=\"%s\"" % (attr_name, options["attributes"][attr_name]))
        open_tag.append(">")
        lines.append("".join(open_tag))
        lines.extend(self._get_html_header(options))
        # Data
        rows = self._get_rows(options)
        formatted_rows = self._format_rows(rows, options)
        for row in formatted_rows:
            lines.append("    <tr>")
            for field, datum in zip(self._field_names, row):
                if options["fields"] and field not in options["fields"]:
                    continue
                if options['unescape'] and field in options['unescape']:
                    lines.append("        <td>%s</td>" % datum.replace("\n", linebreak))
                else:
                    lines.append("        <td>%s</td>" % escape(datum).replace("\n", linebreak))
            lines.append("    </tr>")

        lines.append("</table>")

        return self._unicode("\n").join(lines)

    def _get_formatted_html_string(self, options):

        lines = []
        lpad, rpad = self._get_padding_widths(options)
        if options["xhtml"]:
            linebreak = "<br/>"
        else:
            linebreak = "<br>"

        open_tag = []
        open_tag.append("<table")
        if options["border"]:
            if options["hrules"] == ALL and options["vrules"] == ALL:
                open_tag.append(" frame=\"box\" rules=\"all\"")
            elif options["hrules"] == FRAME and options["vrules"] == FRAME:
                open_tag.append(" frame=\"box\"")
            elif options["hrules"] == FRAME and options["vrules"] == ALL:
                open_tag.append(" frame=\"box\" rules=\"cols\"")
            elif options["hrules"] == FRAME:
                open_tag.append(" frame=\"hsides\"")
            elif options["hrules"] == ALL:
                open_tag.append(" frame=\"hsides\" rules=\"rows\"")
            elif options["vrules"] == FRAME:
                open_tag.append(" frame=\"vsides\"")
            elif options["vrules"] == ALL:
                open_tag.append(" frame=\"vsides\" rules=\"cols\"")
        if options["attributes"]:
            for attr_name in options["attributes"]:
                open_tag.append(" %s=\"%s\"" % (attr_name, options["attributes"][attr_name]))
        open_tag.append(">")
        lines.append("".join(open_tag))
        lines.extend(self._get_html_header(options, lpad, rpad))
        # Data
        rows = self._get_rows(options)
        formatted_rows = self._format_rows(rows, options)
        aligns = []
        valigns = []
        for field in self._field_names:
            aligns.append({ "l" : "left", "r" : "right", "c" : "center" }[self._align[field]])
            valigns.append({"t" : "top", "m" : "middle", "b" : "bottom"}[self._valign[field]])
        for row in formatted_rows:
            lines.append("    <tr>")
            for field, datum, align, valign in zip(self._field_names, row, aligns, valigns):
                if options["fields"] and field not in options["fields"]:
                    continue
                lines.append("        <td style=\"padding-left: %dem; padding-right: %dem; text-align: %s; vertical-align: %s\">%s</td>" % (lpad, rpad, align, valign, escape(datum).replace("\n", linebreak)))
            lines.append("    </tr>")
        lines.append("</table>")
        return self._unicode("\n").join(lines)