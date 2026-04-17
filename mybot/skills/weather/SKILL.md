---
name: weather
description: Get current weather and forecasts. Use when user asks about weather.
---
# Weather

Free weather via wttr.in (no API key):

\```bash

# 简洁格式

curl -s "wttr.in/CityName?format=3"

# 详细格式

curl -s "wttr.in/CityName?format=%l:+%c+%t+%h+%w"
\```

URL-encode spaces: `wttr.in/New+York`
