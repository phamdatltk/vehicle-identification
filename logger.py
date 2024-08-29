import os
import logging as log
from colorlog import ColoredFormatter

def logger_handler():
    """
    ## logger_handler

    Returns the logger handler

    **Returns:** A logger handler
    """
    # logging formatter
    formatter = ColoredFormatter(
        "{green}{asctime}{reset} :: {bold_purple}{name:^13}{reset} :: {log_color}{levelname:^8}{reset} :: {bold_white}{message}",
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            "INFO": "bold_cyan",
            "DEBUG": "bold_yellow",
            "WARNING": "bold_red,fg_thin_yellow",
            "ERROR": "bold_red",
            "CRITICAL": "bold_red,bg_white",
        },
        style="{",
    )
    # check if VIDGEAR_LOGFILE defined
    file_mode = os.environ.get("VEHICLE_IDENTIFICATION_LOGFILE", False)
    # define handler
    handler = log.StreamHandler()
    if file_mode and isinstance(file_mode, str):
        file_path = os.path.abspath(file_mode)
        if (os.name == "nt" or os.access in os.supports_effective_ids) and os.access(
            os.path.dirname(file_path), os.W_OK
        ):
            file_path = (
                os.path.join(file_path, "vidgear.log")
                if os.path.isdir(file_path)
                else file_path
            )
            handler = log.FileHandler(file_path, mode="a")
            formatter = log.Formatter(
                "{asctime} :: {name} :: {levelname} :: {message}",
                datefmt="%H:%M:%S",
                style="{",
            )

    handler.setFormatter(formatter)
    return handler

def GetLogger(name:str, level:int=log.DEBUG):
    logger = log.getLogger(name)
    logger.propagate = False
    logger.addHandler(logger_handler())
    logger.setLevel(level)
    return logger