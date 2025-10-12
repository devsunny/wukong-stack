import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Union

class CustomJsonEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that handles datetime.date and datetime.datetime objects 
    by converting them to ISO 8601 strings.
    Other non-serializable objects are converted to a dictionary representation.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        try:
            # Attempt to convert other non-serializable objects to a dictionary
            return obj.__dict__
        except AttributeError:
            # If __dict__ is not available, fall back to the default JSONEncoder behavior
            return super().default(obj)