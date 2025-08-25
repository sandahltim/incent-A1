# forms.py
# Version: 1.2.23
# Note: Allow zero values for scoreboard timing settings with InputRequired.

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, SubmitField, TextAreaField, SelectMultipleField, FloatField
from wtforms.validators import DataRequired, InputRequired, NumberRange, Length, Optional, Regexp

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
    pin = PasswordField('PIN (4-6 digits)', validators=[DataRequired(), Length(min=4, max=6)], default='8101')
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
    pin = PasswordField('PIN (4-6 digits)', validators=[DataRequired(), Length(min=4, max=6)])
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
    bonus_percent = FloatField('Bonus % of Sales Amount', validators=[DataRequired(), NumberRange(min=0, max=100)])
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
    ], validators=[Optional()], coerce=str)
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

class VoteLimitsForm(FlaskForm):
    max_total_votes = IntegerField('Max Total Votes', validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_plus_votes = IntegerField('Max Positive Votes', validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_minus_votes = IntegerField('Max Negative Votes', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Update Vote Limits')

class ScoreboardSettingsForm(FlaskForm):
    money_threshold = IntegerField('In The Money Threshold', validators=[InputRequired(), NumberRange(min=0, max=1000)])
    top_color = StringField('Top Color', validators=[DataRequired()])
    mid_color = StringField('Middle Color', validators=[DataRequired()])
    bottom_color = StringField('Bottom Color', validators=[DataRequired()])
    reel_color = StringField('Reel Color', validators=[DataRequired()])
    spin_duration = IntegerField('Spin Duration (s)', validators=[InputRequired(), NumberRange(min=0, max=3600)])
    spin_iterations = IntegerField('Spin Iterations (0=infinite)', validators=[InputRequired(), NumberRange(min=0, max=1000)])
    spin_pause = IntegerField('Spin Pause (s)', validators=[InputRequired(), NumberRange(min=0, max=3600)])
    spin_delay = IntegerField('Spin Start Delay (s)', validators=[InputRequired(), NumberRange(min=0, max=3600)])
    refresh_interval = IntegerField('Refresh Interval (s)', validators=[DataRequired(), NumberRange(min=1, max=3600)])
    submit = SubmitField('Update Scoreboard Settings')

class QuickAdjustForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=-100, max=100)])
    reason = StringField('Reason', validators=[DataRequired(), Length(min=1, max=200)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    username = StringField('Username', validators=[Optional(), Length(min=1, max=50)])
    password = PasswordField('Password', validators=[Optional()])
    submit = SubmitField('Adjust Points')


class AwardGameForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], choices=[])
    game_type = SelectField('Game Type', validators=[DataRequired()], choices=[('slot', 'Slot'), ('scratch', 'Scratch-Off'), ('roulette', 'Roulette')])
    submit = SubmitField('Award Game')


class PlayGameForm(FlaskForm):
    pin = PasswordField('Enter PIN', validators=[DataRequired(), Length(min=4, max=6)])
    game_id = StringField('Game ID', validators=[DataRequired()])
    submit = SubmitField('Play')


class MiniGameSettingsForm(FlaskForm):
    award_chance_points = IntegerField('Award % on Points', validators=[DataRequired(), NumberRange(min=0, max=100)])
    award_chance_vote = IntegerField('Award % on Vote', validators=[DataRequired(), NumberRange(min=0, max=100)])
    points_amount = IntegerField('Points Prize Amount', validators=[DataRequired()])
    points_chance = IntegerField('Points Prize Chance', validators=[DataRequired(), NumberRange(min=0, max=100)])
    prize1_desc = StringField('Prize 1 Description', validators=[Optional(), Length(max=100)])
    prize1_value = FloatField('Prize 1 Value', validators=[Optional()])
    prize1_chance = IntegerField('Prize 1 Chance', validators=[Optional(), NumberRange(min=0, max=100)])
    prize2_desc = StringField('Prize 2 Description', validators=[Optional(), Length(max=100)])
    prize2_value = FloatField('Prize 2 Value', validators=[Optional()])
    prize2_chance = IntegerField('Prize 2 Chance', validators=[Optional(), NumberRange(min=0, max=100)])
    prize3_desc = StringField('Prize 3 Description', validators=[Optional(), Length(max=100)])
    prize3_value = FloatField('Prize 3 Value', validators=[Optional()])
    prize3_chance = IntegerField('Prize 3 Chance', validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField('Save Mini-Game Settings')


class EmployeeLoginForm(FlaskForm):
    employee_id = StringField('Employee ID', validators=[DataRequired(), Regexp(r'^E\d{3}$', message='Employee ID must be in format E001, E002, etc.')])
    pin = PasswordField('PIN', validators=[DataRequired(), Length(min=4, max=6)])
    submit = SubmitField('Access')


class ChangePinForm(FlaskForm):
    current_pin = PasswordField('Current PIN', validators=[DataRequired(), Length(min=4, max=6)])
    new_pin = PasswordField('New PIN', validators=[DataRequired(), Length(min=4, max=6)])
    submit = SubmitField('Change PIN')


class PortForm(FlaskForm):
    port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)])
    submit = SubmitField('Update Port')


class RestartServiceForm(FlaskForm):
    submit = SubmitField('Restart Service')


class RebootPiForm(FlaskForm):
    submit = SubmitField('Reboot Pi')

