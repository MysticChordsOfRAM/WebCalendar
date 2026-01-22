import json
import time
import httpx
import pytz
import os
from typing import List
from ics import Calendar, Event
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from random import randint
from pydantic import BaseModel, Field

PDF_URL = "https://edr.state.fl.us/Content/calendar.pdf"
CAL_ID = os.getenv("CAL_ID", "default")
OUTPUT_FILE = f"/output/{CAL_ID}.ics"
API_KEY = os.getenv('GEMINI_KEY')
MODEL_NAME = 'gemini-3-flash-preview'

class CalendarEvent(BaseModel):
    title: str = Field(description="The name of the meeting or event")
    date: str = Field(description="The date in format DD-Month (e.g. 12-January)")
    time: str = Field(description="The start time in format HH:MM AM/PM (e.g. 1:30 PM)")

class CalendarResponse(BaseModel):
    events: List[CalendarEvent]

def log(msg):
	print(f"{[datetime.now().strftime('%H:%M:%S')]} {msg}", flush = True)
	
def pull_calendar():
	log('starting job')
	
	try:
		doc_data = httpx.get(PDF_URL).content
		log(f"Calendar is {len(doc_data)} bytes today")
	except Exception as e:
		log(f"Download Failed: {e}")
		return None
		
	client = genai.Client(api_key = API_KEY)
			
	prompt = """
    This PDF contains a schedule of meetings for the Florida Economic Estimating Conference.
    The user wants to parse this schedule into a list of events. Please take each event on
    this schedule and exctract the event title, event date, and event start time. Return
    a JSON list of events matching the provided schema.
    
    If a year is not explicitly mentioned, assume the current year (2026).
    
    Ignore page headers/footers.
    """
		
	log("Gemini Working...")
	try:
		response = client.models.generate_content(
            model = MODEL_NAME,
            contents = [
				types.Part.from_bytes(
					data = doc_data,
					mime_type = 'application/pdf'
				), 
				prompt
			],
            config = {"response_mime_type": "application/json",
                      "response_json_schema": CalendarResponse.model_json_schema()}
			)
        
		log("Received Response")
		clean_text = response.text.replace("```json", "").replace("```", "").strip()
		data = json.loads(clean_text)		 
		event_list = data.get('events', [])
		log(f"Gemini Found {len(event_list)} events!")
	except Exception as e:
		log(f"Gemini Failure: {e}")
		time.sleep(10)
		log(f"Raw Response: {response.text}")
		return None
		
	parsed_events = []
	current_year = datetime.now().year
	timezone = pytz.timezone('US/Eastern')
	
	for item in event_list:
		DATE = item['date']
		TIME = item['time']
		TITLE = item['title']
		
		try:
			dt_str = f"{DATE} {current_year} {TIME}"
			dt = datetime.strptime(dt_str, "%d-%B %Y %I:%M %p")
			dt = dt.replace(tzinfo = timezone)
			
			parsed_events.append({"title": TITLE,
								  "start": dt})
		except Exception as e:
			log(f"Bad Data Found {e}")
			
	parsed_events.sort(key = lambda x: x['start'])
			
	cal = Calendar()
	
	for dex in range(len(parsed_events)):
		log(f"Creating Event {dex}...")
		
		citem = parsed_events[dex]
		start_time = citem["start"]
		
		limit_5h = start_time + timedelta(hours = 5)
		candidates = [limit_5h]
		
		limit_7pm = start_time.replace(hour = 19, minute = 0, second = 0)
		if limit_7pm > start_time:
			candidates.append(limit_7pm)
			
		if dex + 1 < len(parsed_events):
			next_event = parsed_events[dex + 1]
			next_start = next_event['start']
			
			if next_start.date() == start_time.date():
				if next_start > start_time:
					candidates.append(next_start)
					
		end_time = min(candidates)
		
		duration = end_time - start_time
		
		if duration < timedelta(minutes = 15):
			duration = timedelta(minutes = 15)
			
		e = Event()
		e.name = citem['title']
		e.begin = start_time
		e.end = start_time + duration
		cal.events.add(e)

	with open(OUTPUT_FILE, "w") as f:
		f.writelines(cal.serialize())
	log("Calendar Updated")
	
if __name__ == "__main__":
	time.sleep(randint(7, 19))
	pull_calendar()
