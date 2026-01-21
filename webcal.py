import requests
import pdfplumber
import json
import time
import os
from ics import Calendar, Event
from datetime import datetime
import pytz

PDF_URL = "https://edr.state.fl.us/Content/calendar.pdf"
CAL_ID = os.getenv("CAL_ID", "default")
OUTPUT_FILE = f"/output/{CAL_ID}.ics"
OLLAMA_API = "http://ollama:11434/api"
MODEL = "llama3.2"

def log(msg):
	print(f"{[datetime.now().strftime('%H:%M:%S')]} {msg}", flush = True)
	
def pull_calendar():
	log('starting job')
	
	try:
		response = requests.get(PDF_URL, timeout = 15)
		with open("temp_pdf", 'wb') as f:
			f.write(response.content)
	except Exception as e:
		log(f"Download Failed: {e}")
		return None
		
	text_content = ""
	with pdfplumber.open("temp_pdf") as pdf:
		for page in pdf.pages:
			text_content = page.extract_text() + '\n'
			
	prompt = """
	Extract events from this text into a JSON object with key 'events'
	(list of {{title, date, time}})
	Date Format: DD-Month.
	Time Format: HH:MM AM/PM
	
	**TEXT**: {text_content[:3000]}
	"""
	
	payload = {
		"model": MODEL,
		"prompt": prompt,
		"format": "json",
		"stream": False,
		"keep_alive": 0
		}
		
	log("Ollama Working...")
	try:
		resp = requests.post("f{OLLAMA_API}/generate",
							 json = payload,
							 timeout = 300)
							 
		result = resp.json()
		event_list = json.loads(result['response']).get('events', [])
	except Exception as e:
		log(f"Ollama Failure: {e}")
		return None
	
	cal = Calendar()
	year = datetime.now().year
	
	for item in events_list:
		try:
			dt_str = f"{item['date']} {year} {item['time']}"
			dt = dattime.strptime(dt_str, "%d-%B %Y %I:%M %p")
			e = Event()
			e.name = item['title']
			e.begin = dt.replace(tzinfo = pytz.timezone('US/Eastern'))
			cal.events.add(e)
		except:
			continue
		
	with open(OUTPUT_FILE, "w") as f:
		f.writelines(cal.serialize())
	log("Calendar Updated")
	
if __name__ == "__main__":
	time.sleep(18)
	pull_calendar()
	
