import logging
import json

logger = logging.getLogger('default')


def convert_json_simple_to_dict(raw_json, allow_error=False):
    try:
        converted_stats = json.loads(raw_json)
    except Exception as exc:
        if allow_error:
            converted_stats = {"broken_json": raw_json}
        else:
            return "convert_json_stats_to_dict: Can't convert '{0}' to dictionary." \
                   " \nError message: {1}'".format(raw_json, exc)
    return converted_stats
