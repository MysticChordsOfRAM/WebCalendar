import requests
import json
import time
import httpx
import pytz
import os
from typing import List
from ics import Calendar, Event
from datetime import datetime
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
		time.sleep(10)
		clean_text = response.text.replace("```json", "").replace("```", "").strip()
		data = json.loads(clean_text)		 
		event_list = data.get('events', [])
		log(f"Gemini Found {len(event_list)} events!")
	except Exception as e:
		log(f"Gemini Failure: {e}")
		time.sleep(10)
		log(f"Raw Response: {response.text}")
		return None
	
	cal = Calendar()
	year = datetime.now().year
	
	for item in event_list:
		log(f"Creating Event {item['title']}...")
		try:
			dt_str = f"{item['date']} {year} {item['time']}"
			dt = datetime.strptime(dt_str, "%d-%B %Y %I:%M %p")
			e = Event()
			e.name = item['title']
			e.begin = dt.replace(tzinfo = pytz.timezone('US/Eastern'))
			cal.events.add(e)
		except:
			continue
		
	with open(OUTPUT_FILE, "w") as f:
		f.writelines(cal.serialize())
	log("Calendar Updated")
	
	try:
		client.files.delete(name = sample_file.name)
	except:
		pass
	
if __name__ == "__main__":
	time.sleep(randint(7, 19))
	pull_calendar()
	
