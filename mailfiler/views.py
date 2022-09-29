from urllib import response
from urllib.request import url2pathname
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from datetime import datetime, timedelta, timezone
from dateutil import tz, parser
from .forms import NewUserForm
from django.contrib.auth.forms import AuthenticationForm 
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, parsers
from .serializers import DropBoxSerializer
from mailfiler.auth_helper import get_sign_in_flow, get_token_from_code, store_user, remove_user_and_token, get_token, get_token_with_graph_user
from mailfiler.graph_helper import *
from .models import DropBox
from .models import GraphUser
from mailfiler.models import Mail
from mailfiler.models import Attachment
import json
import os
import io
import requests
import yaml

# Load the oauth_settings.yml file
stream = open('oauth_settings.yml', 'r')
settings = yaml.load(stream, yaml.SafeLoader)

# <HomeViewSnippet>
@csrf_exempt
def home(request):
  if(request.method == "POST"):
    validationToken = request.get_full_path().split('=')
    # If valdationToken for subscription arrives return it back
    if(len(validationToken) > 1):
      validationToken = validationToken[1].replace('%3a', ':')
      validationToken = validationToken.replace('+', ' ')
      return HttpResponse(validationToken, 'text/plain')
    else :
      # If notification of new message arrives
      data = json.loads(request.body)
      if('value' in data):
        for subscription in data['value']:
          graph_user_id = subscription['resource'].split('/')[1]
          graphUser = GraphUser.objects.get(graph_user_id=graph_user_id)
          token = get_token_with_graph_user(graph_user_id)
          mail = get_message(token, subscription['resource'])
          date = mail['receivedDateTime']
          date = parser.isoparse(date)
          print(date)
          if(settings['schema_id'] in get_schema_extension(token, mail['id'], settings['schema_id'])):
            return HttpResponse('mail already downloaded', 'text/plain')
          ### save mail ###
          # Upload mail html file
          newMail = Mail(immutableId = mail['id'], subject = mail['subject'], bodyPreview = mail['bodyPreview'], sender = mail['from']['emailAddress']['name'], receivedDateTime = date, user_id = graphUser.id)
          # Save mail reference to database
          newMail.save()
          title = mail['id'][len(mail['id']) - 25 : len(mail['id'])]
          
          with open(r'C:\demos\%s.html' % title, 'w+', encoding='utf-8') as fp:
            # write mails into html file
            line = mail['body']
            line = line['content']
            fp.write(line)
            fp.close()
          
          with open(r'C:\demos\%s.html' % title, 'rb') as fp:
            # post file to s3 bucket
            url = 'http://localhost:8000/accounts/'
            jsonObj = {'title': title}
            fileObj = {'document' : fp}

            x = requests.post(url, data = jsonObj, files = fileObj)
            add_schema_extension(token, mail['id'], settings['schema_id'])

            # delete html file
            fp.close()
            if(os.path.exists(r'C:\demos\%s.html' % title)):
              os.remove(r'C:\demos\%s.html' % title)

          # Upload attachment files
          attachment_list = get_attachment_list(
            token,
            mail['id'])
          if 'value' in attachment_list:
            attachment_list = attachment_list['value']
            for attach in attachment_list:
              newAttach = Attachment(immutableId = attach['id'], name = attach['name'], contentType = attach['contentType'], size= attach['size'], mail_id = newMail.id)
              newAttach.save()
              title = attach['id']
              title = title[len(title) - 25 : len(title)]
              typeStr = attach["name"][len(attach["name"]) - 4:len(attach["name"])]
              attach['name'] = attach['name'][0 : (21, len(attach['name']) - 4)[len(attach['name']) - 4 < 21]]
              attach['name'] = f'{attach["name"]}{typeStr}'
              attach_raw_content = get_attachment_raw_content(token, mail['id'], attach['id'])
              toread = io.BytesIO()
              toread.write(attach_raw_content)
              with open(r'C:\demos\%s' % attach['name'], 'wb') as fp:
                # write attachment files
                fp.write(toread.getbuffer())
                fp.close()
              
              with open(r'C:\demos\%s' % attach['name'], 'rb') as fp:
                # post attachment file to s3 bucket
                url = 'http://localhost:8000/accounts/'
                jsonObj = {'title': title}
                fileObj = {'document' : fp}

                x = requests.post(url, data = jsonObj, files = fileObj)
                print('attachresponse', x.text)
                # delete attachment file
                fp.close()
                if(os.path.exists(r'C:\demos\%s' % attach['name'])):
                  os.remove(r'C:\demos\%s' % attach['name'])
          
          return HttpResponse('mail downloaded', 'text/plain')

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

  schema_extension = is_schema_extension_defined(token, settings['schema_id'])
  if('value' in schema_extension):
    print(schema_extension['value'])
  else:
    print(schema_extension)
    # response = define_schema_extension(token)
    # print(response.text)

  mails = get_inbox(
    token,
    user['timeZone'])

  # if response arrived successufuly
  if 'value' in mails:
    downloaded_mail_idx = []
    mails = mails['value']
    # iterate mails and get attachment_list
    for idx, mail in enumerate(mails):
      # check if the mail is already downloaded
      if(settings['schema_id'] in get_schema_extension(token, mail['id'], settings['schema_id'])):
        downloaded_mail_idx.append(idx)
        continue
      # fetch attachments
      attachment_list = get_attachment_list(
        token,
        mail['id'])
      if 'value' in attachment_list:
        attachment_list = attachment_list['value']
        mail['attachment_list'] = attachment_list
    # del downloaded mails
    offset = 0
    for idx in downloaded_mail_idx:
      del mails[idx - offset]
      offset += 1

    context['mails'] = mails
    context['jsonMails'] = json.dumps(mails)

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
  graphUser = GraphUser.objects.get(graph_user_id=request.session.get('graphUser')['graph_user_id'])
  if request.method == 'POST':
    mails = json.loads(request.POST['mails'])
    token = get_token(request)

    for mail in mails:
      # Upload mail html file
      newMail = Mail(immutableId = mail['immutableId'], subject = mail['subject'], bodyPreview = mail['bodyPreview'], sender = mail['sender'], receivedDateTime = mail['receivedDateTime'], user_id = graphUser.id)
      # Save mail reference to database
      newMail.save()
      title = mail['immutableId'][len(mail['immutableId']) - 25 : len(mail['immutableId'])]
      
      with open(r'C:\demos\%s.html' % title, 'w+', encoding='utf-8') as fp:
        # write mails into html file
        line = eval(mail['body'])
        line = line['content']
        fp.write(line)
        fp.close()
      
      with open(r'C:\demos\%s.html' % title, 'rb') as fp:
        # post file to s3 bucket
        url = 'http://localhost:8000/accounts/'
        jsonObj = {'title': title}
        fileObj = {'document' : fp}

        x = requests.post(url, data = jsonObj, files = fileObj)
        add_schema_extension(token, mail['immutableId'], settings['schema_id'])

        # delete html file
        fp.close()
        if(os.path.exists(r'C:\demos\%s.html' % title)):
          os.remove(r'C:\demos\%s.html' % title)

      # Upload attachment files
      if 'attachments' in mail:
        for attach in mail['attachments']:
          newAttach = Attachment(immutableId = attach['id'], name = attach['name'], contentType = attach['contentType'], size= attach['size'], mail_id = newMail.id)
          newAttach.save()
          title = attach['id']
          title = title[len(title) - 25 : len(title)]
          typeStr = attach["name"][len(attach["name"]) - 4:len(attach["name"])]
          attach['name'] = attach['name'][0 : (21, len(attach['name']) - 4)[len(attach['name']) - 4 < 21]]
          attach['name'] = f'{attach["name"]}{typeStr}'
          attach_raw_content = get_attachment_raw_content(token, mail['immutableId'], attach['id'])
          toread = io.BytesIO()
          toread.write(attach_raw_content)
          with open(r'C:\demos\%s' % attach['name'], 'wb') as fp:
            # write attachment files
            fp.write(toread.getbuffer())
            fp.close()
          
          with open(r'C:\demos\%s' % attach['name'], 'rb') as fp:
            # post attachment file to s3 bucket
            url = 'http://localhost:8000/accounts/'
            jsonObj = {'title': title}
            fileObj = {'document' : fp}

            x = requests.post(url, data = jsonObj, files = fileObj)

            # delete attachment file
            fp.close()
            if(os.path.exists(r'C:\demos\%s' % attach['name'])):
              os.remove(r'C:\demos\%s' % attach['name'])

    return HttpResponse('Mails Saved Successfuly')
  
  # Render savedMails.html
  context = initialize_context(request)
  url = 'http://localhost:8000/accounts/'

  files = requests.get(url)
  files = json.loads(files.text)
  mails = list(graphUser.mail_set.all())
  dictMails = []
  # fetch only logged-in graphUser's mails
  for idx, mail in enumerate(mails):
    if(mail.user_id != graphUser.id):
      del mails[idx]

  for mail in mails:
    immutableId = mail.immutableId
    immutableId = immutableId[len(immutableId) - 25 : len(immutableId)]
    filteredFile = list(filter(lambda file: file['title'] == immutableId, files))[0]
    mail.url = filteredFile['document']
    mail.immutableId = immutableId[len(immutableId) - 8 : len(immutableId)]
    attachments = mail.attachment_set.all()
    mail.attachments = attachments
    dictAttachments = []
    for attachment in attachments:
      immutableId = attachment.immutableId[len(attachment.immutableId) - 25 : len(attachment.immutableId)]
      filteredFile = list(filter(lambda file: file['title'] == immutableId, files))
      filteredFile = ([], filteredFile[0])[len(filteredFile)]
      attachment.url = filteredFile['document']
      dictAttachments.append({
        'immutableId' : attachment.immutableId,
        'name' : attachment.name,
        'contentType' : attachment.contentType,
        'size' : attachment.size,
        'url' : attachment.url
      })
    mail = {
      'bodyPreview' : mail.bodyPreview,
      'subject' : mail.subject,
      'sender' : mail.sender,
      'receivedDateTime' : mail.receivedDateTime.strftime("%m/%d/%Y, %H:%M:%S"),
      'immutableId' : mail.immutableId,
      'url' : mail.url,
      'attachments' : dictAttachments
    }
    dictMails.append(mail)

  context['mails'] = mails
  context['jsonMails'] = json.dumps(dictMails)

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

# </Notify>
def notify(request):
  print('validation request arrived')
  if(request.method == 'POST'):
    print(request.POST)
# </Notify>