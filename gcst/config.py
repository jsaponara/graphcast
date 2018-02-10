
from gcst.dataTypes import DayDate, Clouds, PrecipAmt, PrecipProb, PrecipMaxProb, Temp

# first entry is top pane, etc
layout = [
    [DayDate, Clouds],
    [PrecipAmt, PrecipProb, PrecipMaxProb, ],
    [Temp],
    [Temp],
]
