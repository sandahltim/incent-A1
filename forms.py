# forms.py
# Version: 1.0.0
# Description: Defines Flask-WTF forms with CSRF protection for the A1 Rent-It Incentive Program.

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, SubmitField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired, NumberRange, Length

class AdminLoginForm(FlaskForm):
    # Form for admin login
    username = StringField('Username', validators=[DataRequired(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StartVotingForm(FlaskForm):
    # Form to start a voting session
    username = StringField('Username', validators=[DataRequired(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Start Voting')

class VoteForm(FlaskForm):
    # Form for casting votes
    initials = StringField('Your Initials', validators=[DataRequired(), Length(min=2, max=10)])
    submit = SubmitField('Submit Votes')

class AddEmployeeForm(FlaskForm):
    # Form to add a new employee
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    initials = StringField('Initials', validators=[DataRequired(), Length(min=2, max=10)])
    role = SelectField('Role', validators=[DataRequired()], choices=[])  # Choices set dynamically
    submit = SubmitField('Add Employee')

class AdjustPointsForm(FlaskForm):
    # Form to adjust employee points
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])  # Choices set dynamically
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    reason = StringField('Reason', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Adjust Points')

class AddRuleForm(FlaskForm):
    # Form to add a new rule
    description = StringField('Description', validators=[DataRequired(), Length(min=1, max=200)])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    submit = SubmitField('Add Rule')

class EditRuleForm(FlaskForm):
    # Form to edit an existing rule
    old_description = StringField('Old Description', validators=[DataRequired(), Length(min=1, max=200)])
    new_description = StringField('New Description', validators=[DataRequired(), Length(min=1, max=200)])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    submit = SubmitField('Edit Rule')

class RemoveRuleForm(FlaskForm):
    # Form to remove a rule
    description = StringField('Description', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Remove')

class EditEmployeeForm(FlaskForm):
    # Form to edit an employee
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])  # Choices set dynamically
    name = StringField('New Name', validators=[DataRequired(), Length(min=1, max=100)])
    role = SelectField('New Role', validators=[DataRequired()], choices=[])  # Choices set dynamically
    submit = SubmitField('Edit Employee')

class RetireEmployeeForm(FlaskForm):
    # Form to retire an employee
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])  # Choices set dynamically
    submit = SubmitField('Retire')

class ReactivateEmployeeForm(FlaskForm):
    # Form to reactivate an employee
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])  # Choices set dynamically
    submit = SubmitField('Reactivate')

class DeleteEmployeeForm(FlaskForm):
    # Form to permanently delete an employee
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])  # Choices set dynamically
    submit = SubmitField('Delete Forever')

class UpdatePotForm(FlaskForm):
    # Form to update incentive pot
    sales_dollars = IntegerField('Sales Dollars', validators=[DataRequired(), NumberRange(min=0)])
    bonus_percent = IntegerField('Bonus % of Sales Amount', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Update Pot')

class UpdatePriorYearSalesForm(FlaskForm):
    # Form to update prior year sales
    prior_year_sales = IntegerField('Prior Year Sales Dollars', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Update Prior Year Sales')

class SetPointDecayForm(FlaskForm):
    # Form to set point decay
    role_name = SelectField('Role', validators=[DataRequired()], choices=[])  # Choices set dynamically
    points = IntegerField('Points to Deduct Daily', validators=[DataRequired(), NumberRange(min=0, max=100)])
    days = SelectMultipleField('Days to Trigger', choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday')
    ])
    submit = SubmitField('Set Point Decay')

class UpdateAdminForm(FlaskForm):
    # Form to update admin credentials
    old_username = SelectField('Current Username', validators=[DataRequired()], choices=[])  # Choices set dynamically
    new_username = StringField('New Username', validators=[DataRequired(), Length(min=1, max=50)])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Update Admin')

class AddRoleForm(FlaskForm):
    # Form to add a new role
    role_name = StringField('Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    percentage = IntegerField('Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Add Role')

class EditRoleForm(FlaskForm):
    # Form to edit an existing role
    old_role_name = StringField('Old Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    new_role_name = StringField('New Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    percentage = IntegerField('Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Edit')

class RemoveRoleForm(FlaskForm):
    # Form to remove a role
    role_name = StringField('Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Remove')

class MasterResetForm(FlaskForm):
    # Form for master reset
    password = PasswordField('Master Password', validators=[DataRequired()])
    submit = SubmitField('Reset All Voting and History')