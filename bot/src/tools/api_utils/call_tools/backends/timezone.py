from aiohttp import ClientSession

async def get_current_time(timezone):
    url = f"http://worldtimeapi.org/api/timezone/{timezone}"
    
    async with ClientSession() as session:
        try:
            async with session.get(url) as response:
                # Check if the request was successful
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract the "datetime" value which includes the full date and time
                    current_time = data["datetime"]
                    
                    # Extract only the time in HH:MM:SS format
                    time = current_time.split("T")[1].split(".")[0]
                    
                    return f"The time in {timezone} is: {time}"
                else:
                    return "Timezone not found or incorrect."
        except Exception as e:
            return f"Error: {str(e)}"
