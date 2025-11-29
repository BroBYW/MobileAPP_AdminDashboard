from nicegui import ui, app
import requests
import datetime
import io
import csv
import re
import os
from dotenv import load_dotenv

load_dotenv(override=True)

FIREBASE_URL = 'https://mad-mental-default-rtdb.asia-southeast1.firebasedatabase.app'


def fetch_users():
    try:
        r = requests.get(f'{FIREBASE_URL}/users.json', timeout=15)
        if r.status_code == 200:
            data = r.json() or {}
            return data
        return {}
    except Exception:
        return {}


def transform_users(data):
    rows = []
    for uid, content in (data or {}).items():
        profile = (content or {}).get('profile') or {}
        journal = (content or {}).get('journal') or {}
        rows.append({
            'uid': uid,
            'username': profile.get('Username') or '',
            'email': profile.get('Email') or '',
            'photo': profile.get('PhotoUrl') or '',
            'journals': len(journal),
        })
    return rows


def transform_journals(data):
    rows = []
    for uid, content in (data or {}).items():
        profile = (content or {}).get('profile') or {}
        username = profile.get('Username') or ''
        email = profile.get('Email') or ''
        journal = (content or {}).get('journal') or {}
        for push_id, entry in journal.items():
            mood = entry.get('Mood')
            summary = entry.get('Summary') or ''
            date_raw = entry.get('Date') or ''
            dt = parse_date(date_raw)
            date = dt.isoformat() if dt else (date_raw[:10] if isinstance(date_raw, str) and len(date_raw) >= 10 else '')
            image = entry.get('ImagePath') or ''
            rows.append({
                'uid': uid,
                'push_id': push_id,
                'username': username,
                'email': email,
                'mood': mood,
                'summary': summary,
                'date': date,
                'image': image,
            })
    return rows


def parse_date(s):
    try:
        if not s:
            return None
        ss = str(s).strip().strip('`')
        if not ss:
            return None
        ss = ss.replace('Z', '+00:00')
        try:
            return datetime.datetime.fromisoformat(ss).date()
        except Exception:
            pass
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                return datetime.datetime.strptime(ss, fmt).date()
            except Exception:
                continue
        if len(ss) >= 10:
            try:
                return datetime.datetime.strptime(ss[:10], '%Y-%m-%d').date()
            except Exception:
                return None
        return None
    except Exception:
        return None


store = {'users': [], 'journals': []}
last_fetch_ok = True


def is_http(url):
    return isinstance(url, str) and re.match(r'^https?://', url or '') is not None


def download_csv(rows, columns, filename):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([c['label'] for c in columns])
    for r in rows:
        writer.writerow([r.get(c['field']) for c in columns])
    ui.download(buf.getvalue().encode('utf-8'), filename)


def reload_data():
    global last_fetch_ok
    data = fetch_users()
    last_fetch_ok = bool(data)
    store['users'] = transform_users(data)
    store['journals'] = transform_journals(data)


reload_data()


users_table = None
journals_table = None


def check_credentials(email, password):
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    return bool(admin_email and admin_password and email == admin_email and password == admin_password)


@ui.page('/login')
def login_page():
    if app.storage.user.get('authed'):
        ui.navigate.to('/')
        return
    with ui.column().classes('w-full items-center justify-center min-h-screen'):
        with ui.card().classes('w-full md:w-[26rem]'):
            ui.label('Admin Login').classes('text-lg font-semibold')
            email_in = ui.input('Email').props('outlined dense').classes('w-full')
            pass_in = ui.input('Password', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
            def do_login():
                email = (email_in.value or '').strip()
                pwd = pass_in.value or ''
                if check_credentials(email, pwd):
                    app.storage.user['authed'] = True
                    app.storage.user['email'] = email
                    ui.notify('Login successful', color='positive')
                    ui.navigate.to('/')
                else:
                    ui.notify('Invalid credentials', color='negative')
            ui.button('Login', on_click=do_login).props('unelevated color=primary').classes('w-full')


@ui.page('/')
def index():
    if not app.storage.user.get('authed'):
        ui.navigate.to('/login')
        return
    global users_table, journals_table
    with ui.header().classes('items-center justify-between'):
        ui.label('MentalTrack Admin').classes('text-lg md:text-2xl font-bold')
        def do_refresh():
            reload_data()
            if users_table:
                users_table.rows = store['users']
                users_table.update()
            if journals_table:
                journals_table.rows = store['journals']
                journals_table.update()
            update_overview()
            update_chart()
            if not last_fetch_ok:
                ui.notify('Failed to load data from Firebase', color='negative')
            else:
                ui.notify('Data refreshed', color='positive')
        ui.button('Refresh', on_click=do_refresh).props('unelevated color=primary')
        def do_logout():
            try:
                app.storage.user.clear()
            except Exception:
                pass
            ui.navigate.to('/login')
        ui.button('Logout', on_click=do_logout).props('flat color=negative')

    with ui.row().classes('w-full'):
        tabs = ui.tabs().classes('w-full')
        with tabs:
            ui.tab('Overview')
            ui.tab('Users')
            ui.tab('Journals')
            ui.tab('Analytics')
        with ui.tab_panels(tabs, value='Overview').classes('w-full'):
            with ui.tab_panel('Overview').classes('w-full'):
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    overview_users = ui.card().classes('w-full md:w-1/3')
                    with overview_users:
                        ui.label('Total Users').classes('text-sm text-gray-600')
                        total_users_label = ui.label('0').classes('text-3xl font-semibold')
                    overview_journals = ui.card().classes('w-full md:w-1/3')
                    with overview_journals:
                        ui.label('Total Journals').classes('text-sm text-gray-600')
                        total_journals_label = ui.label('0').classes('text-3xl font-semibold')
                    overview_mood = ui.card().classes('w-full md:w-1/3')
                    with overview_mood:
                        ui.label('Average Mood').classes('text-sm text-gray-600')
                        avg_mood_label = ui.label('0').classes('text-3xl font-semibold')

                def update_overview():
                    total_users_label.text = str(len(store['users']))
                    total_journals_label.text = str(len(store['journals']))
                    moods = [j['mood'] for j in store['journals'] if isinstance(j.get('mood'), (int, float))]
                    avg = round(sum(moods) / len(moods), 2) if moods else 0
                    avg_mood_label.text = str(avg)

                update_overview()

            with ui.tab_panel('Users').classes('w-full'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-end gap-2'):
                        user_search = ui.input(label='Search users').classes('w-full md:w-1/3')
                        def apply_user_search():
                            term = (user_search.value or '').lower()
                            filtered = [u for u in store['users'] if term in u['username'].lower() or term in u['email'].lower() or term in u['uid'].lower()]
                            users_table.rows = filtered
                            users_table.update()
                        user_search.on('change', apply_user_search)
                        def export_users():
                            download_csv(users_table.rows, users_columns, 'users.csv')
                        ui.button('Export CSV', on_click=export_users).props('unelevated')
                    users_columns = [
                        {'name': 'uid', 'label': 'UID', 'field': 'uid', 'sortable': True},
                        {'name': 'username', 'label': 'Username', 'field': 'username', 'sortable': True},
                        {'name': 'email', 'label': 'Email', 'field': 'email', 'sortable': True},
                        {'name': 'journals', 'label': 'Journals', 'field': 'journals', 'sortable': True},
                    ]
                    selected_user_row = {'value': None}
                    def on_users_select(e):
                        sel = e.selection or []
                        if sel:
                            s = sel[0]
                            if isinstance(s, dict):
                                selected_user_row['value'] = s
                            else:
                                try:
                                    selected_user_row['value'] = next((r for r in users_table.rows if r.get('uid') == s), None)
                                except Exception:
                                    selected_user_row['value'] = None
                        else:
                            selected_user_row['value'] = None
                    users_table = ui.table(columns=users_columns, rows=store['users'], row_key='uid', selection='single', on_select=on_users_select).classes('w-full')
                    with ui.dialog() as user_dialog, ui.card().classes('w-full md:w-[32rem]'):
                        user_title = ui.label('User Profile').classes('text-lg font-semibold')
                        user_avatar = ui.avatar('').props('size=64')
                        user_email = ui.label('')
                        user_uid = ui.label('')
                        ui.separator()
                        ui.label('Recent Journals').classes('text-sm text-gray-600')
                        user_journal_list = ui.column().classes('gap-2')
                        def open_user(selected):
                            user_title.text = selected.get('username') or 'User Profile'
                            user_email.text = selected.get('email') or ''
                            user_uid.text = selected.get('uid') or ''
                            photo = selected.get('photo') or ''
                            if is_http(photo):
                                user_avatar.props(f'src={photo}')
                            else:
                                user_avatar.props('icon=person')
                            user_journal_list.clear()
                            uid = selected.get('uid')
                            journals = [j for j in store['journals'] if j.get('uid') == uid]
                            for j in sorted(journals, key=lambda x: x.get('date') or '', reverse=True)[:8]:
                                with user_journal_list:
                                    ui.label(f"{j.get('date','')} • Mood {j.get('mood','')} • {j.get('summary','')[:60]}")
                            user_dialog.open()
                    def on_user_view():
                        selected = selected_user_row['value']
                        if not selected:
                            ui.notify('No user selected', color='warning')
                            return
                        open_user(selected)
                    ui.button('View Selected', on_click=on_user_view).props('unelevated')

            with ui.tab_panel('Journals').classes('w-full'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full items-center justify-between gap-2 flex-wrap'):
                        journal_search = ui.input(label='Search journals').props('outlined dense').classes('w-full md:w-1/2')
                        count_label = ui.label('').classes('text-xs text-gray-600')
                    with ui.row().classes('items-end gap-2 flex-wrap'):
                        start_date = ui.input(label='Start date', placeholder='YYYY-MM-DD').props('outlined dense').classes('w-full md:w-1/4')
                        end_date = ui.input(label='End date', placeholder='YYYY-MM-DD').props('outlined dense').classes('w-full md:w-1/4')
                        def apply_journal_filters():
                            term = (journal_search.value or '').lower()
                            sd = parse_date(start_date.value or '')
                            ed = parse_date(end_date.value or '')
                            def within_date(d):
                                dt = parse_date(d or '')
                                if not dt:
                                    return False if (sd or ed) else True
                                if sd and dt < sd:
                                    return False
                                if ed and dt > ed:
                                    return False
                                return True
                            filtered = [j for j in store['journals'] if within_date(j.get('date')) and (term in (j.get('summary') or '').lower() or term in (j.get('username') or '').lower() or term in (j.get('email') or '').lower())]
                            journals_table.rows = filtered
                            journals_table.update()
                            count_label.text = f"Showing {len(filtered)} of {len(store['journals'])}"
                        journal_search.on('change', apply_journal_filters)
                        start_date.on('change', apply_journal_filters)
                        end_date.on('change', apply_journal_filters)
                        def last_n_days(n):
                            today = datetime.date.today()
                            start = today - datetime.timedelta(days=n-1)
                            start_date.value = start.strftime('%Y-%m-%d')
                            end_date.value = today.strftime('%Y-%m-%d')
                            apply_journal_filters()
                        def this_month():
                            today = datetime.date.today()
                            start = today.replace(day=1)
                            if start.month == 12:
                                next_month = start.replace(year=start.year+1, month=1, day=1)
                            else:
                                next_month = start.replace(month=start.month+1, day=1)
                            last_day = next_month - datetime.timedelta(days=1)
                            start_date.value = start.strftime('%Y-%m-%d')
                            end_date.value = last_day.strftime('%Y-%m-%d')
                            apply_journal_filters()
                        def clear_dates():
                            start_date.value = None
                            end_date.value = None
                            apply_journal_filters()
                        ui.button('Last 7 days', on_click=lambda: last_n_days(7)).props('unelevated')
                        ui.button('Last 30 days', on_click=lambda: last_n_days(30)).props('unelevated')
                        ui.button('This month', on_click=this_month).props('unelevated')
                        ui.button('Clear', on_click=clear_dates).props('unelevated')

                    journals_columns = [
                        {'name': 'date', 'label': 'Date', 'field': 'date', 'sortable': True},
                        {'name': 'username', 'label': 'Username', 'field': 'username', 'sortable': True},
                        {'name': 'email', 'label': 'Email', 'field': 'email', 'sortable': True},
                        {'name': 'mood', 'label': 'Mood', 'field': 'mood', 'sortable': True},
                        {'name': 'summary', 'label': 'Summary', 'field': 'summary', 'sortable': False},
                        {'name': 'image', 'label': 'ImagePath', 'field': 'image', 'sortable': False},
                    ]
                    selected_journal_row = {'value': None}
                    def on_journals_select(e):
                        sel = e.selection or []
                        if sel:
                            s = sel[0]
                            if isinstance(s, dict):
                                selected_journal_row['value'] = s
                            else:
                                try:
                                    selected_journal_row['value'] = next((r for r in journals_table.rows if r.get('push_id') == s), None)
                                except Exception:
                                    selected_journal_row['value'] = None
                        else:
                            selected_journal_row['value'] = None
                    journals_table = ui.table(columns=journals_columns, rows=store['journals'], row_key='push_id', selection='single', on_select=on_journals_select).classes('w-full')
                    count_label = ui.label('').classes('text-xs text-gray-600')
                    def export_journals():
                        download_csv(journals_table.rows, journals_columns, 'journals.csv')
                    ui.button('Export CSV', on_click=export_journals).props('unelevated')
                    with ui.dialog() as journal_dialog, ui.card().classes('w-full md:w-[36rem]'):
                        jd_title = ui.label('Journal Entry').classes('text-lg font-semibold')
                        jd_date = ui.label('')
                        jd_user = ui.label('')
                        jd_mood = ui.label('')
                        jd_summary = ui.label('')
                        jd_image = ui.image('').classes('w-full').props('fit=contain')
                        def open_journal(row):
                            jd_title.text = row.get('push_id') or 'Journal Entry'
                            jd_date.text = row.get('date') or ''
                            jd_user.text = f"{row.get('username','')} ({row.get('email','')})"
                            jd_mood.text = f"Mood: {row.get('mood','')}"
                            jd_summary.text = row.get('summary') or ''
                            img = row.get('image') or ''
                            if is_http(img):
                                jd_image.props(f'src={img}')
                            else:
                                jd_image.props('src=')
                            journal_dialog.open()
                    def on_journal_view():
                        selected = selected_journal_row['value']
                        if not selected:
                            ui.notify('Select a journal row first', color='warning')
                            return
                        open_journal(selected)
                    ui.button('View Selected', on_click=on_journal_view).props('unelevated')

            with ui.tab_panel('Analytics').classes('w-full'):
                with ui.column().classes('w-full gap-4'):
                    chart = ui.echart({
                        'tooltip': {},
                        'grid': {'left': '3%', 'right': '3%', 'bottom': '3%', 'containLabel': True},
                        'xAxis': {'type': 'category', 'data': ['1', '2', '3', '4', '5']},
                        'yAxis': {'type': 'value'},
                        'series': [{'name': 'Mood Count', 'type': 'bar', 'data': [0, 0, 0, 0, 0], 'itemStyle': {'color': '#3b82f6'}}],
                    }).classes('w-full h-64')

                    def update_chart():
                        counts = [0, 0, 0, 0, 0]
                        for j in store['journals']:
                            m = j.get('mood')
                            if isinstance(m, int) and 1 <= m <= 5:
                                counts[m - 1] += 1
                        chart.options['series'][0]['data'] = counts
                        chart.update()

                    update_chart()

ui.run(storage_secret=os.getenv('STORAGE_SECRET', 'mentaltrack_secret_key'))
