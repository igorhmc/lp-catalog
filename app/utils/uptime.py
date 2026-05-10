import time

_start_time = time.time()

def get_uptime_seconds():
    return int(time.time() - _start_time)

def get_uptime_human():
    secs = get_uptime_seconds()
    mins, sec = divmod(secs, 60)
    hrs, min_ = divmod(mins, 60)
    days, hr = divmod(hrs, 24)
    if days > 0:
        return f"{days}d {hr}h {min_}m"
    elif hr > 0:
        return f"{hr}h {min_}m"
    elif min_ > 0:
        return f"{min_}m {sec}s"
    else:
        return f"{sec}s"
