import os
import pymysql
import numpy as np
import pymysql.cursors
from zeep import Client
import requests
from datetime import datetime, date, time, timedelta
from sys import platform
from flask import url_for, flash, render_template, redirect, session, jsonify, Blueprint, Flask, Response
from flask_login import current_user, login_required, login_user
import glob
import app.database as data
import cv2
#import face_recognition
import glob2 as gb
import datetime

#import app.settings as settings_handlers
from app.middleware import db, gtranslator
from app.utils import log_error, remove_string_noise, generate_qr_code
from app.forms.core import LoginForm, TouchSubmitForm
from app.helpers import (reject_no_offices, reject_operator, is_operator, reject_not_admin,
                         is_office_operator, is_common_task_operator, decode_links,
                         reject_setting, get_or_reject)
import time
import pyttsx3

from host_data import DATABASE_HOST, SOAP_HOST, DATABASE_PASSWORD, DATABASE_NAME, DATABASE_USER

from app.services.student.StudentService import StudentService
from app.services.parsec.parsec_service import get_code as get_parsec_code
from flask import request

tts = pyttsx3.init()
from gtts import gTTS
global video
from app.views.schedule import access, schedule1, createperson
core = Blueprint('core', __name__)
schedule1()
def gen(video):
    while True:
        success, image = video.read()
        ret, jpeg = cv2.imencode('.jpg', image)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def shift(lst, steps):
    if steps < 0:
        steps = abs(steps)
        for i in range(steps):
            lst.append(lst.pop(0))
    else:
        for i in range(steps):
            lst.insert(0, lst.pop())

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
            destination = url_for('manage_app.manage')

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
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    m = timedelta(hours=3, minutes=1)
    k = timedelta(hours=3, minutes=0)
    c = a+b #отображение студента с задержкой в 5 минут
    j = a+m #время для оповещения за 1 минуту до окончания
    o = a+k #текущее время
    c = a + b
    d1 = c.strftime("%d.%m.%Y")
    timez = c.strftime("%H:%M")
    test4 = data.Stud_access.query.filter(data.Stud_access.time_begin > timez).filter(data.Stud_access.date == d1).order_by(data.Stud_access.time_begin).all()

    access = data.Stud_access.query.all()

    schedule = data.Access.query.all()

    stud = data.Student.query.all()

    stud_list = data.Stud_list.query.all()
    tablo = data.Tablo.query.all()

    i=1

    return render_template('tablo1.html', schedule=schedule, stud=stud, tablo=tablo, access=access, timez=timez, test4=test4, i=i )

@core.route('/floor/<number>')
def floor(number):
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    m = timedelta(hours=3, minutes=1)
    k = timedelta(hours=3, minutes=0)
    c = a+b #отображение студента с задержкой в 5 минут
    j = a+m #время для оповещения за 1 минуту до окончания
    o = a+k #текущее время
    c = a + b
    d1 = c.strftime("%d.%m.%Y")
    timez = c.strftime("%H:%M")
    test4 = data.Stud_access.query.filter(data.Stud_access.time_begin > timez).filter(data.Stud_access.date == d1).filter(data.Stud_access.room.like(number+".%")).order_by(data.Stud_access.time_begin).all()
    access = data.Stud_access.query.all()
    schedule = data.Access.query.all()
    stud = data.Student.query.all()
    stud_list = data.Stud_list.query.all()
    tablo = data.Tablo.query.all()
    i=1
    print("test4-", test4)
    print("access-", access)
    print("schefule-", schedule)
    print("stud-", stud)
    print("tablo-", tablo)
    return render_template('tablo1.html', schedule=schedule, stud=stud, tablo=tablo, access=access, timez=timez, test4=test4, i=i )

@core.route('/camcap')
def camcap():
    return render_template('camcap.html')


@core.route('/monitor/<string:room>', methods=['GET', 'POST'])
def monitor(room):
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    m = timedelta(hours=3, minutes=1)
    k = timedelta(hours=2, minutes=59, seconds= 25)
    c = a+b #отображение студента с задержкой в 5 минут
    j = a+m #время для оповещения за 1 минуту до окончания
    o = a+k #текущее время
    d1 = c.strftime("%d.%m.%Y")
    rooms = data.Room.query.filter(data.Room.number == room).all()
    timez = c.strftime("%H:%M")
    timez1 = j.strftime("%H:%M")
    timez2 = o.strftime("%H:%M:%S")
    logs = data.Logs.query.filter(data.Logs.source == rooms[0].ip).filter(data.Logs.time > timez2).filter(data.Logs.date == d1).filter(data.Logs.event == "Нормальный вход по ключу").all()

    test4 = data.Stud_access.query.filter(data.Stud_access.time_begin > timez).filter(data.Stud_access.date == d1).filter(data.Stud_access.room == room).order_by(data.Stud_access.time_begin).all()
    test7 = data.Stud_access.query.filter(data.Stud_access.time_end >= timez1).filter(data.Stud_access.date == d1).filter(data.Stud_access.room == room).order_by(data.Stud_access.time_begin).all()
    test8 = data.Stud_access.query.filter(data.Stud_access.time_end > timez2).filter(data.Stud_access.date == d1).filter(data.Stud_access.room == room).order_by(data.Stud_access.time_begin).all()
    if bool(test4)!=0:
        tut = data.Specialization.query.filter(data.Specialization.name == test4[0].specialization).all()
        rr = data.Station.query.filter(data.Station.room == room).filter(data.Station.spec_id == tut[0].id).all()
    else:
        rr = data.Station.query.filter(data.Station.room == room).all()
    return render_template('monitor.html', test4=test4, rr=rr, test7=test7, test8=test8, logs=logs)

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
@core.route('/touch/ru')
#@core.route('/touch/<int:a>', defaults={'office_id': None})
# @core.route('/touch/<int:a>/<int:office_id>')
#@reject_setting('single_row', True)
def touch():
    ''' touch screen view. '''
   # form = TouchSubmitForm()
   # touch_screen_stings = data.Touch_store.query.first()
   # numeric_ticket_form = data.Printer.query.first().value == 2
   # aliases_settings = data.Aliases.query.first()
  #   office = data.Office.get(office_id)
   # tasks = data.Task.query.filter_by(hidden=False)\
   #                        .order_by(data.Task.timestamp)

  #  if office:
 #       tasks = tasks.filter(data.Task.offices.contains(office))


    return render_template('touch.html')


@core.route('/planning')
def planning():

    return render_template('planning.html')

@core.route('/pult')



def pult():
    access = data.Stud_access.query.all()

    data.Stud_access.query.delete()
    db.session.commit()
    volna= 1
    i=1
    ab = 10 #длительность экзамена
    ac = 8 #длительность перерыва
    t = ab + ac  # время волны
    room_1= ["1.15","1.14","1.9","1.3","1.12"]
    room_2= ["1.1","1.4","1.6","1.2","1.10"]
    room_3= []
    special= "Лечебное дело"
    h=1
    m=2 #количество потоков (не больше 3)
    pereriv = 3 #кол-во волн до перерыва
    pereriv_c = 0
    pereriv_m = 30
    cx = 9  # час начала экзаменов
    mx = 0  # минута начала
    rx = cx
    fx = mx
    max = data.Student.query.count()
    while i<=max:

        test = data.Student.query.filter_by(id=i).all()
        n=0
        while n < len(room_1):
                hl = rx
                hm = fx + ab

                if hm>=60:
                    hm=hm%60
                    hl+=1
                if len(str(hl)) == 1:
                    pm = "0" + str(hl)
                else:
                    pm = str(hl)
                if len(str(hm)) == 1:
                    pl = "0" + str(hm)
                else:
                    pl = str(hm)



                if len(str(rx)) == 1:
                    km = "0" + str(rx)
                else:
                    km = str(rx)

                if fx == 0:
                    kl = str(fx) + "0"
                else:
                    kl = str(fx)
                if i%m==m-1:

                    add_stud = data.Stud_access(id=h,
                                                id_stud=test[0].id,
                                                room=room_1[n],
                                                student=test[0].name,
                                                time_begin=km+":"+kl,
                                                time_end=pm+":"+pl,
                                                specialization=special,
                                                flow=1,
                                                )
                    shift(room_1, -1)
                elif i%m==m-2:
                    add_stud = data.Stud_access(id=h,
                                                id_stud=test[0].id,
                                                room=room_2[n],
                                                student=test[0].name,
                                                time_begin=km+":"+kl,
                                                time_end=pm+":"+pl,
                                                specialization=special,
                                                flow=2,
                                                )
                    shift(room_2, -1)
                elif i%m==m-3:
                    add_stud = data.Stud_access(id=h,
                                                id_stud=test[0].id,
                                                room=room_3[n],
                                                student=test[0].name,
                                                time_begin=km+":"+kl,
                                                time_end=pm+":"+pl,
                                                specialization=special,
                                                flow=3,
                                                )
                    shift(room_3, -1)

                fx+=t
                if fx>=60:
                    fx=fx%60
                    rx+=1


                n += 1
                h += 1


                db.session.add(add_stud)
                db.session.commit()
        if bool(room_1) != False: shift(room_1, -1)
        if bool(room_2) != False: shift(room_2, -1)
        if bool(room_3) != False: shift(room_3, -1)
        if i % (len(room_1)+len(room_2)+len(room_3)) == 0 and volna == pereriv:
            fx += pereriv_m
            rx += pereriv_c
            if fx >= 60:
                fx = fx % 60
                rx += 1
            cx = rx
            mx = fx
            volna += 1
        elif i % (len(room_1)+len(room_2)+len(room_3)) == 0 and volna != pereriv:
            cx = rx
            mx = fx
            volna += 1


        rx = cx
        fx = mx
        i += 1

    return render_template('tablo2.html')
def create():

    os.mknod(r'C:\Users\1\Pictures\rezerv\2.txt')
def delete():
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), r'C:\Users\1\Pictures\rezerv\2.txt')

    return os.remove(path)

@core.route('/regist')
@core.route('/regist/en')
@core.route('/regist/ru')
def regist():
    print('regist')
    return render_template('regist.html')

@core.route('/view-ticket/<sernomer>')
def render_ticket_view(sernomer):
    #studentService = StudentService()
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    c = a+b
    d1 = c.strftime("%d.%m.%Y")

    suppose_student = data.Student.query.filter(data.Student.date == d1).filter(data.Student.ser_nomer == sernomer).all()
    if bool(suppose_student) != 0:
        id_st = suppose_student[0].person_id
        student_with_access = data.Stud_access.query.filter(data.Stud_access.date == d1).filter(data.Stud_access.id_stud == id_st).all()
        
        if bool(student_with_access) == 0:
            return redirect(url_for('core.render_error_page', page_title='Ошибка', error_title='Ошибка', error_message='По указанным данным студент не найден'))
        
        parsec_code = get_parsec_code(id_st)
        qr_code = generate_qr_code(parsec_code)

        redirect_print_url = f'/print-ticket/{sernomer}/{id_st}'

        return render_template('ticket/ticket.html', student=student_with_access, qr_code=qr_code, redirect_to_print_url=redirect_print_url)
    else:
        return redirect(url_for('core.render_error_page', page_title='Ошибка', error_title='Ошибка', error_message='Студент с указанным номером паспорта не найден'))

@core.route('/print-ticket/<sernomer>/<int:id_stud>')
def render_print_view(sernomer, id_stud):
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    m = timedelta(hours=3, minutes=1)
    k = timedelta(hours=3, minutes=0)
    c = a+b #отображение студента с задержкой в 5 минут
    j = a+m #время для оповещения за 1 минуту до окончания
    o = a+k #текущее время
    d1 = c.strftime("%d.%m.%Y")
    redir="/touch/ru"

    #studentService = StudentService()

    #student = studentService.get_student_by_serial_code(serial_code=sernomer)
    if id_stud == 1:
        redir="/vvesti"
    # client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    suppose_student = data.Student.query.filter(data.Student.date == d1).filter(data.Student.ser_nomer == sernomer).all()
    if bool(suppose_student) != 0:
        id_st = suppose_student[0].person_id
        student_with_access = data.Stud_access.query.filter(data.Stud_access.date == d1).filter(data.Stud_access.id_stud == id_st).all()
        # domain = "SYSTEM"
        # nameuser = "parsec"
        # password = "parsec"
        # session = (client.service.OpenSession(domain, nameuser, password))
        # sessionID = session.Value.SessionID
        # lastname = "Student"
        # firstname = id_st
        # buf = (client.service.FindPeople(sessionID, lastname, firstname))
        # PERSON_ID = buf[0].ID
        # code1 = (client.service.GetPersonIdentifiers(sessionID, PERSON_ID))
        # CODE = code1[0].CODE
        # decimal = int(CODE, 16)
        parsec_code = get_parsec_code(id_st)

        if bool(student_with_access) == 0:
            return redirect(url_for('core.render_error_page', page_title='Ошибка', error_title='Ошибка', error_message='По указанным данным студент не найден'))
        
        qr_code = generate_qr_code(parsec_code)
        return render_template('print-ticket/print-ticket.html', student=student_with_access, qr_code=qr_code, redirect_url=redir)
    else:
        return redirect(url_for('core.render_error_page', page_title='Ошибка', error_title='Ошибка', error_message='На сегодня для вас нет запланированного экзамена'))

@core.route('/error-ticket/')
def render_error_page():
    return render_template('error-page.html',
                           page_title=request.args['page_title'],
                           error_title=request.args['error_title'],
                           error_message=request.args['error_message']
                           )


@core.route('/reg/<sernomer>')
def regist_go(sernomer):
    a = datetime.datetime.now()
    b = timedelta(hours=3, minutes=0)
    c = a + b  # отображение студента с задержкой в 5 минут
    d1 = c.strftime("%d.%m.%Y")
    connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD, database=DATABASE_NAME)
    cursor = connection.cursor()
    """ cursor.execute("SELECT * FROM student WHERE ser_nomer = (%s) AND date = (%s) ", (sernomer,d1)) """
    cursor.execute("SELECT * FROM student WHERE ser_nomer = (%s) ", (sernomer))
    name = cursor.fetchall()
    connection.close()

    if (name == ()):
        return redirect('/touch')
    
    
    return render_template('helloallok.html', test=name)
@core.route('/printf/<sernomer>', defaults={'id': None})
@core.route('/printf/<sernomer>/<int:id>')
def printf(sernomer, id):
    a = datetime.datetime.now()
    b = timedelta(hours=2, minutes=55)
    m = timedelta(hours=3, minutes=1)
    k = timedelta(hours=3, minutes=0)
    c = a+b #отображение студента с задержкой в 5 минут
    j = a+m #время для оповещения за 1 минуту до окончания
    o = a+k #текущее время
    d1 = c.strftime("%d.%m.%Y")
    redir="touch/ru"
    if id == 1:
        redir="vvesti"
    # client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    test1 = data.Student.query.filter(data.Student.date == d1).filter(data.Student.ser_nomer == sernomer).all()
    if bool(test1) != 0:
        id_st = test1[0].person_id
        test2 = data.Stud_access.query.filter(data.Stud_access.date == d1).filter(data.Stud_access.id_stud == id_st).all()
        # domain = "SYSTEM"
        # nameuser = "parsec"
        # password = "parsec"
        # session = (client.service.OpenSession(domain, nameuser, password))
        # sessionID = session.Value.SessionID
        # lastname = "Student"
        # firstname = id_st
        # buf = (client.service.FindPeople(sessionID, lastname, firstname))
        # PERSON_ID = buf[0].ID
        # code1 = (client.service.GetPersonIdentifiers(sessionID, PERSON_ID))
        # CODE = code1[0].CODE
        # decimal = int(CODE, 16)
        return render_template('printf.html', test=test2, code=1234, redir=redir)
    else:
        return render_template('printf.html', test=1, code=1, redir=redir)

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

@core.route('/logo')
def logo():
    voices = tts.getProperty('voices')
    tts.setProperty('voice', 'ru')
    tts.setProperty('rate', '100')
    tts.save_to_file('Здарова' , 'test4.mp3')
    tts.runAndWait()
    return render_template('logo.html')


@core.route('/video_feed/<setting>')
def video(setting):
    test = data.Student.query.filter_by(ser_nomer=setting).all()
    path = '/home/adminsuo/FQM-0.9/static/photo/'+setting
    if os.path.isdir(path):
        files = os.listdir(path)
        return render_template('face.html', setting=setting, files=files)
    else:
        files = ""
        return render_template('face1.html')