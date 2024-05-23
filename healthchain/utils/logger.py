import logging
from colorama import init, Fore, Back

init(autoreset=True)


class ColorFormatter(logging.Formatter):
    # Change this dictionary to suit your coloring needs!
    COLORS = {
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "CRITICAL": Fore.RED + Back.WHITE,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.asctime = color + self.formatTime(record, self.datefmt)
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)


def add_handlers(log):
    if len(log.handlers) == 0:
        formatter = ColorFormatter(
            "%(levelname)s: %(asctime)-10s [%(module)s]: %(message)s"
        )
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)

    return log
