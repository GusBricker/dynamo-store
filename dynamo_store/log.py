import logging
import logging.handlers
import logging.config

LOG_LEVEL = logging.DEBUG
LOG_CONFIG = { 
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': { 
        'standard': { 
            'format': '%(asctime)s [%(filename)s:%(lineno)s - %(levelname)8s] %(message)s'
        },
    },
    'handlers': { 
        'c': { 'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': logging.DEBUG}
    },
    'loggers': { 
        'dynamo-store': { 
            'handlers': ['c'],
            'level': logging.INFO,
            'propagate': True
        }
    } 
}

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('dynamo-store')