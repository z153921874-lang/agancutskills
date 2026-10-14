"""Compare output times on a declared frame grid, including decimal JSON endpoints."""
import math
def frame_at(time,fps):
    if not math.isfinite(float(time)) or not math.isfinite(float(fps)) or fps<=0:raise ValueError('finite time and positive fps required')
    return round(time*fps)
def before(time,boundary,fps):return frame_at(time,fps)<frame_at(boundary,fps)
def contains(time,start,end,fps):
    a,b=frame_at(start,fps),frame_at(end,fps)
    if b<=a:raise ValueError('span must contain at least one output frame')
    return a<=frame_at(time,fps)<b
