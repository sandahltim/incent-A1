# forms.py
# Version: 1.2.13
# Note: Updated SetPointDecayForm to use days[] naming for consistency with client-side submission. Retained all functionality from version 1.2.10. Compatible with app.py (1.2.88), script.js (1.2.68), config.py (1.2.6), admin_manage.html (1.2.33), incentive.html (1.2.30), quick_adjust.html (1.2.11), style.css (1.2.17), base.html (1.2.21), macros.html (1.2.10), start_voting.html (1.2.7), settings.html (1.2.6), admin_login.html (1.2.5), incentive_service.py (1.2.22), history.html (1.2.6), error.html, init_db.py (1.2.4).

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, SubmitField, TextAreaField, SelectMultipleField, FloatField
from wtforms.validators import DataRequired, NumberRange, Length, Optional


class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StartVotingForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Start Voting')

class PauseVotingForm(FlaskForm):
    submit = SubmitField('Pause Voting')

class CloseVotingForm(FlaskForm):
    password = PasswordField('Admin Password', validators=[DataRequired()])
    submit = SubmitField('Close Voting')

class ResetScoresForm(FlaskForm):
    submit = SubmitField('Reset All Scores')

class VoteForm(FlaskForm):
    initials = StringField('Your Initials', validators=[DataRequired(), Length(min=2, max=10)])
    submit = SubmitField('Submit Votes')

class AddEmployeeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    initials = StringField('Initials', validators=[DataRequired(), Length(min=2, max=10)])
    role = SelectField('Role', validators=[DataRequired()], choices=[])
    submit = SubmitField('Add Employee')

class AdjustPointsForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    reason = StringField('Reason', validators=[DataRequired(), Length(min=1, max=200)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Adjust Points')

class AddRuleForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired(), Length(min=1, max=200)])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    details = TextAreaField('Details', validators=[Length(max=500)])
    submit = SubmitField('Add Rule')

class EditRuleForm(FlaskForm):
    old_description = StringField('Old Description', validators=[DataRequired(), Length(min=1, max=200)])
    new_description = StringField('New Description', validators=[DataRequired(), Length(min=1, max=200)])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    details = TextAreaField('Details', validators=[Length(max=500)])
    submit = SubmitField('Edit Rule')

class RemoveRuleForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Remove')

class EditEmployeeForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    name = StringField('New Name', validators=[DataRequired(), Length(min=1, max=100)])
    role = SelectField('New Role', validators=[DataRequired()], choices=[])
    submit = SubmitField('Edit Employee')

class RetireEmployeeForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    submit = SubmitField('Retire')

class ReactivateEmployeeForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    submit = SubmitField('Reactivate')

class DeleteEmployeeForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    submit = SubmitField('Delete Forever')

class UpdatePotForm(FlaskForm):
    sales_dollars = IntegerField('Sales Dollars', validators=[DataRequired(), NumberRange(min=0)])
    bonus_percent = IntegerField('Bonus % of Sales Amount', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Update Pot')

class UpdatePriorYearSalesForm(FlaskForm):
    prior_year_sales = IntegerField('Prior Year Sales Dollars', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Update Prior Year Sales')

class SetPointDecayForm(FlaskForm):
    role_name = SelectField('Role', validators=[DataRequired()])
    points = IntegerField('Points to Deduct Daily', validators=[DataRequired(), NumberRange(min=0)])
    days = SelectMultipleField('Days to Trigger', choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday')
    ], validators=[Optional()], option_widget=lambda x: x(name='days[]'))
    submit = SubmitField('Set Point Decay')

class UpdateAdminForm(FlaskForm):
    old_username = SelectField('Current Username', validators=[DataRequired()], choices=[])
    new_username = StringField('New Username', validators=[DataRequired(), Length(min=1, max=50)])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Update Admin')

class AddRoleForm(FlaskForm):
    role_name = StringField('Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    percentage = IntegerField('Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Add Role')

class EditRoleForm(FlaskForm):
    old_role_name = StringField('Old Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    new_role_name = StringField('New Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    percentage = FloatField('Percentage', validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField('Edit')

class RemoveRoleForm(FlaskForm):
    role_name = StringField('Role Name', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Remove')

class MasterResetForm(FlaskForm):
    password = PasswordField('Master Password', validators=[DataRequired()])
    submit = SubmitField('Reset All Voting and History')

class FeedbackForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(min=1, max=1000)])
    initials = StringField('Initials', validators=[Length(max=10)])
    submit = SubmitField('Submit Feedback')

class VotingThresholdsForm(FlaskForm):
    pos_threshold_1 = IntegerField('Positive Threshold 1 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    pos_points_1 = IntegerField('Positive Points 1', validators=[DataRequired(), NumberRange(min=0, max=100)])
    pos_threshold_2 = IntegerField('Positive Threshold 2 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    pos_points_2 = IntegerField('Positive Points 2', validators=[DataRequired(), NumberRange(min=0, max=100)])
    pos_threshold_3 = IntegerField('Positive Threshold 3 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    pos_points_3 = IntegerField('Positive Points 3', validators=[DataRequired(), NumberRange(min=0, max=100)])
    neg_threshold_1 = IntegerField('Negative Threshold 1 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    neg_points_1 = IntegerField('Negative Points 1', validators=[DataRequired(), NumberRange(min=-100, max=0)])
    neg_threshold_2 = IntegerField('Negative Threshold 2 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    neg_points_2 = IntegerField('Negative Points 2', validators=[DataRequired(), NumberRange(min=-100, max=0)])
    neg_threshold_3 = IntegerField('Negative Threshold 3 (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    neg_points_3 = IntegerField('Negative Points 3', validators=[DataRequired(), NumberRange(min=-100, max=0)])
    submit = SubmitField('Update Voting Thresholds')

class QuickAdjustForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    reason = StringField('Reason', validators=[DataRequired(), Length(min=1, max=200)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    username = StringField('Username', validators=[Optional(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[Optional()])
    submit = SubmitField('Adjust Points')