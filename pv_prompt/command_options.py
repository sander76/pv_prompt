class CommandOption:
    def __init__(self, key, text):
        self.key = key
        self.text = text


class CommandOptions:
    def __init__(self, *commands):
        self._commands = list(commands)
        self._col_width = 15
        self._no_of_cols = 4
        self._col_format_string = '{:<' + str(self._col_width) + '}'
        self._list_format = self._no_of_cols * self._col_format_string
        self._print_commands = []
        self._print_options()

    def append(self, command_option: CommandOption):
        if self.is_valid(command_option):
            self._commands.append(command_option)
        else:
            pass

    def is_valid(self, command_option):
        return True

    def _print_options(self):
        _start = 0
        _line = ""
        for _command in self._commands:
            if _start < self._no_of_cols:
                _line = _line + self._col_format_string.format(_command.text)
            else:

                _line = ''
                _start = 0
        self._print_commands.append(_line)

    def print_options(self):
        for _ln in self._print_commands:
            print(_ln)

if __name__ == "__main__":
    NAV_SHADES = CommandOption('s', '(s)hades')
    NAV_ROOMS = CommandOption('r', '(r)ooms')

    MAIN_OPTIONS = CommandOptions(
        NAV_SHADES,
        NAV_ROOMS
    )
    MAIN_OPTIONS.print_options()
