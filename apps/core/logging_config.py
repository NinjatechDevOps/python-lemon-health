"""
Logging configuration for the Lemon Health application
"""
import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path

def setup_logging(environment: str = "development"):
    """
    Setup logging configuration for the application
    
    Args:
        environment: The environment (development, staging, production)
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Define log file paths
    log_file = logs_dir / f"lemon_health_{environment}.log"
    error_log_file = logs_dir / f"lemon_health_{environment}_errors.log"
    
    # Configure logging based on environment
    if environment == "production":
        # Production logging - minimal console output, detailed file logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                },
                "json": {
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(log_file),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": str(error_log_file),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
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
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
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
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(log_file),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 3
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
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
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
                "file": {
                    "class": "logging.FileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(log_file)
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