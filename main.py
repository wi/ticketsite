import uuid
from flask import Flask, render_template, flash, redirect, url_for, session, request, jsonify
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import timedelta, datetime
from mongoDB import MongoHandler
from Tickets import Ticket

app = Flask(__name__)
app.secret_key = 'hj43w98i05rth3wuiontrf4eokjwl'
app.permanent_session_lifetime = timedelta(days=1)
app.config.ticket_mongo = MongoHandler('tickets', 'tickets')
app.config.user_mongo = MongoHandler('tickets', 'users')


# Form classes
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords do not match')])
    confirm = PasswordField('Confirm Password', [validators.DataRequired(),
                                                 validators.EqualTo('confirm', message='Passwords do not match')])


class createTicket(Form):
    message = TextAreaField('', [validators.Length(min=1, max=2000)])


class dashboardForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    perms = SelectField('perms')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


# Index
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return render_template('create_ticket.html')
    return render_template('home.html')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))
        check = str(form.password.data)

        user_check = app.config.user_mongo.raw_query({'username': username.lower()})
        email_check = app.config.user_mongo.raw_query({'email': email})

        if user_check is not None:
            flash('Username Taken', 'danger')
            return redirect(url_for('register'))
        elif email_check is not None:
            flash('email already in use!', 'danger')
            return redirect(url_for('register'))
        elif len(check) <= 5:
            flash('Please use a stronger password!', 'danger')
            return redirect(url_for('register'))

        app.config.user_mongo.raw_insert(
            {'_id': str(uuid.uuid4()), 'email': email.lower(), 'username': username.lower(), 'password': password,
             'name': name, 'creation_date': int(datetime.now().timestamp()), 'permission_level': 0})
        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username'].lower()

        user_check = app.config.user_mongo.raw_query({'username': username})
        if user_check is None:
            user_check = app.config.user_mongo.raw_query({'email': username})

        if user_check is not None:
            if sha256_crypt.verify(request.form['password'], user_check['password']):
                # Passed
                session['logged_in'] = True
                session['username'] = username.lower()
                session['uuid'] = user_check['_id']
                session['permission_level'] = user_check['permission_level']
                session['view_all'] = False

                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid login')
        else:
            return render_template('login.html', error='Username not found')

    return render_template('login.html')


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/create', methods=['GET', 'POST'])
@is_logged_in
def create_ticket():
    form = createTicket(request.form)
    if request.method == "POST" and form.validate():
        ticket_id = app.config.ticket_mongo.get_max_value('_id')
        ticket_id = ticket_id['_id'] + 1
        ticket = Ticket(ticket_id, session['uuid'], form.message.data)
        app.config.ticket_mongo.raw_insert(ticket.create_default_ticket())

        return render_template('view_ticket.html', data=ticket.get_ticket_db())

    return render_template('create.html', form=form)


@app.route('/tickets', methods=['GET', 'POST'])
@is_logged_in
def tickets():
    if request.method == "POST":
        if request.form['submit'] == "Create a Ticket":
            return redirect('create')
        elif request.form['submit'] == "Toggle view-all" and session['permission_level'] > 0:
            session['view_all'] = not session['view_all']
            flash(f'Toggled your view all to {"on" if session["view_all"] is True else "off"}', 'success')
            return redirect('tickets')
    if not session['view_all']:
        tickets_ = app.config.ticket_mongo.raw_query({'ticket_owner_uid': session['uuid']}, one=False).sort("_id",
                                                                                                            -1)
        if tickets_ is not None:
            return render_template('view_tickets.html', tickets=tickets_)
        return render_template('view_tickets.html', msg='You have no open tickets!')
    else:
        if session['permission_level'] > 0:
            tickets_ = app.config.ticket_mongo.raw_query({}, one=False).sort("_id", -1)
            if tickets_ is not None:
                return render_template('view_tickets.html', tickets=tickets_, all=True)
            return render_template('view_tickets.html', msg='There are no created tickets!')
        else:
            flash('You don\'t have access to that.', 'danger')
            return redirect('view_tickets')


@app.route('/viewticket/<int:ticket_id>', methods=['GET', 'POST'])
@is_logged_in
def tickets_with_id(ticket_id):
    form = createTicket(request.form)
    if request.method == "POST":
        ticket = Ticket(ticket_id)
        if request.form['submit'] == "Add reply":
            if form.validate():
                if ticket.is_open():
                    ticket.add_reply(session['uuid'], form.message.data)
                    ticket.update()
                    flash('reply added successfully.', 'success')
                    return render_template('view_ticket.html', data=ticket.get_ticket_db(),
                                           form=createTicket(request.form))
                else:
                    flash('This ticket has been closed', 'danger')
                    return render_template('view_ticket.html', data=Ticket(ticket_id).get_ticket_db(), form=form)
            else:
                flash('Your reply is not within 15-2000 characters!', 'danger')
                return render_template('view_ticket.html', data=Ticket(ticket_id).get_ticket_db(), form=form)
        elif request.form['submit'] == "Close ticket":
            flash('This ticket has been closed', 'success')
            ticket.close_reopen()
            return render_template('view_ticket.html', data=Ticket(ticket_id).get_ticket_db(),
                                   form=createTicket(request.form))
        elif request.form['submit'] == "Reopen ticket":
            flash('This ticket has been reopened', 'success')
            ticket.close_reopen()
            return render_template('view_ticket.html', data=Ticket(ticket_id).get_ticket_db(),
                                   form=createTicket(request.form))
    ticket_info = app.config.ticket_mongo.raw_query({'_id': ticket_id})
    if ticket_info is None:
        flash('That ticket does not exist', 'danger')
        return redirect('/view_tickets')
    else:
        if not session['permission_level'] > 0 and session['uuid'] != ticket_info['ticket_owner_uid']:
            flash('You dont have access to this ticket!', 'danger')
            return redirect('/view_tickets')
        return render_template('view_ticket.html', data=ticket_info, form=form)


# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
    if session['permission_level'] > 1:
        form = dashboardForm(request.form)
        if request.method == "POST":
            if 3 < len(form.username.data) < 26:
                username = form.username.data.lower()
                user = app.config.user_mongo.raw_query({"username": username})
                if user is None:
                    flash('That user does not exist.', 'danger')
                    return render_template('dashboard.html', form=form)
                app.config.user_mongo.raw_update({"username": username}, {"$set": {"permission_level": int(form.perms.data)}})
                flash(f'Updated {username}\'s permission level to {form.perms.data}')
                return render_template('dashboard.html', form=form)
            else:
                flash('That isn\'t a valid username', 'danger')
                return render_template('dashboard.html', form=form)
        return render_template('dashboard.html', form=form)
    flash('You don\'t have access to this!', 'danger')
    return redirect('tickets')


def time_string(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime("%B %d %Y @ %I:%M %p UTC")


def convert_uid_username(uid):
    user = app.config.user_mongo.raw_query({'_id': uid})
    return user['username'] if user is not None else "User not found"


if __name__ == '__main__':
    app.jinja_env.globals.update(time_string=time_string)
    app.jinja_env.globals.update(convert_uid_username=convert_uid_username)
    app.run(port=5000, debug=True)
