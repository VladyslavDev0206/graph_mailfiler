from urllib.request import url2pathname
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from datetime import datetime, timedelta
from dateutil import tz, parser
from .forms import NewUserForm
from django.contrib.auth.forms import AuthenticationForm 
from rest_framework import viewsets, parsers
from .models import DropBox
from .serializers import DropBoxSerializer
from mailfiler.auth_helper import get_sign_in_flow, get_token_from_code, store_user, remove_user_and_token, get_token
from mailfiler.graph_helper import *
from mailfiler.models import Mail
import json
import os
import requests

# <HomeViewSnippet>
def home(request):
  context = initialize_context(request)

  return render(request, 'mailfiler/home.html', context)
# </HomeViewSnippet>

# <InitializeContextSnippet>
def initialize_context(request):
  context = {}

  # Check for any errors in the session
  error = request.session.pop('flash_error', None)

  if error != None:
    context['errors'] = []
    context['errors'].append(error)

  # Check for user in the session
  context['graphUser'] = request.session.get('graphUser', {'is_authenticated': False})
  return context
# </InitializeContextSnippet>

# <SignInViewSnippet>
def connect(request):
  # Get the sign-in flow
  flow = get_sign_in_flow()
  # Save the expected flow so we can use it in the callback
  try:
    request.session['auth_flow'] = flow
  except Exception as e:
    print(e)
  # Redirect to the Azure sign-in page
  return HttpResponseRedirect(flow['auth_uri'])
# </SignInViewSnippet>

# <SignOutViewSnippet>
def disconnect(request):
  # Clear out the user and token
  remove_user_and_token(request)

  return HttpResponseRedirect(reverse('home'))
# </SignOutViewSnippet>

# <CallbackViewSnippet>
def callback(request):
  # Make the token request
  result = get_token_from_code(request)

  #Get the user's profile
  # print(result)
  user = get_user(result['access_token'])

  # Store user
  store_user(request, user)
  return HttpResponseRedirect(reverse('home'))
# </CallbackViewSnippet>

# <CalendarViewSnippet>
def calendar(request):
  context = initialize_context(request)
  user = context['graphUser']

  # Load the user's time zone
  # Microsoft Graph can return the user's time zone as either
  # a Windows time zone name or an IANA time zone identifier
  # Python datetime requires IANA, so convert Windows to IANA
  time_zone = get_iana_from_windows(user['timeZone'])
  tz_info = tz.gettz(time_zone)

  # Get midnight today in user's time zone
  today = datetime.now(tz_info).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0)

  # Based on today, get the start of the week (Sunday)
  if (today.weekday() != 6):
    start = today - timedelta(days=today.isoweekday())
  else:
    start = today

  end = start + timedelta(days=7)

  token = get_token(request)

  events = get_calendar_events(
    token,
    start.isoformat(timespec='seconds'),
    end.isoformat(timespec='seconds'),
    user['timeZone'])

  if events:
    # Convert the ISO 8601 date times to a datetime object
    # This allows the Django template to format the value nicely
    for event in events['value']:
      event['start']['dateTime'] = parser.parse(event['start']['dateTime'])
      event['end']['dateTime'] = parser.parse(event['end']['dateTime'])

    context['events'] = events['value']

  return render(request, 'mailfiler/calendar.html', context)
# </CalendarViewSnippet>

# <MailViewSnippet>
def mail(request):
  context = initialize_context(request)
  user = context['graphUser']

  token = get_token(request)

  mails = get_inbox(
    token,
    user['timeZone'])
  if 'value' in mails:
    # Convert the ISO 8601 date times to a datetime object
    # This allows the Django template to format the value nicely
    # for mail in mails['value']:
      # event['start']['dateTime'] = parser.parse(event['start']['dateTime'])
      # event['end']['dateTime'] = parser.parse(event['end']['dateTime'])

    context['mails'] = mails['value']

  return render(request, 'mailfiler/inbox.html', context)
# </MailViewSnippet>

# <NewEventViewSnippet>
def newevent(request):
  context = initialize_context(request)
  user = context['graphUser']

  if request.method == 'POST':
    # Validate the form values
    # Required values
    if (not request.POST['ev-subject']) or \
       (not request.POST['ev-start']) or \
       (not request.POST['ev-end']):
      context['errors'] = [
        { 'message': 'Invalid values', 'debug': 'The subject, start, and end fields are required.'}
      ]
      return render(request, 'mailfiler/newevent.html', context)

    attendees = None
    if request.POST['ev-attendees']:
      attendees = request.POST['ev-attendees'].split(';')
    body = request.POST['ev-body']

    # Create the event
    token = get_token(request)

    create_event(
      token,
      request.POST['ev-subject'],
      request.POST['ev-start'],
      request.POST['ev-end'],
      attendees,
      request.POST['ev-body'],
      user['timeZone'])

    # Redirect back to calendar view
    return HttpResponseRedirect(reverse('calendar'))
  else:
    # Render the form
    return render(request, 'mailfiler/newevent.html', context)
  print('hello')
# </NewEventViewSnippet>

# </MailSaveSnippet>
def mailSave(request):
  if request.method == 'POST':
    mails = json.loads(request.POST['mails'])

    for mail in mails:
      newMail = Mail(immutableId = mail['immutableId'], subject = mail['subject'], bodyPreview = mail['bodyPreview'], sender = mail['sender'], receivedDateTime = mail['receivedDateTime'], user_id = request.user.id)
      newMail.save()
      title = mail['immutableId'][len(mail['immutableId']) - 25 : len(mail['immutableId'])]
      with open(r'C:\demos\%s.html' % title, 'w+') as fp:
        # write mails into html file
        line = eval(mail['body'])
        line = line['content']
        print(type(line))
        fp.write(line)
        fp.close()
        print('file %s writed' % title)
      
      with open(r'C:\demos\%s.html' % title, 'rb') as fp:
        # post file to s3 bucket
        url = 'http://localhost:8000/accounts/'
        jsonObj = {'title': title}
        fileObj = {'document' : fp}

        x = requests.post(url, data = jsonObj, files = fileObj)

        # delete html file
        fp.close()
        if(os.path.exists(r'C:\demos\%s.html' % title)):
          os.remove(r'C:\demos\%s.html' % title)
          print('file deleted %s' % title)
    return HttpResponse('Mails Saved Successfuly')
  
  # Render savedMails.html
  context = initialize_context(request)
  user = request.user

  url = 'http://localhost:8000/accounts/'

  files = requests.get(url)
  files = json.loads(files.text)
  print(files)
  mails = list(user.mail_set.all())
  for mail in mails:
    immutableId = mail.immutableId
    immutableId = immutableId[len(immutableId) - 25 : len(immutableId)]
    filteredFile = list(filter(lambda file: file['title'] == immutableId, files))[0]
    mail.url = filteredFile['document']
    mail.immutableId = immutableId[len(immutableId) - 8 : len(immutableId)]

  context['mails'] = mails

  return render(request, 'mailfiler/savedMails.html', context)
# </MailSaveSnippet>

# </RegisterViewSnippet>
def register_request(request):
	if request.method == "POST":
		form = NewUserForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			messages.success(request, "Registration successful." )
			return redirect("home")
		messages.error(request, "Unsuccessful registration. Invalid information.")
	form = NewUserForm()
	return render (request=request, template_name="mailfiler/register.html", context={"register_form":form})
# </RegisterViewSnippet>

# </LoginViewSnippet>
def login_request(request):
	if request.method == "POST":
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			username = form.cleaned_data.get('username')
			password = form.cleaned_data.get('password')
			user = authenticate(username=username, password=password)
			if user is not None:
				login(request, user)
				messages.info(request, f"You are now logged in as {username}.")
				return redirect("home")
			else:
				messages.error(request,"Invalid username or password.")
		else:
			messages.error(request,"Invalid username or password.")
	form = AuthenticationForm()
	return render(request=request, template_name="mailfiler/login.html", context={"login_form":form})
  # </LoginViewSnippet>

  
# </LogoutViewSnippet>
def logout_request(request):
	logout(request)
	messages.info(request, "You have successfully logged out.") 
	return redirect("home")
# </LogoutViewSnippet>

# </DropBoxViewSet>
class DropBoxViewset(viewsets.ModelViewSet):
 
    queryset = DropBox.objects.all()
    serializer_class = DropBoxSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    http_method_names = ['get', 'post', 'patch', 'delete']
# </DropBoxViewSet>