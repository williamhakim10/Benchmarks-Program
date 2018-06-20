from flask import session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
import requests

class BasicInfoForm(FlaskForm):
	name = StringField('Name', validators=[DataRequired()])
	newsroom = StringField('Newsroom', validators=[DataRequired()])
	email = (StringField('Email Address', validators=
		[DataRequired(), Email()]))
	submit = SubmitField('Submit')

	# Validate basic info submission
	def validate(self):
		
		# Default validation (if any), e.g. required fields
		rv = FlaskForm.validate(self)
		if not rv:
			return False

		# Store name, newsroom, and email in session
		session['name'] = self.name.data
		session['newsroom'] = self.newsroom.data
		session['email'] = self.email.data

		return True


class ApiKeyForm(FlaskForm):
	key = StringField('API Key', validators=[DataRequired()])
	submit = SubmitField('Submit')

	# Validate API key submission 
	def validate(self):
		
		# Default validation (if any), e.g. required fields
		rv = FlaskForm.validate(self)
		if not rv:
			return False

		key = self.key.data

		# Check key contains a data center (i.e. ends with '-usX')
		if '-' not in key:
			self.key.errors.append('Key missing data center')
			return False

		data_center = key.split('-')[1]

		# Get total number of lists
		# If connection refused by server or request fails, bad API key
		request_uri = ('https://' + data_center +
			'.api.mailchimp.com/3.0/')
		params = (
			('fields', 'total_items'),
		)
		try:
			response = (requests.get(request_uri +
				'lists', params=params, 
				auth=('shorenstein', key)))
		except requests.exceptions.ConnectionError:
			self.key.errors.append('Connection to MailChimp servers refused')
			return False
		if response.status_code != 200:
			self.key.errors.append(
				'MailChimp responded with error code ' + 
				str(response.status_code))
			return False

		# Store API key, data center, and number of lists in session
		session['key'] = key
		session['data_center'] = data_center
		session['num_lists'] = response.json().get('total_items')

		return True