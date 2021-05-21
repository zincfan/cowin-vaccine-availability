from typing import Optional
import logging
from fastapi import FastAPI, BackgroundTasks
import urllib.request
import json
import datetime
import time
from fastapi_utils.tasks import repeat_every

app = FastAPI()
logging.basicConfig(filename='app.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def write_notification(email='somegamil@gmail.com', message="Vaccine available"):
    writenow=1
    print("emails sent here")
    return 0


def somecode():
    district_id=265
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    today = datetime.date.today()
    datearg = today.strftime('%d-%m-%Y')
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district_id}&date={datearg}"
    headers = {'User-Agent': user_agent, }

    request = urllib.request.Request(
        url, None, headers)  # The assembled request
    response = urllib.request.urlopen(request)
    data = response.read()
    data = data.decode("utf-8")
    parsed = json.loads(data)
    for center in parsed['centers']:
        for session in center['sessions']:
            if session['min_age_limit'] < 45:
                #print(center['name'],
                      #session['available_capacity'], session['date'])
                if session['available_capacity'] != 0:
                    return 1
    return 0


@app.on_event("startup")
@repeat_every(seconds=20)  # 20 sec
def remove_expired_tokens_task():
    if somecode()==1:
        logging.warning('There was vaccine available')
        print("vaccine available")
        write_notification()

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

@app.get("/home")
async def startcheck(background_tasks: BackgroundTasks):
    logging.warning('This will get logged to a file')
    return {"message": "Notification sent in the background"}
