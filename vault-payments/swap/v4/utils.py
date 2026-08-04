def utc_interval(weeks=0, days=0, hours=0, minutes=0, seconds=0):
    utc_sec = 1
    utc_min = utc_sec * 60 
    utc_hour = utc_min * 60 
    utc_day = utc_hour * 24
    utc_week = utc_day * 7

    ret = 0
    if weeks:
        ret += utc_week * weeks
    if days:
        ret += utc_day * days
    if hours:
        ret += utc_hour * hours
    if minutes:
        ret += utc_min * minutes
    if seconds:
        ret += utc_sec * seconds

    return ret