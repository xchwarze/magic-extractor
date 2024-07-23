import logging
from colorama import Fore, Style, init

# Initialize Colorama to make it work on Windows too
init()

class CustomFormatter(logging.Formatter):
    """Custom formatter to apply color codes to the logging output based on the level."""
    
    LOG_COLORS = {
        "DEBUG": Fore.YELLOW,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        log_fmt = f"{self.LOG_COLORS.get(record.levelname, Fore.WHITE)}%(asctime)s - %(levelname)s - %(message)s{Style.RESET_ALL}"
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logging(debug_mode=False):
    """Configure the logging system."""
    logging_level = logging.DEBUG if debug_mode else logging.INFO

    # Create console handler with the appropriate level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)
    console_handler.setFormatter(CustomFormatter())

    # Configure the root logger with the console handler
    logger = logging.getLogger()
    logger.setLevel(logging_level)
    logger.addHandler(console_handler)

    return logger
