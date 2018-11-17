#Flask对象工厂
import os

from flask import Flask

app = Flask(__name__, static_folder='webApp', static_url_path='', instance_relative_config=True)

app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'userConf.db'),
)

app.config.from_pyfile('config.py', silent=True)

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

#导入数据处理层
from . import db
db.init_app(app)

#导入管理蓝图
from . import user_conf
app.register_blueprint(user_conf.bp)

@app.route('/')
def index():
    return app.send_static_file('index2.html')


#webSocket使能部分
from flask_socketio import SocketIO, emit
socketio = SocketIO(app)

@socketio.on('disconnect', namespace='/ws')
def test_disconnect():
    print('Client disconnected')

#向前端主动发送logger信息
def send_logger(message):
	socketio.emit('logger', {'data': message}, namespace='/ws')

#通知步骤重置
def refrash_step():
	socketio.emit('refrashStep', {}, namespace='/ws')

#通知当前工况内容
def send_step(conId, entry, conName):
	socketio.emit('stepNotice', {'conId': conId, 'entry': entry, 'conName': conName}, namespace='/ws')

#通知当前工况内容
def step_end():
	socketio.emit('stepEnd', {}, namespace='/ws')

#数据运行蓝图
from . import work
app.register_blueprint(work.bp)

if __name__ == '__main__':
    socketio.run(app)