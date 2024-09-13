from python_weather import METRIC, IMPERIAL, Client

async def getweather(location: str = "Bello", unit: str = "C"):
    if unit == "C":
        newwnit = METRIC
    else:
        newwnit = IMPERIAL
    info = ""

    # declare the client. the measuring unit used defaults to the metric system (celcius, km/h, etc.)
    try:
        async with Client(unit=newwnit) as client:
            # fetch a weather forecast from a city
            weather = await client.get(location=location)
            unit = weather._CustomizableBase__unit.temperature
            # returns the current day's forecast temperature (int)
            info = f"Location: `{weather.location}, {weather.country}`.\n"
            info += f"Current temperature: `{weather.temperature}°{unit}`.\n"
            info += f'**{weather.description}**\n\n'
            # get the weather forecast for a few days

            for day in weather.daily_forecasts:
                info += f"\n{day.date:%A, %B %d, %Y}:\n\n"
                info += f"Temperatures:\n"
                info += f" - Highest: {day.highest_temperature}°{unit}\n"
                info += f" - Lowest: {day.lowest_temperature}°{unit}\n"
                info += f"Sunrise: {day.sunrise:%H:%M}\n"
                info += f"Sunset: {day.sunset:%H:%M}\n\n"

                info += f'Hourly:\n\n'
                for hour in day.hourly_forecasts:
                    info += f"- {hour.time:%I:%M %p}:\n"
                    info += f"{hour.temperature}°{unit}, {hour.description}\n"
                    info += f"Sunshine chance: {hour.chances_of_sunshine}, UV Level: {hour.ultraviolet}\n"
                    info += f"Humidity: {hour.humidity}, Rain chance: {hour.chances_of_rain}\n"
                    info += f"Wind speed: {hour.wind_speed}, Wind direction: {hour.wind_direction}\n\n"
                break

        return info

    except Exception as e:
        raise ConnectionError(e)