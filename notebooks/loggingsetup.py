import os
import argparse
import logging

# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
log_file = f'{program_name}.log'

# Initial logging setup
# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format=('%(asctime)s:' + logging.BASIC_FORMAT),
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logging.info('Initial log message before parsing arguments')

# Set up argparse
parser = argparse.ArgumentParser(description='Example script')
parser.add_argument('--log', default='INFO', help='Set the logging level')
args = parser.parse_args()

# Override logging level based on argparse
logging.getLogger().setLevel(getattr(logging, args.log.upper(), None))

# Set up a logging filter
class MyFilter(logging.Filter):
    def filter(self, record):
        return 'specific_keyword' in record.msg or \
            record.levelno in {logging.INFO, logging.WARNING, logging.ERROR}

# Add the filter to the root logger
logging.getLogger().addFilter(MyFilter())

# Example usage
logging.debug('This is a debug message')
logging.info('This is an info message with specific_keyword')
logging.info('This is an info message')
logging.warning('This is a warning message')
logging.error('This is an error message')
logging.critical('This is a critical message')

logger = logging.getLogger(__name__)
logger.info('This is a message from the logger')
logger.info('This is a message with specific_keyword')
logger.debug('This is a debug message from the logger')
logger.error('This is an error message from the logger')
logger.critical('This is a critical message from the logger')
logger.warning('This is a warning message from the logger')
