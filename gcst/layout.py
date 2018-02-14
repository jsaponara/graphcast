
from gcst.dataTypes import (Pane, DayDate, Clouds, PrecipAmt,
        PrecipProb, PrecipMaxProb, Temp, Weather)

# first layout entry is top pane, etc
layout = [
    Pane([DayDate, Clouds], 'clouds'),
    Pane([PrecipAmt, PrecipProb, PrecipMaxProb], 'storms'),
    Pane([Temp], 'temp'),
]

