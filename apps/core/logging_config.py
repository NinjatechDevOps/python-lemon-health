"""
Logging configuration for the Lemon Health application
"""
import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
import pytz

# Custom formatter class to add both UTC and Indian time
class DualTimezoneFormatter(logging.Formatter):
    """Custom formatter that includes both UTC and Indian timezone"""
    
    def formatTime(self, record, datefmt=None):
        """Override formatTime to include both UTC and IST"""
        # Get UTC time
        utc_time = datetime.utcfromtimestamp(record.created).replace(tzinfo=pytz.UTC)
        
        # Convert to Indian timezone
        indian_tz = pytz.timezone('Asia/Kolkata')
        indian_time = utc_time.astimezone(indian_tz)
        
        # Format both times
        utc_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')
        ist_str = indian_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return f"[UTC: {utc_str} | IST: {ist_str}]"
    
    def format(self, record):
        """Format the log record with dual timezone"""
        # Store original datefmt
        original_datefmt = self.datefmt
        # Temporarily set datefmt to None to use our custom formatTime
        self.datefmt = None
        # Get the formatted time string
        record.asctime = self.formatTime(record)
        # Restore original datefmt
        self.datefmt = original_datefmt
        # Return the formatted message
        return super().format(record)

def setup_logging(environment: str = "development"):
    """
    Setup logging configuration for the application
    
    Args:
        environment: The environment (development, staging, production)
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("static/logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Commented out: Old log file naming without date
    # # Define log file paths
    # log_file = logs_dir / f"lemon_health_{environment}.log"
    # error_log_file = logs_dir / f"lemon_health_{environment}_errors.log"
    
    # Updated: Create date-based log file names using Indian timezone
    indian_tz = pytz.timezone('Asia/Kolkata')
    current_date = datetime.now(indian_tz).strftime('%Y-%m-%d')
    log_file = logs_dir / f"lemon_health_{environment}_{current_date}.log"
    error_log_file = logs_dir / f"lemon_health_{environment}_errors_{current_date}.log"
    
    # Configure logging based on environment
    if environment == "production":
        # Production logging - minimal console output, detailed file logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                # Commented out: Old formatter without dual timezone
                # "detailed": {
                #     "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                #     "datefmt": "%Y-%m-%d %H:%M:%S"
                # },
                # Updated: Using custom formatter class with dual timezone
                "detailed": {
                    "()": DualTimezoneFormatter,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                },
                # Commented out: Old JSON formatter without dual timezone
                # "json": {
                #     "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                #     "datefmt": "%Y-%m-%d %H:%M:%S"
                # }
                # Updated: JSON formatter with dual timezone
                "json": {
                    "()": DualTimezoneFormatter,
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                # Commented out: Old RotatingFileHandler without date-based rotation
                # "file": {
                #     "class": "logging.handlers.RotatingFileHandler",
                #     "level": "INFO",
                #     "formatter": "detailed",
                #     "filename": str(log_file),
                #     "maxBytes": 10485760,  # 10MB
                #     "backupCount": 5
                # },
                # Updated: Using TimedRotatingFileHandler for daily rotation
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(log_file),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30  # Keep 30 days of logs
                },
                # Commented out: Old error handler without date-based rotation
                # "error_file": {
                #     "class": "logging.handlers.RotatingFileHandler",
                #     "level": "ERROR",
                #     "formatter": "detailed",
                #     "filename": str(error_log_file),
                #     "maxBytes": 10485760,  # 10MB
                #     "backupCount": 5
                # }
                # Updated: Using TimedRotatingFileHandler for daily rotation
                "error_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": str(error_log_file),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30  # Keep 30 days of error logs
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": "INFO",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                },
                "apps.chat": {
                    "level": "INFO",
                    "handlers": ["file", "error_file"],
                    "propagate": False
                },
                "apps.auth": {
                    "level": "INFO",
                    "handlers": ["file", "error_file"],
                    "propagate": False
                },
                "apps.profile": {
                    "level": "INFO",
                    "handlers": ["file", "error_file"],
                    "propagate": False
                },
                "uvicorn": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                },
                "fastapi": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    elif environment == "staging":
        # Staging logging - moderate console output, detailed file logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                # Commented out: Old formatter without dual timezone
                # "detailed": {
                #     "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                #     "datefmt": "%Y-%m-%d %H:%M:%S"
                # },
                # Updated: Using custom formatter class with dual timezone
                "detailed": {
                    "()": DualTimezoneFormatter,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                # Commented out: Old RotatingFileHandler without date-based rotation
                # "file": {
                #     "class": "logging.handlers.RotatingFileHandler",
                #     "level": "DEBUG",
                #     "formatter": "detailed",
                #     "filename": str(log_file),
                #     "maxBytes": 10485760,  # 10MB
                #     "backupCount": 3
                # }
                # Updated: Using TimedRotatingFileHandler for daily rotation
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(log_file),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 15  # Keep 15 days of logs for staging
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "propagate": False
                },
                "apps.chat": {
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "propagate": False
                }
            }
        }
    else:
        # Development logging - verbose console output, basic file logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                # Commented out: Old formatter without dual timezone
                # "detailed": {
                #     "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                #     "datefmt": "%Y-%m-%d %H:%M:%S"
                # },
                # Updated: Using custom formatter class with dual timezone
                "detailed": {
                    "()": DualTimezoneFormatter,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
                },
                "simple": {
                    "format": "%(levelname)s - %(name)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                # Commented out: Old FileHandler without date-based rotation
                # "file": {
                #     "class": "logging.FileHandler",
                #     "level": "DEBUG",
                #     "formatter": "detailed",
                #     "filename": str(log_file)
                # }
                # Updated: Using TimedRotatingFileHandler for daily rotation in development
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(log_file),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 7  # Keep 7 days of logs for development
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "propagate": False
                },
                "apps.chat": {
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "propagate": False
                }
            }
        }
    
    # Apply the configuration
    logging.config.dictConfig(logging_config)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {environment} environment")
    logger.info(f"Log files: {log_file}, {error_log_file if environment == 'production' else 'N/A'}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name) 