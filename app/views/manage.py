from flask import url_for, flash, request, render_template, redirect, Blueprint
import os
import zipfile
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
from datetime import datetime, date, time, timedelta
import csv
from app.views.schedule import access, schedule1, createperson
import app.database as data
from app.middleware import db
from app.utils import ids, remove_string_noise
from app.helpers import (reject_operator, reject_no_offices, is_operator, is_office_operator,
                         is_common_task_operator, reject_setting, get_or_reject, decode_links)
#from app.forms.manage import OfficeForm, TaskForm, SearchForm, ProcessedTicketForm
from app.constants import TICKET_WAITING


manage_app = Blueprint('manage_app', __name__)

#path= "C:/Users/tasdid/Desktop/TEST"
path= "/home/adminsuo/FQM-0.9/static/photo"
#path= "C:/adminsuo/09sep/static/photo"
UPLOAD_PAPKA = os.path.realpath(path)

ALLOWED_EXTENSIONS = set(['zip'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@manage_app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            zip_ref = zipfile.ZipFile(os.path.join(UPLOAD_FOLDER, filename), 'r')
            zip_ref.extractall(UPLOAD_PAPKA)
            zip_ref.close()
            flash("ZIP Uploaded Successfully")
            return redirect(url_for('manage_app.upload_file',
                                    filename=filename))



    return render_template('picin.html')

def shift(lst, steps):
    if steps < 0:
        steps = abs(steps)
        for i in range(steps):
            lst.append(lst.pop(0))
    else:
        for i in range(steps):
            lst.insert(0, lst.pop())

UPLOAD_FOLDER = '/home/adminsuo/DOCS'
@manage_app.route('/manage')
@login_required
def manage():
    ''' management welcome screen. '''
    
    return render_template('manage.html',
                           page_title='Management',
                           navbar='#snb1',
                           ooid=0,  # NOTE: filler to collapse specific office
                       #    serial=data.Serial.all_clean(),
                     #      offices=data.Office.query,
                   #        operators=data.Operators.query,
                  #         tasks=data.Task
                           )


@manage_app.route('/all_offices')
@login_required
@reject_operator
def all_offices():
    ''' lists all offices. '''
    page = request.args.get('page', 1, type=int)
    tickets = None
    pagination = tickets.paginate(page, per_page=10, error_out=False)
    last_ticket_pulled = tickets.filter_by(p=True).first()
    last_ticket_office = last_ticket_pulled and data.Office.query\
                                                    .filter_by(id=last_ticket_pulled.office_id)\
                                                    .first()
    tickets_form = ()

    return render_template('all_offices.html',
                           officesp=pagination.items,
                           pagination=pagination,
                           len=len,
                           page_title='All Offices',
                         #  serial=data.Serial.all_clean(),
                         #  offices=data.Office.query,
                           tasks=data.Task,
                           users=data.User.query,
                           operators=data.Operators.query,
                           navbar='#snb1',
                           hash='#da2',
                           last_ticket_pulled=last_ticket_pulled,
                           last_ticket_office=last_ticket_office,
                           tickets_form=tickets_form)


@manage_app.route('/offices/<int:o_id>', methods=['GET', 'POST'])
@login_required
@reject_setting('single_row', True)
@get_or_reject()
def offices(office):
    ''' view and update an office. '''
    if is_operator() and not is_office_operator(office.id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

  #  form = OfficeForm(current_prefix=office.prefix)
  #  tickets_form = ProcessedTicketForm()
    page = request.args.get('page', 1, type=int)
    tickets = data.Serial.all_office_tickets(office.id)
    last_ticket_pulled = tickets.filter_by(p=True).first()
    pagination = tickets.paginate(page, per_page=10, error_out=False)
 #   office_name = remove_string_noise(form.name.data or '',
   #                                   lambda s: s.startswith('0'),
   #                                   lambda s: s[1:]) or None

    if form.validate_on_submit():
        if not office.is_valid_new_name(office_name):
            flash('Error: name is used by another one, choose another name', 'danger')
            return redirect(url_for('manage_app.offices', o_id=office.id))

        office = data.Office.get(office.id)  # NOTE: DB session is lost
        office.name = office_name
        office.prefix = form.prefix.data.upper()
        db.session.commit()
        flash('Notice: office has been updated. ', 'info')
        return redirect(url_for('manage_app.offices', o_id=office.id))

    form.name.data = office.name
    form.prefix.data = office.prefix.upper()

    return render_template('offices.html',
                           form=form,
                           officesp=pagination.items,
                           pagination=pagination,
                           page_title='Office : ' + office.prefix + str(office.name),
                           o_id=office.id,
                           ooid=office,
                           len=len,
                           serial=tickets,
                           offices=data.Office.query,
                           tasks=data.Task,
                           users=data.User.query,
                           operators=data.Operators.query,
                           navbar='#snb1',
                           dropdown='#dropdown-lvl' + str(office.id),
                           hash='#t1' + str(office.id),
                           last_ticket_pulled=last_ticket_pulled,
                           tickets_form=tickets_form)


@manage_app.route('/office_a', methods=['GET', 'POST'])
@login_required
@reject_operator
@reject_setting('single_row', True)
def office_a():
    ''' add an office. '''
    form = OfficeForm()
    office_name = remove_string_noise(form.name.data or '',
                                      lambda s: s.startswith('0'),
                                      lambda s: s[1:]) or None

    if form.validate_on_submit():
        if data.Office.query.filter_by(name=form.name.data).first():
            flash('Error: name is used by another one, choose another name', 'danger')
            return redirect(url_for('manage_app.all_offices'))

        db.session.add(data.Office(office_name, form.prefix.data.upper()))
        db.session.commit()
        flash('Notice: new office been added . ', 'info')
        return redirect(url_for('manage_app.all_offices'))

    return render_template('office_add.html',
                           form=form,
                           page_title='Adding new office',
                           offices=data.Office.query,
                           tasks=data.Task,
                           operators=data.Operators.query,
                           navbar='#snb1',
                           hash='#da3',
                           serial=data.Serial.all_clean())


@manage_app.route('/office_d/<int:o_id>')
@login_required
@reject_operator
@reject_setting('single_row', True)
@get_or_reject()
def office_d(office):
    ''' delete office and its belongings. '''
    if office.tickets.count():
        flash('Error: you must reset it, before you delete it ', 'danger')
        return redirect(url_for('manage_app.offices', o_id=office.id))

    office.delete_all()
    flash('Notice: office and its all tasks been deleted ', 'info')
    return redirect(url_for('manage_app.all_offices'))


@manage_app.route('/office_da')
@login_required
@reject_operator
@reject_no_offices
@reject_setting('single_row', True)
def office_da():
    ''' delete all offices and their belongings.'''
    if data.Serial.query.filter(data.Serial.number != 100).count():
        flash('Error: you must reset it, before you delete it ', 'danger')
        return redirect(url_for('manage_app.all_offices'))

    data.Serial.query.delete()
    data.Task.query.delete()
    data.Office.query.delete()
    db.session.commit()
    flash('Notice: office and its all tasks been deleted ', 'info')
    return redirect(url_for('manage_app.all_offices'))


@manage_app.route('/search', methods=['GET', 'POST'])
@login_required
@reject_operator
def search():
    ''' search for tickets. '''
    search_kwargs = {}
    first_time = not bool(request.args.get('page', default=0, type=int))
    form = SearchForm() if first_time else search.form
    base_template_arguments = dict(form=form, page_title='Tickets search', offices=data.Office.query,
                                   tasks=data.Task, users=data.User.query, len=len,
                                   operators=data.Operators.query, navbar='#snb1', hash='#da1',
                                   serial=data.Serial.query.filter(data.Serial.number != 100))

    # NOTE: storing the first form submitted as an endpoint attr instead of a global variable
    if first_time:
        setattr(search, 'form', form)

    if form.validate_on_submit() or not first_time:

        for form_data, keyword_argument in [
            (form.number.data, {'number': form.number.data}),
            (form.date.data, {'date': form.date.data and form.date.data.strftime('%Y-%m-%d')}),
            (form.tl.data, {'office_id': form.tl.data})
        ]:
            if form_data and str(form_data).strip():
                search_kwargs.update(keyword_argument)

        if not search_kwargs:
            flash('Error: fault in search parameters', 'danger')
            return redirect(url_for('manage_app.search'))

        tickets_found = data.Serial.query.filter(data.Serial.number != 100)\
                                         .filter_by(**search_kwargs)

        if not tickets_found.first():
            flash('Notice: Sorry, no matching results were found ', 'info')
            return redirect(url_for('manage_app.search'))

        page = request.args.get('page', 1, type=int)
        pagination = tickets_found.order_by(data.Serial.timestamp.desc())\
                                  .paginate(page, per_page=10, error_out=False)

        return render_template('search_r.html', serials=tickets_found, pagination=pagination,
                               serialsp=pagination.items, **base_template_arguments)

    return render_template('search.html', **base_template_arguments)


@manage_app.route('/task/<int:o_id>', methods=['POST', 'GET'], defaults={'ofc_id': None})
@manage_app.route('/task/<int:o_id>/<int:ofc_id>', methods=['POST', 'GET'])
@login_required
@reject_setting('single_row', True)
@get_or_reject()
def task(task, ofc_id):
    ''' view specific task. '''
    if is_operator() and not is_common_task_operator(task.id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    task = data.Task.get(task.id)  # NOTE: session's lost
    form = TaskForm(common=task.common)
    tickets_form = ProcessedTicketForm()
    page = request.args.get('page', 1, type=int)
    tickets = data.Serial.all_task_tickets(ofc_id, task.id)
    last_ticket_pulled = tickets.filter_by(p=True).first()
    pagination = tickets.paginate(page, per_page=10, error_out=False)

    if form.validate_on_submit():
        if data.Task.query.filter_by(name=form.name.data).count() > 1:
            flash('Error: name is used by another one, choose another name', 'danger')
            return redirect(url_for('manage_app.task', o_id=task.id, ofc_id=ofc_id))

        task = data.Task.get(task.id)
        task.name = form.name.data
        task.hidden = form.hidden.data

        if task.common:
            checked_offices = [o for o in data.Office.query.all() if form[f'check{o.id}'].data]
            removed_offices = [o for o in task.offices if o.id not in ids(checked_offices)]
            to_add_offices = [o for o in checked_offices if o.id not in ids(task.offices)]

            if not checked_offices:
                flash('Error: one office must be selected at least', 'danger')
                return redirect(url_for('manage_app.common_task_a'))

            for office in removed_offices:
                task.migrate_tickets(office, checked_offices[0])
                task.offices.remove(office)

            for office in to_add_offices:
                task.offices.append(office)

        db.session.commit()
        flash('Notice: task has been updated .', 'info')
        return redirect(url_for('manage_app.task', o_id=task.id, ofc_id=ofc_id))

    if not form.errors:
        form.name.data = task.name
        form.hidden.data = task.hidden

        for office in task.offices:
            form[f'check{office.id}'].data = True

    if not ofc_id:
        # NOTE: sidebar collapse failsafe, just incase the office id wasn't passed
        ofc_id = task.offices[0].id

    return render_template('tasks.html',
                           form=form,
                           page_title='Task : ' + task.name,
                           tasksp=pagination.items,
                           pagination=pagination,
                           serial=tickets,
                           o_id=task.id,
                           ofc_id=ofc_id,
                           common=task.common,
                           len=len,
                           offices=data.Office.query,
                           tasks=data.Task,
                           users=data.User.query,
                           operators=data.Operators.query,
                           task=task,
                           navbar='#snb1',
                           dropdown='#dropdown-lvl%i' % ofc_id,  # dropdown a list of offices
                           hash='#tt%i%i' % (ofc_id, task.id),
                           last_ticket_pulled=last_ticket_pulled,
                           edit_task=len(task.offices) == 1 or not is_operator(),
                           office=data.Office.get(ofc_id),
                           tickets_form=tickets_form)


@manage_app.route('/task_d/<int:t_id>', defaults={'ofc_id': None})
@manage_app.route('/task_d/<int:t_id>/<int:ofc_id>')
@login_required
@reject_setting('single_row', True)
@get_or_reject()
def task_d(task, ofc_id):
    ''' to delete a task '''
    if is_operator() and not is_common_task_operator(task.id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    tickets = data.Serial.query.filter(data.Serial.task_id == task.id)

    if tickets.filter(data.Serial.number != 100).count() > 0:
        flash('Error: you must reset it, before you delete it ', 'danger')
        return redirect(url_for('manage_app.task', o_id=task.id, ofc_id=ofc_id))

    tickets.delete()
    db.session.delete(task)
    db.session.commit()
    flash('Notice: task has been deleted .', 'info')
    return redirect(url_for('manage_app.offices', o_id=ofc_id)
                    if ofc_id else
                    url_for('manage_app.all_offices'))


@manage_app.route('/common_task_a', methods=['GET', 'POST'])
@login_required
@reject_operator
@reject_no_offices
@reject_setting('single_row', True)
def common_task_a():
    ''' to add a common task '''
    form = TaskForm(common=True)

    if form.validate_on_submit():
        task = data.Task(form.name.data, form.hidden.data)

        if data.Task.query.filter_by(name=form.name.data).first() is not None:
            flash('Error: name is used by another one, choose another name', 'danger')
            return redirect(url_for('manage_app.common_task_a'))

        offices_validation = [form[f'check{o.id}'].data for o in data.Office.query.all()]
        if len(offices_validation) > 0 and not any(offices_validation):
            flash('Error: one office must be selected at least', 'danger')
            return redirect(url_for('manage_app.common_task_a'))

        db.session.add(task)
        db.session.commit()

        for office in data.Office.query.all():
            if form['check%i' % office.id].data and office not in task.offices:
                task.offices.append(office)

        for office in task.offices:
            initial_ticket = data.Serial.query\
                                 .filter_by(office_id=office.id, number=100)\
                                 .first()

            if not initial_ticket:
                db.session.add(data.Serial(office_id=office.id,
                                           task_id=task.id,
                                           p=True))

        db.session.commit()
        flash('Notice: a common task has been added.', 'info')
        return redirect(url_for('manage_app.all_offices'))
    return render_template('task_add.html', form=form,
                           offices=data.Office.query,
                           serial=data.Serial.all_clean(),
                           tasks=data.Task,
                           operators=data.Operators.query,
                           navbar='#snb1', common=True,
                           page_title='Add a common task',
                           hash='#da6')


@manage_app.route('/task_a/<int:o_id>', methods=['GET', 'POST'])
@manage_app.route('/task_a/<int:o_id>', methods=['GET', 'POST'])
@login_required
@reject_setting('single_row', True)
@get_or_reject()
def task_a(office):
    ''' to add a task '''
    form = TaskForm()

    if is_operator() and not is_office_operator(office.id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    if form.validate_on_submit():
        if data.Task.query.filter_by(name=form.name.data).first() is not None:
            flash('Error: name is used by another one, choose another name', 'danger')
            return redirect(url_for('manage_app.task_a', o_id=office.id))

        task = data.Task(form.name.data, form.hidden.data)
        db.session.add(task)
        db.session.commit()

        if office.id not in ids(task.offices):
            task.offices.append(office)
            db.session.commit()

        initial_ticket = data.Serial.query.filter_by(task_id=task.id,
                                                     office_id=office.id,
                                                     number=100)\
                                          .first()

        if not initial_ticket:
            db.session.add(data.Serial(office_id=task.offices[0].id,
                                       task_id=task.id,
                                       p=True))
            db.session.commit()

        flash('Notice: New task been added.', 'info')
        return redirect(url_for('manage_app.offices', o_id=office.id))
    return render_template('task_add.html', form=form,
                           offices=data.Office.query,
                           serial=data.Serial.all_clean(),
                           tasks=data.Task,
                           operators=data.Operators.query,
                           navbar='#snb1', common=False,
                           dropdown='#dropdown-lvl' + str(office.id),
                           hash='#t3' + str(office.id),
                           page_title='Add new task')


@manage_app.route('/serial_u/<int:ticket_id>/<redirect_to>', methods=['POST'], defaults={'o_id': None})
@manage_app.route('/serial_u/<int:ticket_id>/<redirect_to>/<int:o_id>', methods=['POST'])
@login_required
@decode_links
def serial_u(ticket_id, redirect_to, o_id=None):
    ''' to update ticket details '''
    if is_operator() and not is_office_operator(o_id):
        flash('Error: operators are not allowed to access the page ', 'danger')
        return redirect(url_for('core.root'))

    form = ProcessedTicketForm()
    ticket = data.Serial.get(ticket_id)

    if not ticket:
        flash('Error: wrong entry, something went wrong', 'danger')
        return redirect(redirect_to)

    if form.validate_on_submit():
        ticket.name = form.value.data or ''
        ticket.n = not form.printed.data
        ticket.status = form.status.data

        if ticket.status == TICKET_WAITING:
            ticket.p = False

        db.session.commit()

    flash('Notice: Ticket details updated successfully', 'info')
    return redirect(redirect_to)

@manage_app.route('/student_list', methods=['GET', 'POST'] )
@login_required
def student_list():
    #if request.method == "POST":
     #   name = request.form.get('name')
      #  ser_nomer = request.form.get('ser_nomer')
      #  specialization_id = request.form.get('specialization_id')
      #  personal_number = request.form.get('personal_number')
      #  photo = request.form.get('photo')
      #  file = request.files['file']
      #  filename = secure_filename(file.filename)
      #  file.save(os.path.join(UPLOAD_FOLDER, filename))

      #  student = data.Student(name=name, ser_nomer=ser_nomer, specialization_id=specialization_id, personal_number=personal_number, photo=photo)

       # try:
       #     data.Student.session.add(student)
       #     data.Student.session.commit()
       # except:
       #     return "Ошибка"
       # return render_template('student.html')
    #else:
         return render_template('student.html')

@manage_app.route('/raspis', methods=['GET', 'POST'] )
@login_required
def raspis():
    if request.method == "POST":
        ra = data.Stud_access.query.all()
        raa = data.Stud_access.query.all()
        return render_template('raspisaniye.html', ra=ra, raa=raa)
    else:
        ra = data.Stud_access.query.all()
        raa = data.Stud_access.query.all()
        return render_template('raspisaniye.html', ra=ra, raa=raa)


@manage_app.route('/monik', methods=['GET', 'POST'] )
@login_required
def monik():
    if request.method == "POST":
        mon = data.Stud_access.query.all()
        return render_template('monitors.html', mon=mon)
    else:
        mon = data.Stud_access.query.all()
        return render_template('monitors.html', mon=mon)

@manage_app.route('/cabin', methods=['GET', 'POST'] )
@login_required
def cabin():
    a = datetime.now()

    b = timedelta(hours=3, minutes=0)
    c = a + b
    d1 = c.strftime("%d.%m.%Y")
    if request.method == "POST":
        cab = data.Room.query.all()
        cabs = data.Stud_access.query.filter(data.Stud_access.date==d1).all()
        return render_template('cabinate.html', cab=cab, cabs=cabs)
    else:
        cab = data.Room.query.all()
        cabs = data.Stud_access.query.filter(data.Stud_access.date==d1).all()
        return render_template('cabinate.html', cab=cab, cabs=cabs)

@manage_app.route('/histo', methods=['GET', 'POST'] )
@login_required
def histo():
    if request.method == "POST":
        hist = data.History.query.order_by(data.History.id.desc()).all()
        return render_template('history.html', hist=hist)
    else:
        hist = data.History.query.order_by(data.History.id.desc()).all()
        return render_template('history.html', hist=hist)

@manage_app.route('/poisk_a', methods=['GET', 'POST'] )
@login_required
def poisk_a():
    if request.method == "POST":
        po = data.Stud_access.query.all()
        return render_template('poisk.html', po=po)
    else:
        po = data.Stud_access.query.all()
        return render_template('poisk.html', po=po)

@manage_app.route('/stationsb_sb', methods=['GET', 'POST'] )
@login_required
def stationsb_sb():
    if request.method == "POST":
         return render_template('stationsb.html')
    else:
        return render_template('stationsb.html')
@manage_app.route('/specsb_sb', methods=['GET', 'POST'] )
@login_required
def specsb_sb():
    if request.method == "POST":
        return render_template('specsb.html')
    else:
        return render_template('specsb.html')

@manage_app.route('/dobavit', methods=['GET', 'POST'])
@login_required
def dobavit():
    if request.method == "POST":
        date = request.form.get("date")
        if date == '':
            return render_template('dobavit.html')
        file = request.files['file']
        if file.filename == '':
            return render_template('dobavit.html')
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        data.Student.query.filter_by(date=date).delete()
        db.session.commit()

        with open(UPLOAD_FOLDER + "/" + filename, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                add_stud = data.Student(person_id=row['person_id'],
                                            name=row['name'],
                                            specialization_id=row['specialization'],
                                            ser_nomer=row['ser_nomer'],
                                            #personal_number=row['personal_number'],
                                            date=date,
                                            )
                db.session.add(add_stud)
                db.session.commit()
        return render_template('dobavit.html')
    else:
        return render_template('dobavit.html')
@manage_app.route('/speci_a', methods=['GET', 'POST'])
@login_required
def speci_a():
    if request.method == "POST":
        spez = data.Specialization.query.all()
        speza = data.Station.query.all()
        return render_template('speci.html', spez=spez, speza=speza)
    else:
        spez = data.Specialization.query.all()
        speza = data.Station.query.all()
        return render_template('speci.html', spez=spez, speza=speza)



    # insert data to mysql database via html forms
@manage_app.route('/inzert', methods=['POST'])
def inzert():
    if request.method == 'POST':
        #id = request.form['id']
        name = request.form['name']

        spez = data.Specialization(name=name)
        db.session.add(spez)
        db.session.commit()

        flash("Specialization Inserted Successfully")
        return redirect(url_for('manage_app.speci_a'))

# delete spe
@manage_app.route('/delet/<int:id>', methods=['GET', 'POST'])
def delet(id):

    data.Specialization.query.filter_by(id=id).delete()
    db.session.commit()
    flash("Specialization Deleted Successfully")
    return redirect(url_for('manage_app.speci_a'))

if __name__ == "__main__":

    app.run(debug=True)

@manage_app.route('/dlt/<int:id>', methods=['GET', 'POST'])
def dlt(id):

    data.Station.query.filter_by(id=id).delete()
    db.session.commit()
    flash("Deleted Successfully")
    return redirect(url_for('manage_app.speci_a'))

if __name__ == "__main__":

    app.run(debug=True)


# update spe
@manage_app.route('/updet/<int:id>', methods=['GET', 'POST'])
def updet(id):
    if request.method == 'POST':
        name = request.form['name']

        spez = data.Specialization(id=id, name=name)
        data.Specialization.query.filter_by(id=id).update({'id': id, 'name': name})
        db.session.commit()
        flash("Specialization Updated Successfully")
        return redirect(url_for('manage_app.speci_a'))

@manage_app.route('/upde/<int:id>', methods=['GET', 'POST'])
def upde(id):
    if request.method == 'POST':
        spec_id = request.form['spec_id']
        room = request.form['room']
        name = request.form['name']
        briefing = request.form['briefing']

        speza = data.Station(id=id, spec_id=spec_id, room=room, name=name, briefing=briefing)
        data.Station.query.filter_by(id=id).update({'id': id, 'spec_id': spec_id, 'room': room, 'name': name, 'briefing': briefing})
        db.session.commit()
        flash("Updated Successfully")
        return redirect(url_for('manage_app.speci_a'))



@manage_app.route('/vvesti', methods=['GET', 'POST'])
@login_required
def vvesti():
    if request.method == "POST":
        stud = data.Student.query.order_by(data.Student.id.desc()).all()
        specialization = data.Specialization.query.all()
        return render_template('vvesti.html', stud=stud, specialization=specialization)
    else:
        stud = data.Student.query.order_by(data.Student.id.desc()).all()
        specialization = data.Specialization.query.all()
        return render_template('vvesti.html', stud=stud, specialization=specialization)


# insert data to mysql database via html forms
@manage_app.route('/insert', methods=['POST'])
def insert():
    if request.method == 'POST':
        #id = request.form['id']
        name = request.form['name']
        specialization_id = request.form['specialization_id']
        ser_nomer = request.form['ser_nomer']
        person_id = request.form['personal_number']
        date = request.form['date']

        stud = data.Student(name=name, specialization_id=specialization_id, ser_nomer=ser_nomer, personal_number=person_id, person_id=person_id, date=date)
        db.session.add(stud)
        db.session.commit()

        flash("Student Inserted Successfully")
        return redirect(url_for('manage_app.vvesti'))


@manage_app.route('/ins', methods=['POST'])
def ins():
    if request.method == 'POST':
        #id = request.form['id']
        spec_id = request.form['spec_id']
        name = request.form['name']
        briefing = request.form['briefing']
        room = request.form['room']

        speza = data.Station(name=name, spec_id=spec_id, room=room, briefing=briefing)
        db.session.add(speza)
        db.session.commit()

        flash("Student Inserted Successfully")
        return redirect(url_for('manage_app.speci_a'))

# delete student
@manage_app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):

    data.Student.query.filter_by(id=id).delete()
    db.session.commit()
    flash("Student Deleted Successfully")
    return redirect(url_for('manage_app.vvesti'))


if __name__ == "__main__":

    app.run(debug=True)


# update student
@manage_app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if request.method == 'POST':

        name = request.form['name']
        specialization_id = request.form['specialization_id']
        ser_nomer = request.form['ser_nomer']
        person_id = request.form['personal_number']
        date = request.form['date']
        #stud = data.Student(id=id, name=name, specialization_id=specialization_id, ser_nomer=ser_nomer, personal_number=personal_number, date=date)
        data.Student.query.filter_by(id=id).update({'id':id, 'name':name, 'specialization_id':specialization_id, 'ser_nomer':ser_nomer, 'personal_number':person_id, 'person_id': person_id, 'date':date})
        db.session.commit()
        flash("Student Updated Successfully")
        return redirect(url_for('manage_app.vvesti'))


@manage_app.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    if request.method == "POST":
        print(request)
        specialization = data.Specialization.query.all()
        date = request.form.get('date')  # Дата
        special = request.form.get('special')  # специальность
        stud = data.Student.query.filter_by(date=date).filter_by(specialization_id=special).all()
        stud1 = data.Student.query.filter_by(date=date).count()
        try:
            createperson(stud1)
        except Exception:
            pass
        stud_acc = data.Stud_access.query.filter_by(date=date).filter_by(specialization=special).delete()
        stud_a = data.Stud_access.query.filter_by(date=date).order_by(data.Stud_access.id_stud.desc()).all()
        #if bool(stud_acc) != 0:
         #   db.session.delete(stud_acc)
        db.session.commit()
        volna = 1
        i = 1
        ab = int(request.form.get('time_ek'))  # длительность экзамена  # длительность экзамена
        ac = int(request.form.get('time_pod')) # длительность экзамена  # длительность перерыва
        t = ab + ac  # время волны
        room_11 = request.form.getlist("contact[]")
        room_1 = []
        print(room_11)
        print(len(room_1))
        for l,o in enumerate(room_11):
            if o != "": room_1.append(o)
        room_22 = request.form.getlist("contact2[]")
        room_2 = []
        for l,o in enumerate(room_22):
            if o != "": room_2.append(o)
        room_33 = request.form.getlist("contact3[]")
        room_3 = []
        for l,o in enumerate(room_33):
            if o != "": room_3.append(o)

        h = 1
        m = int(request.form.get('count_p'))  # количество потоков (не больше 3)

        pereriv = int(request.form.get('break1'))  # кол-во волн до перерыва
        pereriv_c = int(request.form.get('break2'))
        pereriv_m = int(request.form.get('break3'))
        cx = int(request.form.get('nd'))  # час начала дня
        mx = int(request.form.get('ndx')) # минута конца дня
       # time_end_h = int(request.form.get('pwd')) # час конца дня
       # time_end_m = int(request.form.get('pwdx')) # минута конца дня

        rx = cx #час
        fx = mx #минута
        max = data.Student.query.filter_by(date=date).filter_by(specialization_id=special).count()
        while i <= max:

            test = data.Student.query.filter_by(date=date).filter_by(specialization_id=special).all()
            n = 0
            while n < len(room_1):
                hl = rx
                hm = fx + ab

                if hm >= 60:
                    hm = hm % 60
                    hl += 1
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

                if len(str(fx)) == 1:
                    kl = "0" + str(fx) 
                else:
                    kl = str(fx)
                if i % m == m - 1:

                    add_stud = data.Stud_access(
                                                id_stud=test[i-1].person_id,
                                                room=room_1[n],
                                                student=test[i-1].name,
                                                time_begin=km + ":" + kl,
                                                time_end=pm + ":" + pl,
                                                specialization=special,
                                                date=test[0].date,
                                                flow=1,
                                                )
                elif i % m == m - 2:
                    add_stud = data.Stud_access(
                                                id_stud=test[i-1].person_id,
                                                room=room_2[n],
                                                student=test[i-1].name,
                                                time_begin=km + ":" + kl,
                                                time_end=pm + ":" + pl,
                                                specialization=special,
                                                date=test[0].date,
                                                flow=2,
                                                )

                elif i % m == m - 3:
                    add_stud = data.Stud_access(
                                                id_stud=test[i-1].person_id,
                                                room=room_3[n],
                                                student=test[i-1].name,
                                                time_begin=km + ":" + kl,
                                                time_end=pm + ":" + pl,
                                                specialization=special,
                                                date=test[0].date,
                                                flow=3,
                                                )


                fx += t
                if fx >= 60:
                    fx = fx % 60
                    rx += 1

                n += 1
                h += 1

                db.session.add(add_stud)
                db.session.commit()
            if i % m == 0:
                if bool(room_1) != False: shift(room_1, 1)
                if bool(room_2) != False: shift(room_2, 1)
                if bool(room_3) != False: shift(room_3, 1)
            
            if i % (len(room_1) * m) == 0 and volna == pereriv:
                rx += pereriv_c
                fx += pereriv_m
                if fx >= 60:
                    fx = fx % 60
                    rx += 1
                cx = rx
                mx = fx
                volna += 1
            elif i % (len(room_1) * m) == 0 and volna != pereriv:
                cx = rx
                mx = fx
                volna += 1

            rx = cx
            fx = mx
            i += 1
        return render_template('planning.html', specialization=specialization)

    else:
        specialization = data.Specialization.query.all()
        return render_template('planning.html', specialization=specialization)


@manage_app.route('/station', methods=['GET', 'POST'])
@login_required
def station():
    if request.method == "POST":
        name = request.form['name']
        ser_nomer = request.form['ser_nomer']
        specialization_id = request.form['specialization_id']
        personal_number = request.form['personal_number']
        photo = request.form['photo']

        student = data.Student(name=name, ser_nomer=ser_nomer, specialization_id=specialization_id, personal_number=personal_number, photo=photo)

        try:
            data.Student.session.add(student)
            data.Student.session.commit()
        except:
            return "Ошибка"
    else:
         return render_template('station.html')


@manage_app.route('/spec', methods=['GET', 'POST'])
@login_required
def spec():
    if request.method == "POST":
        name = request.form['name']
        ser_nomer = request.form['ser_nomer']
        specialization_id = request.form['specialization_id']
        personal_number = request.form['personal_number']
        photo = request.form['photo']

        student = data.Student(name=name, ser_nomer=ser_nomer, specialization_id=specialization_id, personal_number=personal_number, photo=photo)

        try:
            data.Student.session.add(student)
            data.Student.session.commit()
        except:
            return "Ошибка"
    else:
         return render_template('spec.html')
