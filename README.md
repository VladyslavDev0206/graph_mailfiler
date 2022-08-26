# graph_mailfiler
Access graph to fetch and patch resources such as mails

- Python version 3.8 required

- establish a virtual environment

- then install modules required
  pip install -r requirements.txt
  
- database setup
  server : Postgresql on local
  Environment variable about database is : DATABASES variable in graph_mailfiler/settings.py
  
- py manage.py migrate
  py manage.py runserver
  
  Then enter "localhost:8000" on the browser.
