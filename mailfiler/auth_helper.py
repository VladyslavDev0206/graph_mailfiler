# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <FirstCodeSnippet>
import yaml
import msal
import os
import time
import json
from .models import GraphUser
from .models import Connect
from .graph_helper import get_user

# Load the oauth_settings.yml file
stream = open('oauth_settings.yml', 'r')
settings = yaml.load(stream, yaml.SafeLoader)

def load_cache(request):
  # Check for a token cache in the session
  cache = msal.SerializableTokenCache()
  if request.session.get('token_cache'):
    cache.deserialize(request.session['token_cache'])
  return cache

def save_cache(request, cache):
  # If cache has changed, persist back to session
  if cache.has_state_changed: 
    access_token = json.loads(cache.serialize())['AccessToken']
    graph_user_id = list(access_token.keys())[0].split('.')[0]
    graphUser = GraphUser.objects.get(graph_user_id=graph_user_id)
    if(Connect.objects.filter(user_id=graphUser.id).exists()):
      connect = Connect.objects.get(user_id=graphUser.id)
      connect.token_cache = cache.serialize()
    else:
      new_connect = Connect(token_cache=cache.serialize(), user_id=graphUser.id, microsoft_user_id=graph_user_id)
      new_connect.save()
    request.session['token_cache'] = cache.serialize()

def get_msal_app(cache=None):
  # Initialize the MSAL confidential client
  auth_app = msal.ConfidentialClientApplication(
    settings['app_id'],
    authority=settings['authority'],
    client_credential=settings['app_secret'],
    token_cache=cache)

  return auth_app

# Method to generate a sign-in flow
def get_sign_in_flow():
  auth_app = get_msal_app()

  return auth_app.initiate_auth_code_flow(
    settings['scopes'],
    redirect_uri=settings['redirect'])

# Method to exchange auth code for access token
def get_token_from_code(request):
  cache = load_cache(request)
  auth_app = get_msal_app(cache)

  # Get the flow saved in session
  flow = request.session.pop('auth_flow', {})

  result = auth_app.acquire_token_by_auth_code_flow(flow, request.GET)
  
  user = get_user(result['access_token'])
  store_user(request, user)
  save_cache(request, cache)

  return result
# </FirstCodeSnippet>

# <SecondCodeSnippet>
def store_user(request, user):
  try:
    id = user['id'].split('@')[0]
    if(GraphUser.objects.filter(graph_user_id=id).exists()):
      print('exist')
    else:
      new_graph_user = GraphUser(graph_user_id=id, name=user['displayName'], email=user['mail'] if (user['mail'] != None) else user['userPrincipalName'], timezone=user['mailboxSettings']['timeZone'] if ('timeZone' in user['mailboxSettings']) else 'UTC')
      new_graph_user.save()
    request.session['graphUser'] = {
      'is_authenticated': True, 
      'graph_user_id': id,
      'name': user['displayName'],
      'email': user['mail'] if (user['mail'] != None) else user['userPrincipalName'],
      'timeZone': user['mailboxSettings']['timeZone'] if ('timeZone' in user['mailboxSettings']) else 'UTC'
    }
  except Exception as e:
    print(e)

def get_token(request):
  cache = load_cache(request)
  auth_app = get_msal_app(cache)

  accounts = auth_app.get_accounts()
  if accounts:
    result = auth_app.acquire_token_silent(
      settings['scopes'],
      account=accounts[0])

    save_cache(request, cache)

    return result['access_token']

def get_token_with_graph_user(graph_user_id):
  connect = Connect.objects.get(microsoft_user_id=graph_user_id)
  token_cache = connect.token_cache
  cache = msal.SerializableTokenCache()
  cache.deserialize(token_cache)
  auth_app = get_msal_app(cache)

  accounts = auth_app.get_accounts()
  if accounts:
    result = auth_app.acquire_token_silent(
      settings['scopes'],
      account=accounts[0])

    connect.token_cache = cache.serialize()
    connect.save()

    return result['access_token']

def remove_user_and_token(request):
  if 'token_cache' in request.session:
    del request.session['token_cache']

  if 'graphUser' in request.session:
    del request.session['graphUser']
# </SecondCodeSnippet>
