#!/bin/python3

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
    LoginManager,
    UserMixin,
)
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
import pymongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# 连接数据库
db = pymongo.MongoClient('mongodb://localhost:27017/')

def get_user(user_name):
    """根据用户名获得用户记录"""
    find_user =  db['app']['user'].find_one({'name': user_name})
    if find_user:
        find_user['id'] = str(find_user['_id'])
        del find_user['_id']
        find_user['password'] = generate_password_hash(find_user['password'])
        return find_user
    return None

def get_valid_users_names():
    usernames = []
    for item in db['app']['user'].find():
        usernames.append(item['name'])
    return usernames

class LoginForm(FlaskForm):
    """登录表单类"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])

class User(UserMixin):
    """用户类"""
    def __init__(self, user):
        self.username = user.get("name")
        self.password_hash = user.get("password")
        self.id = user.get("id")
        self.permission = user.get("permission")

    def verify_password(self, password):
        """密码验证"""
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """获取用户ID"""
        return self.id
    
    def get_name(self):
        return self.username
    
    def get_permission(self):
        return self.permission

    @staticmethod
    def get(user_id):
        """根据用户ID获取用户实体，为 login_user 方法提供支持"""
        if not user_id:
            return None
        
        find_user = db['app']['user'].find_one({'_id': ObjectId(user_id)})
        if find_user:
            find_user['id'] = str(find_user['_id'])
            del find_user['_id']
            find_user['password'] = generate_password_hash(find_user['password'])
            return User(find_user)
        return None

def isNumeric(str):
    if str.isnumeric():
        return True
    s = str.split('.')
    if len(s)>2:
        return False
    else:
        for si in s:
            if not si.isdigit():
                return False
    return True

app = Flask(__name__)  # 创建 Flask 应用

app.secret_key = 'pepperbest'  # 设置表单交互密钥

login_manager = LoginManager()  # 实例化登录管理对象
login_manager.init_app(app)  # 初始化应用
login_manager.login_view = 'login'  # 设置用户登录视图函数 endpoint

@login_manager.user_loader  # 定义获取登录用户的方法
def load_user(user_id):
    return User.get(user_id)

@app.route('/')  # 首页
@app.route('/index')  # 首页
@login_required  # 需要登录才能访问
def index():
    return render_template('index.html', username=current_user.username, permission=current_user.permission)

@app.route('/login', methods=('GET', 'POST'))  # 登录
def login():
    if request.method == "POST":
        data = request.form
        action = data.get('action')
        if action == 'login':
            user_name = data.get('username')
            password = data.get('password')
            user_info = get_user(user_name)  # 从用户数据中查找用户记录
            if user_info is None:
                flash("用户名或密码密码有误")
            else:
                user = User(user_info)  # 创建用户实体
                if user.verify_password(password):  # 校验密码
                    login_user(user)  # 创建用户 Session
                    print(1)
                    return redirect(url_for('index'))
                else:
                    flash("用户名或密码密码有误")
        elif action == 'register':
            return redirect(url_for('register'))
        elif action == 'forget':
            return redirect(url_for('forget'))
    return render_template('login.html')

@app.route('/logout')  # 登出
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        password2 = data.get('password2')
        email = data.get('email')
        email2 = data.get('email2')
        if ' ' in username:
            flash('用户名不能包括空格！')
        if len(username) < 2:
            flash('用户名长度不符合规范！')
        elif password != password2:
            flash('两次密码输入不同，请重试！')
        elif len(password) < 8:
            flash('密码不能少于8位！')
        elif (not email.endswith('@qq.com') or len(email) < 8 ):
            flash('邮箱输入有误，只能支持QQ邮箱！')
        elif email != email2:
            flash('两次邮箱输入不同，请重试！')
        elif db['app']['user'].count_documents({'name': username}) != 0:
            flash('该名字已存在！')
        else:
            result = db['app']['user'].insert_one({
                "name": username,
                "password": password,
                'email': email,
                "permission": 'member',
            })
            inserted_id = result.inserted_id
            if db['app']['user'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                flash('用户创建成功！')
            else:
                flash('用户创建失败，请重试！')
        
    return render_template('register.html')

@app.route('/add', methods=['GET'])  # 填写
@login_required
def add():
    print(current_user.permission)
    return render_template('add.html', permission=current_user.permission)

@app.route('/add_overtime', methods=['GET', 'POST'])
@login_required
def add_overtime():
    if request.method == "POST":
        data = request.form
        date1 = data.get('date1')
        date2 = data.get('date2')
        shift = data.get('shift') # 班次
        room = data.get('room') # 房间号
        
        date1 = datetime.strptime(date1, '%Y-%m-%dT%H:%M')
        date2 = datetime.strptime(date2, '%Y-%m-%dT%H:%M')
        if date1 >= date2 or (date2 - date1).days > 0 or (date2 - date1).seconds / 3600 > 12: # 如果时间超过12个小时
            flash("时间输入有误！")
        elif (datetime.now() - date2).days >= 3: # 禁止填写3天前的记录
            flash("禁止填写3天前的记录！")
        else:
            hours = (date2 - date1).seconds / 3600
            # 插入数据的代码
            dict_to_insert = {
                'start_time': date1,
                'end_time': date2,
                'hours': hours,
                'name': current_user.username,
                'shift': shift,
                'room': room,
                'verify': False,
            }
            result = db['app']['overtime'].insert_one(dict_to_insert)
            inserted_id = result.inserted_id
            if db['app']['overtime'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                flash("数据上传成功！")
            else:
                flash("数据上传失败，请重试！")
            
    return render_template('add_overtime.html', username=current_user.username)

@app.route('/add_compensation', methods=['GET', 'POST'])  # 填写补休
@login_required
def add_compensation():
    if request.method == "POST":
        data = request.form
        date1 = data.get('date1')
        date2 = data.get('date2')
        
        date1 = datetime.strptime(date1, '%Y-%m-%dT%H:%M')
        date2 = datetime.strptime(date2, '%Y-%m-%dT%H:%M')
        
        if date1 >= date2 or (date2 - date1).days > 0 or (date2 - date1).seconds / 3600 > 12: # 如果时间超过12个小时
            flash("时间输入有误！")
        elif (datetime.now() - date2).days >= 3: # 禁止填写3天前的记录
            flash("禁止填写3天前的记录！")
        else:
            hours = (date2 - date1).seconds / 3600
            # 插入数据的代码
            dict_to_insert = {
                'start_time': date1,
                'end_time': date2,
                'hours': hours,
                'name': current_user.username,
                'verify': False,
            }
            result = db['app']['compensation'].insert_one(dict_to_insert)
            inserted_id = result.inserted_id
            if db['app']['compensation'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                flash("数据上传成功！")
            else:
                flash("数据上传失败，请重试！")
    
    return render_template('add_compensation.html', username=current_user.username)

@app.route('/add_writeoff', methods=['GET', 'POST'])  # 填写补休
@login_required
def add_writeoff():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            name = data.get('name')
            writeoff_hours = data.get('writeoff_hours')
            writeoff_date = data.get('writeoff_date')
        
            writeoff_date = datetime.strptime(writeoff_date, '%Y-%m-%d')

            if not isNumeric(writeoff_hours):
                flash('输入有误，请重试！')
            else:
                dict_to_insert = {
                    'date': writeoff_date,
                    'name': name,
                    'hours': float(writeoff_hours),
                    'verify': False,
                }
                result = db['app']['writeoff'].insert_one(dict_to_insert)
                inserted_id = result.inserted_id
                if db['app']['writeoff'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                    flash("数据上传成功！")
                else:
                    flash("数据上传失败，请重试！")

    if current_user.permission != 'admin':
        return redirect(url_for('index'))

    valid_users = get_valid_users_names()
    return render_template('add_writeoff.html', permission=current_user.permission, users=valid_users)

@app.route('/view', methods=['GET', 'POST'])  # 查看
@login_required
def view():
    if request.method == "POST":
        data = request.form
        date1 = data.get('date1')
        date2 = data.get('date2')
        name = data.get('name')
        query_type = data.get('query_type')
        times = {}
        times['overtime'] = {'hours1': data.get('real_overtime_hours1'), 'hours2': data.get('real_overtime_hours2')}
        times['compensation'] = {'hours1': data.get('compensation_hours1'), 'hours2': data.get('compensation_hours2')}
        times['writeoff'] = {'hours1': data.get('writeoff_hours1'), 'hours2': data.get('writeoff_hours2')}
        sort_order = data.get('sort_order')
        
        date1 = datetime.strptime(date1, '%Y-%m-%d')
        date2 = datetime.strptime(date2, '%Y-%m-%d') + timedelta(days=1)
        
        pipline = [{
            '$match': {
                'verify': True
            }
        }]
        
        if query_type == 'overtime' or query_type == 'compensation':
            pipline.append({
                '$match': {
                    'start_time': {
                        '$gte': date1,
                        '$lt': date2
                    }
                }
            })
        else:
            pipline.append({
                '$match': {
                    'date': {
                        '$gte': date1,
                        '$lt': date2
                    }
                }
            })
        
        if name !='未选择':
            pipline.append({
                '$match': {
                    'name': name
                }
            })

        pipline.append({
            '$match': {
                'hours' : {
                    '$gte': times[query_type]['hours1'] == '' and -999999 or int(times[query_type]['hours1']),
                    '$lte': times[query_type]['hours2'] == '' and 999999 or int(times[query_type]['hours2'])
                }
            }
        })
        
        pipline.append({
            '$sort': {
                'hours': int(sort_order)
            }
        })
        
        aggr = db['app'][query_type].aggregate(pipline)
        query_result = [item for item in aggr]
        return render_template('view_result.html', query_type=query_type, query_result=query_result)

    valid_users = get_valid_users_names()
    return render_template('view.html', username=current_user.username, users=valid_users)

@app.route('/report', methods=['GET', 'POST'])  # 统计
@login_required
def report():
    if request.method == "POST":
        data = request.form
        date1 = data.get('date1')
        date2 = data.get('date2')
        query_type = data.get('query_type')

        date1 = datetime.strptime(date1, '%Y-%m-%d')
        date2 = datetime.strptime(date2, '%Y-%m-%d') + timedelta(days=1)
                
        if query_type == '实际加班时间统计':
            aggr = db['app']['overtime'].aggregate([
                {
                    '$match': {
                        'start_time': {
                            '$gte': date1,
                            '$lt': date2
                        }
                    }
                }, {
                    '$group': {
                        '_id': '$name',
                        'hours_count': {'$sum': '$hours'},
                    }
                }, {
                    '$sort': {
                        'hours_count': -1
                    }
                }
            ])
            table_title = ['名字', '时长']
            table_content = [[item['_id'], round(item['hours_count'],1)] for item in aggr]
            return render_template('report_result.html', query_type=query_type, table_title=table_title, table_content=table_content)

        elif query_type == '调整后加班时间统计':
            aggr = db['app']['overtime'].aggregate([
                {
                    '$match': {
                        'start_time': {
                            '$gte': date1,
                            '$lt': date2
                        },
                        'verify': True
                    }
                }, {
                    '$group': {
                        '_id': '$name',
                        'hours_count': {'$sum': '$hours'},
                    }
                }
            ])
            overtime = [[item['_id'], item['hours_count']] for item in aggr]
            
            aggr = db['app']['compensation'].aggregate([
                {
                    '$match': {
                        'start_time': {
                            '$gte': date1,
                            '$lt': date2
                        },
                        'verify': True
                    }
                }, {
                    '$group': {
                        '_id': '$name',
                        'hours_count': {'$sum': '$hours'},
                    }
                }
            ])
            compensation = [[item['_id'], item['hours_count']] for item in aggr]
            
            aggr = db['app']['writeoff'].aggregate([
                {
                    '$match': {
                        'date': {
                            '$gte': date1,
                            '$lt': date2
                        },
                        'verify': True
                    }
                }, {
                    '$group': {
                        '_id': '$name',
                        'hours_count': {'$sum': '$hours'},
                    }
                }
            ])
            writeoff = [[item['_id'], item['hours_count']] for item in aggr]
                        
            table_title = ['名字', '时长']
            table_content = {}
            
            for item in overtime:
                name = item[0]
                hours = item[1]
                if item[0] in table_content:
                    table_content[name] += hours
                else:
                    table_content[name] = hours
            
            for item in compensation + writeoff:
                name = item[0]
                hours = item[1]
                if item[0] in table_content:
                    table_content[name] -= hours
                else:
                    table_content[name] = -hours
            
            table_content = [[key, round(value, 1)] for key, value in table_content.items()]
            table_content = sorted(table_content, key=lambda x: -x[1])
            
            return render_template('report_result.html', query_type=query_type, table_title=table_title, table_content=table_content)

        elif query_type == '17点以后加班次数统计':
            aggr = db['app']['overtime'].aggregate([
                {
                    '$match': {
                        'start_time': {
                            '$gte': date1,
                            '$lt': date2
                        },
                    'verify':True
                    }
                }
            ])
            table_content = {}
            for item in aggr:
                start_time = item['start_time']
                end_time = item['end_time']
                name = item['name']
                # 如果是开始和结束是同一天
                if start_time.month == end_time.month and start_time.day == end_time.day:
                    # 如果是17点以后下班
                    if end_time > datetime(end_time.year, end_time.month, end_time.day, 17, 0):
                        if name in table_content:
                            table_content[name] += 1
                        else:
                            table_content[name] = 1
                    # 如果是7点上班
                    elif start_time < datetime(start_time.year, start_time.month, start_time.day, 8, 0):
                        if name in table_content:
                            table_content[name] += 1
                        else:
                            table_content[name] = 1
                # 如果是开始和结束不是同一天 那就肯定是17点以后的了
                else:
                    if name in table_content:
                        table_content[name] += 1
                    else:
                        table_content[name] = 1
            table_content = [[key, value] for key, value in table_content.items()]
            table_content = sorted(table_content, key=lambda x: -x[1])
            table_title = ['名字', '次数']
            
            return render_template('report_result.html', query_type=query_type, table_title=table_title, table_content=table_content)
        
        elif query_type == '22点以后加班次数统计':
            aggr = db['app']['overtime'].aggregate([
                {
                    '$match': {
                        'start_time': {
                            '$gte': date1,
                            '$lt': date2
                        },
                    'verify':True
                    }
                }
            ])
            table_content = {}
            for item in aggr:
                start_time = item['start_time']
                end_time = item['end_time']
                name = item['name']
                # 如果是开始和结束是同一天
                if start_time.month == end_time.month and start_time.day == end_time.day:
                    # 如果是22点以后下班
                    if end_time > datetime(end_time.year, end_time.month, end_time.day, 22, 0):
                        if name in table_content:
                            table_content[name] += 1
                        else:
                            table_content[name] = 1
                    # 如果是7点上班
                    elif start_time < datetime(start_time.year, start_time.month, start_time.day, 8, 0):
                        if name in table_content:
                            table_content[name] += 1
                        else:
                            table_content[name] = 1
                # 如果是开始和结束不是同一天 那就肯定是22点以后的了
                else:
                    if name in table_content:
                        table_content[name] += 1
                    else:
                        table_content[name] = 1
            table_content = [[key, value] for key, value in table_content.items()]
            table_content = sorted(table_content, key=lambda x: -x[1])
            table_title = ['名字', '次数']
            
            return render_template('report_result.html', query_type=query_type, table_title=table_title, table_content=table_content)


        elif query_type == '核销时间统计':
            aggr = db['app']['writeoff'].aggregate([
                {
                    '$match': {
                        'date': {
                            '$gte': date1,
                            '$lt': date2
                        },
                        'verify': True
                    }
                }, {
                    '$group': {
                        '_id': '$name',
                        'hours_count': {'$sum': '$hours'},
                    }
                }, {
                    '$sort': {
                        'hours_count': -1
                    }
                }
            ])
            table_title = ['名字', '时长']
            table_content = [[item['_id'], item['hours_count']] for item in aggr]
            return render_template('report_result.html', query_type=query_type, table_title=table_title, table_content=table_content)

    return render_template('report.html')

@app.route('/batch_overtime', methods=['GET', 'POST'])  # 批量加班
@login_required
def batch_overtime():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            date1 = data.get('date1')
            date2 = data.get('date2')
            
            chosen_players = []
            for key, value in data.items():
                if key != 'date1' and key != 'date2':
                    chosen_players.append(value)
        
            date1 = datetime.strptime(date1, '%Y-%m-%dT%H:%M')
            date2 = datetime.strptime(date2, '%Y-%m-%dT%H:%M')
            
            if date1 >= date2 or (date2 - date1).days > 0 or (date2 - date1).seconds / 3600 > 12: # 如果时间超过12个小时
                flash("时间输入有误！")
            else:
                hours = (date2 - date1).seconds / 3600
                number_needs_to_insert = len(chosen_players)
                number_inserted = 0
                for player in chosen_players:
                    # 插入数据的代码
                    dict_to_insert = {
                        'start_time': date1,
                        'end_time': date2,
                        'hours': hours,
                        'name': player,
                        'verify': False,
                    }
                    result = db['app']['overtime'].insert_one(dict_to_insert)
                    inserted_id = result.inserted_id
                    if db['app']['overtime'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                        number_inserted += 1
                flash(f'一共{number_needs_to_insert}条数据，成功上传{number_inserted}条，请去审核界面查看！')

    if current_user.permission != 'admin':
        return redirect(url_for('index'))

    valid_users = get_valid_users_names()
    return render_template('batch_overtime.html', username=current_user.username, permission=current_user.permission, users=valid_users)

@app.route('/batch_compensation', methods=['GET', 'POST'])  # 批量补休
@login_required
def batch_compensation():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            date1 = data.get('date1')
            date2 = data.get('date2')
            
            chosen_players = []
            for key, value in data.items():
                if key != 'date1' and key != 'date2':
                    chosen_players.append(value)
        
            date1 = datetime.strptime(date1, '%Y-%m-%dT%H:%M')
            date2 = datetime.strptime(date2, '%Y-%m-%dT%H:%M')
            
            if date1 >= date2 or (date2 - date1).days > 0 or (date2 - date1).seconds / 3600 > 12: # 如果时间超过12个小时
                flash("时间输入有误！")
            else:
                hours = (date2 - date1).seconds / 3600
                number_needs_to_insert = len(chosen_players)
                number_inserted = 0
                for player in chosen_players:
                    # 插入数据的代码
                    dict_to_insert = {
                        'start_time': date1,
                        'end_time': date2,
                        'hours': hours,
                        'name': player,
                        'verify': False,
                    }
                    result = db['app']['compensation'].insert_one(dict_to_insert)
                    inserted_id = result.inserted_id
                    if db['app']['compensation'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                        number_inserted += 1
                flash(f'一共{number_needs_to_insert}条数据，成功上传{number_inserted}条，请去审核界面查看！')

    if current_user.permission != 'admin':
        return redirect(url_for('index'))

    valid_users = get_valid_users_names()
    return render_template('batch_compensation.html', username=current_user.username, permission=current_user.permission, users=valid_users)

@app.route('/batch_writeoff', methods=['GET', 'POST'])
@login_required
def batch_writeoff():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            writeoff_hours = data.get('writeoff_hours')
            writeoff_date = data.get('writeoff_date')
            
            chosen_players = []
            for key, value in data.items():
                if key != 'writeoff_hours' and key != 'writeoff_date':
                    chosen_players.append(value)
                    
            writeoff_date = datetime.strptime(writeoff_date, '%Y-%m-%d')
            
            if not isNumeric(writeoff_hours):
                flash('输入有误，请重试！')
            else:
                number_needs_to_insert = len(chosen_players)
                number_inserted = 0
                for player in chosen_players:
                    # 插入数据的代码
                    dict_to_insert = {
                        'date': writeoff_date,
                        'name': player,
                        'hours': float(writeoff_hours),
                        'verify': False,
                    }
                    result = db['app']['writeoff'].insert_one(dict_to_insert)
                    inserted_id = result.inserted_id
                    if db['app']['writeoff'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                        number_inserted += 1
                flash(f'一共{number_needs_to_insert}条数据，成功上传{number_inserted}条，请去审核界面查看！')

    if current_user.permission != 'admin':
        return redirect(url_for('index'))
       
    valid_users = get_valid_users_names()
    return render_template('batch_writeoff.html', username=current_user.username, permission=current_user.permission, users=valid_users)

@app.route('/batch')  # 批量填写
@login_required
def batch():
    if current_user.permission != 'admin':
        return redirect(url_for('index'))
    return render_template('batch.html', permission=current_user.permission)

@app.route('/verify', methods=['GET', 'POST'])  # 审核
@login_required
def verify():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            action = data.get('action')
            _id = data.get('_id')
            group = data.get('group')
            
            if action == 'confirm':
                db['app'][group].find_one_and_update({'_id': ObjectId(_id)}, {'$set': {'verify': True}})
            else:
                db['app'][group].find_one_and_delete({'_id': ObjectId(_id)})
        
    if current_user.permission != 'admin':
        return redirect(url_for('index'))
    
    overtime_aggr = db['app']['overtime'].aggregate([
        {
            '$match': {
                'verify': False
            }
        }
    ])
    compensation_aggr = db['app']['compensation'].aggregate([
        {
            '$match': {
                'verify': False
            }
        }
    ])
    writeoff_aggr = db['app']['writeoff'].aggregate([
        {
            '$match': {
                'verify': False
            }
        }
    ])
    
    overtime = [item for item in overtime_aggr]
    compensation = [item for item in compensation_aggr]
    writeoff = [item for item in writeoff_aggr]
    
    return render_template(
        'verify.html',
        permission=current_user.permission,
        overtime=overtime,
        compensation=compensation,
        writeoff=writeoff
    )

@app.route('/user_manage')
@login_required
def user_manage():
    if current_user.permission != 'admin':
        return redirect(url_for('index'))
    return render_template("user_manage.html", permission=current_user.permission)

@app.route('/user_add', methods=['GET', 'POST'])
@login_required
def user_add():
    if request.method == "POST":
        if current_user.permission == 'admin':
            data = request.form
            username = data.get('username').strip()
            password = data.get('password')
            password2 = data.get('password2')
            email = data.get('email').strip()
            if ' ' in username:
                flash('用户名不能包括空格！')
            if len(username) < 2:
                flash('用户名不符合规范！')
            elif password != password2:
                flash('两次密码输入不同，请重试！')
            elif len(password) < 8:
                flash('密码不能少于8位！')
            elif (not email.endswith('@qq.com') or len(email) < 8 ):
                flash('邮箱输入有误，只能支持QQ邮箱！')
            elif db['app']['user'].count_documents({'name': username}) != 0:
                flash('该名字已存在！')
            else:
                result = db['app']['user'].insert_one({
                    "name": username,
                    "password": password,
                    'email': email,
                    "permission": 'member',
                })
                inserted_id = result.inserted_id
                if db['app']['user'].count_documents({'_id': ObjectId(inserted_id)}) == 1:
                    flash('用户创建成功！')
                else:
                    flash('用户创建失败，请重试！')

    if current_user.permission != 'admin':
        return redirect(url_for('index'))

    return render_template("user_add.html", permission=current_user.permission)

@app.route('/user_remove', methods=['GET', 'POST'])
@login_required
def user_remove():
    if request.method == 'POST':
        if current_user.permission == 'admin':
            data = request.form
            _id = data.get('_id')
            db['app']['user'].find_one_and_delete({'_id': ObjectId(_id)})

    if current_user.permission != 'admin':
        return redirect(url_for('index'))

    table_content = []
    for item in db['app']['user'].find({'permission': 'member'}):
        table_content.append({
            '_id': str(item['_id']),
            'name': item['name'],
        })
    return render_template("user_remove.html", permission=current_user.permission, table_content=table_content)

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0', port=80)
