# cowin-vaccine-availability
This web app runs a server side script every few seconds to check vaccine availability under 45 in cowin portal.
Install modules through pip3,
```
  pip3 install -r requirements.txt
```
  
Do edit the district_id variable in ```somecode()``` function to your district id. Intercepting requests in cowin.gov.in website when you search the vaccine availability in homepage will give you the district id.

Then run the server side script as
```
  uvicorn servercode:app
 ```
  
You can also run this on heroku using the given procfile. Heroku disbales the dyno when it is inactive. So it will not run all the time.

You need to write your own notification function in ```write_notification() ```function however to get the notification. If you are running locally, a sound alert can be given. A cloud hoisting may require email or sms notification.
