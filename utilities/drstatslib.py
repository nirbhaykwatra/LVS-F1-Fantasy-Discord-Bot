# A library for calculating driver statistics requiring more data manipulation than usual.
# For example, calculating driver podiums, teammate battles, positions gained/lost, etc.
import settings
from utilities import fastf1util as f1

logger = settings.create_logger('driver-stats')
