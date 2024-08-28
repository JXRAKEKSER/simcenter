import os
from sys import platform
from flask import url_for, flash, render_template, redirect, session, jsonify, Blueprint, Flask, Response
from flask_login import current_user, login_required, login_user
import glob
import app.database as data
import cv2
import face_recognition
import glob2 as gb
import datetime
#import app.settings as settings_handlers
from app.middleware import db, gtranslator
from app.utils import log_error, remove_string_noise
from app.forms.core import LoginForm, TouchSubmitForm
from app.helpers import (reject_no_offices, reject_operator, is_operator, reject_not_admin,
                         is_office_operator, is_common_task_operator, decode_links,
                         reject_setting, get_or_reject)
import time

global video

core = Blueprint('core', __name__)

def gen(video):
    while True:
        success, image = video.read()
        ret, jpeg = cv2.imencode('.jpg', image)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@core.route('/', methods=['GET', 'POST'], defaults={'n': None})
@core.route('/log/<n>', methods=['GET', 'POST'])
def root(n=None):
    ''' welcome view and login. '''
    form = LoginForm()
    has_default_password = data.User.has_default_password()
    wrong_credentials = n == 'a'
    should_redirect = n == 'b'
    single_row = data.Settings.get().single_row

    def logged_in_all_good():
        destination = url_for('manage_app.manage')

        if is_operator() and not single_row:
            destination = url_for('manage_app.offices',
                                  o_id=data.Operators.get(current_user.id).office_id)
        elif should_redirect:
            destination = f'{session.get("next_url", "/")}'
            session['next_url'] = None

        flash('Notice: logged-in and all good', 'info')
        return redirect(destination)

    if form.validate_on_submit():
        if current_user.is_authenticated:
            return logged_in_all_good()

        user = data.User.query.filter_by(name=form.name.data).first()

        if not user or not user.verify_password(form.password.data):
            flash('Error: wrong user name or password', 'danger')
            return redirect(url_for('core.root', n='a'))

        login_user(user, remember=bool(form.rm.data))
        return logged_in_all_good()

    return render_template('index.html',
                           page_title='Advance queue system', form=form,
                           n=wrong_credentials, dpass=has_default_password)


@core.route('/serial/<int:t_id>', methods=['POST', 'GET'], defaults={'office_id': None})
@core.route('/serial/<int:t_id>/<int:office_id>', methods=['GET', 'POST'])
@reject_setting('single_row', True)
#@get_or_reject(t_id=data.Task)
def serial(task, office_id=None):
    ''' generate a new ticket and print it. '''
    windows = os.name == 'nt'
    form = TouchSubmitForm()
    task = data.Task.get(task.id)
    office = data.Office.get(office_id)
    touch_screen_stings = data.Touch_store.get()
    ticket_settings = data.Printer.get()
    printed = not touch_screen_stings.n
    numeric_ticket_form = ticket_settings.value == 2
    name_or_number = remove_string_noise(form.name.data or '',
                                         lambda s: s.startswith('0'),
                                         lambda s: s[1:]) or None

    # NOTE: if it is registered ticket, will display the form
    if not form.validate_on_submit() and not printed:
        return render_template('touch.html', title=touch_screen_stings.title,
                               tnumber=numeric_ticket_form, ts=touch_screen_stings,
                               bgcolor=touch_screen_stings.bgcolor, a=4, done=False,
                               page_title='Touch Screen - Enter name ', form=form,
                               dire='multimedia/', alias=data.Aliases.query.first(),
                               office_id=office_id)

    new_ticket, exception = data.Serial.create_new_ticket(task,
                                                          office,
                                                          name_or_number)

    if exception:
        flash('Error: you must have available printer, to use printed', 'danger')
        flash('Notice: make sure that printer is properly connected', 'info')

        if windows:
            flash('Notice: Make sure to make the printer shared on the local network', 'info')
        elif 'linux' in platform:
            flash('Notice: Make sure to execute the command `sudo gpasswd -a $(users) lp` and '
                  'reboot the system', 'info')

        log_error(exception)
        return redirect(url_for('core.root'))

    return redirect(url_for('core.touch', a=1, office_id=office_id))


@core.route('/serial_r/<int:o_id>')
@login_required
#@get_or_reject(o_id=data.Office)
def serial_r(office):
    ''' reset by removing tickets of a given office. '''
    single_row = data.Settings.get().single_row
    office = data.Office.get(office.id)
    office_redirection = url_for('manage_app.all_offices')\
        if single_row else url_for('manage_app.offices', o_id=office.id)

    if (is_operator() and not is_office_operator(office.id)) and not single_row:
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    if not office.tickets.first():
        flash('Error: the office is already resetted', 'danger')
        return redirect(office_redirection)

    office.tickets.delete()
    db.session.commit()
    flash('Notice: office has been resetted. ..', 'info')
    return redirect(office_redirection)


@core.route('/serial_ra')
@login_required
@reject_operator
@reject_no_offices
@reject_setting('single_row', True)
def serial_ra():
    ''' reset all offices by removing all tickets. '''
    tickets = data.Serial.query.filter(data.Serial.number != 100)

    if not tickets.first():
        flash('Error: the office is already resetted', 'danger')
        return redirect(url_for('manage_app.all_offices'))

    tickets.delete()
    db.session.commit()
    flash('Notice: office has been resetted. ..', 'info')
    return redirect(url_for('manage_app.all_offices'))

@core.route('/hall')
def hall():
    schedule = data.Access.query.all()
    stud = data.Student.query.all()
    stud_list = data.Stud_list.query.all()
    tablo = data.Tablo.query.all()

    return render_template('tablo1.html', schedule=schedule, stud=stud, tablo=tablo)


@core.route('/camcap')
def camcap():
    return render_template('camcap.html')


@core.route('/monitor')
def monitor():
    return render_template('tablo2.html')

@core.route('/afk')
def afk():
    return render_template('nres.html')

@core.route('/serial_rt/<int:t_id>', defaults={'ofc_id': None})
@core.route('/serial_rt/<int:t_id>/<int:ofc_id>')
@login_required
@reject_setting('single_row', True)
#@get_or_reject(t_id=data.Task)
def serial_rt(task, ofc_id=None):
    ''' reset a given task by removing its tickets. '''
    if is_operator() and not is_common_task_operator(task.id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    task = data.Task.get(task.id)
    tickets = task.tickets

    if ofc_id:
        tickets = tickets.filter_by(office_id=ofc_id)

    if not tickets.first():
        flash('Error: the task is already resetted', 'danger')
        return redirect(url_for('manage_app.task', o_id=task.id, ofc_id=ofc_id))

    tickets.delete()
    db.session.commit()
    flash('Error: the task is already resetted', 'info')
    return redirect(url_for('manage_app.task', o_id=task.id, ofc_id=ofc_id))


@core.route('/pull', defaults={'o_id': None, 'ofc_id': None})
@core.route('/pull/<int:o_id>/<int:ofc_id>')
@login_required
def pull(o_id=None, ofc_id=None):
    ''' pull ticket for specific task and office or globally. '''
    def operators_not_allowed():
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    strict_pulling = data.Settings.get().strict_pulling
    single_row = data.Settings.get().single_row
    task = data.Task.get(0 if single_row else o_id)
    office = data.Office.get(0 if single_row else ofc_id)
    global_pull = not bool(o_id and ofc_id)
    general_redirection = redirect(url_for('manage_app.all_offices')
                                   if global_pull or single_row else
                                   url_for('manage_app.task', ofc_id=ofc_id, o_id=o_id))

    if global_pull:
        if not single_row and is_operator():
            return operators_not_allowed()
    else:
        if not task:
            flash('Error: wrong entry, something went wrong', 'danger')
            return redirect(url_for('core.root'))

        if is_operator() and not (is_office_operator(ofc_id)
                                  if strict_pulling else
                                  is_common_task_operator(task.id)):
            return operators_not_allowed()

    next_ticket = data.Serial.get_next_ticket(task_id=o_id,
                                              office_id=ofc_id)

    if not next_ticket:
        flash('Error: no tickets left to pull from ..', 'danger')
        return general_redirection

    next_ticket.pull(office and office.id or next_ticket.office_id)
    flash('Notice: Ticket has been pulled ..', 'info')
    return general_redirection


@core.route('/pull_unordered/<ticket_id>/<redirect_to>', defaults={'office_id': None})
@core.route('/pull_unordered/<ticket_id>/<redirect_to>/<int:office_id>')
@login_required
@decode_links
@reject_setting('single_row', True)
def pull_unordered(ticket_id, redirect_to, office_id=None):
    office = data.Office.get(office_id)
    ticket = data.Serial.query.filter_by(id=ticket_id).first()
    strict_pulling = data.Settings.get().strict_pulling

    if not ticket or ticket.on_hold:
        flash('Error: wrong entry, something went wrong', 'danger')
        return redirect(url_for('core.root'))

    if is_operator() and not (is_office_operator(ticket.office_id)
                              if strict_pulling else
                              is_common_task_operator(ticket.task_id)):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    ticket.pull((office or ticket.office).id)
    flash('Notice: Ticket has been pulled ..', 'info')
    return redirect(redirect_to)


@core.route('/on_hold/<ticket_id>/<redirect_to>')
@login_required
@decode_links
@reject_setting('single_row', True)
#@get_or_reject(ticket_id=data.Serial)
def on_hold(ticket, redirect_to):
    ticket = data.Serial.get(ticket.id)
    strict_pulling = data.Settings.get().strict_pulling

    if is_operator() and not (is_office_operator(ticket.office_id)
                              if strict_pulling else
                              is_common_task_operator(ticket.task_id)):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    ticket.toggle_on_hold()
    flash('Notice: On-hold status has changed successfully', 'info')
    return redirect(redirect_to)


@core.route('/feed', defaults={'office_id': None})
@core.route('/feed/<int:office_id>')
def feed(office_id=None):
    ''' stream list of waiting tickets and current ticket. '''
    display_settings = data.Display_store.get()
    single_row = data.Settings.get().single_row
    current_ticket = data.Serial.get_last_pulled_ticket(office_id)
    empty_text = gtranslator.translate('Empty', dest=[session.get('lang')])
    current_ticket_text = current_ticket and current_ticket.display_text or empty_text
    current_ticket_office_name = current_ticket and current_ticket.office.display_text or empty_text
    current_ticket_task_name = current_ticket and current_ticket.task.name or empty_text

    def _resolve_ticket_index(_index):
        return '' if display_settings.hide_ticket_index else f'{_index + 1}. '

    if single_row:
        tickets_parameters = {
            f'w{_index + 1}': f'{_resolve_ticket_index(_index)}{number}'
            for _index, number in enumerate(range(getattr(current_ticket, 'number', 1) + 1,
                                                  getattr(current_ticket, 'number', 1) + 10))}
    else:
        waiting_tickets = (data.Serial.get_waiting_list_tickets(office_id) + ([None] * 9))[:9]
        tickets_parameters = {
            f'w{_index + 1}':
            f'{_resolve_ticket_index(_index)}{ticket.display_text}' if ticket else empty_text
            for _index, ticket in enumerate(waiting_tickets)}

    # NOTE: Add last 10 processed tickets, for supported template.
    if display_settings.tmp == 3:
        processed_tickets = (data.Serial.get_processed_tickets(office_id, offset=1) + ([None] * 9))[:9]
        tickets_parameters.update({
            f'p{_index + 1}':
            f'{_resolve_ticket_index(_index)}{ticket.display_text}' if ticket else empty_text
            for _index, ticket in enumerate(processed_tickets)})

    # NOTE: Ensure `tickets_parameters` last value is as distinct as the `current_ticket`
    # To fix `uniqueness` not picking up the change in passed waiting list
    tickets_parameters[f'w{len(tickets_parameters)}'] = (current_ticket.name
                                                         if current_ticket.n else
                                                         current_ticket.number
                                                         ) if current_ticket else empty_text

    return jsonify(con=current_ticket_office_name,
                   cot=current_ticket_text,
                   cott=current_ticket_task_name,
                   **tickets_parameters)


@core.route('/set_repeat_announcement/<int:status>')
@login_required
def set_repeat_announcement(status):
    ''' set repeat TTS announcement status. '''
    display_settings = data.Display_store.get()
    display_settings.r_announcement = bool(status)
    db.session.commit()

    return jsonify(status=bool(status))


@core.route('/repeat_announcement')
def repeat_announcement():
    ''' get repeat TTS announcement. '''
    display_settings = data.Display_store.get()
    status = display_settings.r_announcement

    if status:
        display_settings.r_announcement = False
        db.session.commit()

    return jsonify(status=status)


@core.route('/display', defaults={'office_id': None})
@core.route('/display/<int:office_id>')
def display(office_id=None):
    ''' display screen view. '''
    display_settings = data.Display_store.query.first()
    slideshow_settings = data.Slides_c.query.first()
    slides = data.Slides.query.order_by(data.Slides.id.desc()).all() or None
    aliases_settings = data.Aliases.query.first()
    video_settings = data.Vid.query.first()
    feed_url = url_for('core.feed', office_id=office_id)

    return render_template('display.html',
                           audio=1 if display_settings.audio == 'true' else 0,
                           audio_2=1 if display_settings.announce != 'false' else 0,
                           ss=slides, sli=slideshow_settings, ts=display_settings,
                           slides=data.Slides.query, tv=display_settings.tmp,
                           page_title='Display Screen', anr=display_settings.anr,
                           alias=aliases_settings, vid=video_settings,
                           feed_url=feed_url)

@core.route('/touch')
@core.route('/touch/en')
#@core.route('/touch/<int:a>', defaults={'office_id': None})
# @core.route('/touch/<int:a>/<int:office_id>')
@reject_setting('single_row', True)
def touch(a=1):
    ''' touch screen view. '''
    form = TouchSubmitForm()
    touch_screen_stings = data.Touch_store.query.first()
    numeric_ticket_form = data.Printer.query.first().value == 2
    aliases_settings = data.Aliases.query.first()
  #   office = data.Office.get(office_id)
   # tasks = data.Task.query.filter_by(hidden=False)\
   #                        .order_by(data.Task.timestamp)

  #  if office:
 #       tasks = tasks.filter(data.Task.offices.contains(office))


    return render_template('touch.html', ts=touch_screen_stings,
                           tnumber=numeric_ticket_form, page_title='Touch Screen',
                           alias=aliases_settings, form=form, d=a == 1,
                           a=touch_screen_stings.tmp)


    
@core.route('/pult')
def pult():
    
    return 
def create():

    os.mknod(r'C:\Users\1\Pictures\rezerv\2.txt')
def delete():
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), r'C:\Users\1\Pictures\rezerv\2.txt')
    
    return os.remove(path)


 
@core.route('/regist')
@core.route('/regist/en')
@core.route('/regist/ru')
def regist():
    return render_template('regist.html')

@core.route('/print-ticket')
def render_ticket():
    return render_template('ticket/ticket.html')

@core.route('/reg')
def regist_go():
    list_of_files = glob.glob(r'C:\Users\1\Pictures\gg\*')  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    x = latest_file[23:32]
    last_of_files = glob.glob(r'C:\Users\1\Pictures\rezerv\*')  # * means all if need specific format then *.csv
    litest_file = max(last_of_files, key=os.path.getctime)
    j = litest_file[27:28]
    if(x != '%DOCUMENT' ):
        if data.Stud_list.query.filter_by(nomer=x).all() !='':
            test = data.Stud_list.query.filter_by(nomer=x).all()
    elif (x == '%DOCUMENT' and j == '1'):
        x = "180725199"
        test = data.Stud_list.query.filter_by(nomer=x).all()
        
    elif(x == '%DOCUMENT' and j != '1'):
        test = data.Stud_list.query.filter_by(nomer=x).all()
  


    return render_template('helloallok.html', test=test)

@core.route('/printf')
def printf():
    list_of_files = glob.glob(r'C:\Users\1\Pictures\gg\*')  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    x = latest_file[23:32]
    last_of_files = glob.glob(r'C:\Users\1\Pictures\rezerv\*')  # * means all if need specific format then *.csv
    litest_file = max(last_of_files, key=os.path.getctime)
    j = litest_file[27:28]
    if(x != '%DOCUMENT' ):
        if data.Stud_list.query.filter_by(nomer=x).all() !='':
            test = data.Stud_list.query.filter_by(nomer=x).all()
    elif (x == '%DOCUMENT' and j == '1'):
        x = "180725199"
        test = data.Stud_list.query.filter_by(nomer=x).all()
        
    elif(x == '%DOCUMENT' and j != '1'):
        test = data.Stud_list.query.filter_by(nomer=x).all()
        
    test = data.Stud_list.query.filter_by(nomer=x).all()
    add_stud = data.Tablo(ident= test[0].ident,
                     name= test[0].name,
                     kabinet= test[0].kabinet,
                     level= test[0].level,
                     time= test[0].time)

    db.session.add(add_stud)
    db.session.commit()
    return render_template('printf.html')
    
    
@core.route('/settings/<setting>', defaults={'togo': None})
@core.route('/settings/<setting>/<togo>')
@login_required
@reject_not_admin
@decode_links
def settings(setting, togo=None):
    ''' toggle a setting. '''
    togo = togo or '/'
    settings = data.Settings.get()

    if not settings:
        flash('Error: Failed to find settings in the database', 'danger')
        return redirect(togo)

    toggled_setting_value = not bool(getattr(settings, setting, True))

    getattr( setting)(toggled_setting_value)
    settings.__setattr__(setting, toggled_setting_value)
    db.session.commit()
    flash(f'Notice: Setting got {"Enabled" if toggled_setting_value else "Disabled"} successfully.',
          'info')

    return redirect(togo)
    
@core.route('/video_feed')


def video_feed():
    start_time=time.time()
    video = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    img_path = gb.glob(r'C:\Users\1\Pictures\Фото_для_распознавания\\*.jpg')
    known_face_names = []
    known_face_encodings = []

    for i in img_path:
        picture_name = i.replace(r'C:\Users\1\Pictures\Фото_для_распознавания\\*.jpg', '')
        picture_newname = picture_name.replace('.jpg', '')
        someone_img = face_recognition.load_image_file(i)
        someone_face_encoding = face_recognition.face_encodings(someone_img)[0]
        known_face_names.append(picture_newname)
        known_face_encodings.append(someone_face_encoding)
        someone_img = []
        someone_face_encoding = []

    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while (time.time() - start_time) < 25:
        ret, frame = video.read()
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        if process_this_frame:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_names = []
            for i in face_encodings:
                match = face_recognition.compare_faces(known_face_encodings, i, tolerance=0.39)
                if True in match:
                    match_index = match.index(True)
                    name = "match"
                    # To print name and time
                    cute_clock = datetime.datetime.now()
                    print(known_face_names[match_index] + ':' + str(cute_clock))
                    return (redirect("http://172.29.8.47:5000/printf", code=302), cv2.destroyAllWindows())
                else:
                    name = "unknown"
                face_names.append(name)

        process_this_frame = not process_this_frame

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), 2)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        cv2.imshow('Video', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:  return (redirect("http://172.29.8.47:5000/touch/en", code=302), cv2.destroyAllWindows())

    video.release()
    cv2.destroyAllWindows()
    return Response(gen(video),
                    mimetype='multipart/x-mixed-replace; boundary=frame')