"""这个类在目前是用不上的，数据在运行时加载而不是在服务器启动时加载"""
import sqlite3
import json
import datetime
import os
import time
import threading

from flask import Blueprint, current_app, request
from threading import Timer

from .settings import settings
from .db import get_db
from pyServer import app, send_logger, refrash_step, step_end

#存储用户自定义输入变量
user_var_input = {}

#存储用户自定义输出变量
user_var_output = {}

#存储工况信息的字典
user_condition = {}

#存储全局工况的字典
global_entry = {}

#变量键值对列表，用作json返回或数据记录
input_list = []
output_list = []

#运行状态，标记工况入口，防止重复运行
running_status = False

#输入变量获取经常
timer_input = None

#全局工况进程
timer_global_entry = None
#全局工况计数器
counter_global_entry = 1

#线程相关，暂定标志与结束标志
pause_flag = None
stop_flag = {'flag': False}

from .model import *

"""输入变量刷新进程代码块"""
#定时任务，用以刷新输入参数
def get_all_input():
	global timer_input
	global user_var_input
	for key in user_var_input:
		user_var_input[key].set_value()
	timer_input = Timer(settings.input_interval, get_all_input)
	timer_input.start()

#创建定时任务对象
def makeTimer():
	global timer_input
	timer_input = Timer(settings.input_interval, get_all_input)
	timer_input.start()

"""全局工况加载相关代码块"""

def runGlobalEntry():
	global global_entry
	global timer_global_entry
	global counter_global_entry
	global user_var_input
	global user_var_output
	for key in global_entry:
		if (counter_global_entry % key == 0):
			for temp in global_entry[key]:
				#实际执行每一条全局工况
				if (temp.get('code')):
					exec(temp.get('code'))
				if (temp.get('input_var') and temp.get('input_code') and temp.get('output_var') and temp.get('output_code')):
					exec("if(user_var_input.get(temp.get('input_var')).value " + temp.get('input_code') + "):\
						\n	code_str = temp.get('output_code')\
						\n	if code_str.startswith('='):\
						\n		code_str = code_str[1:]\
						\n		user_var_output[temp.get('output_var')].value = float(code_str)\
						\n	else:\
						\n		user_var_output[temp.get('output_var')].value = user_var_output[temp.get('output_var')].value " + temp.get('output_code'))
					user_var_output[temp.get('output_var')].put_value()
	counter_global_entry = counter_global_entry + 1
	timer_global_entry = Timer(settings.global_base_interval, runGlobalEntry)
	timer_global_entry.start()

def makeTimerGlobalEntry():
	global timer_global_entry
	global counter_global_entry
	counter_global_entry = 1
	timer_global_entry = Timer(settings.global_base_interval, runGlobalEntry)
	timer_global_entry.start()

"""文件记录相关代码块"""
nowtime = None
timer_write = None
data_write = []
def logStart():
	global nowtime
	global timer_write
	#创建日志文件夹，写入baseInfo文件
	nowtime = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	#切换到history目录
	os.chdir(os.path.join(app.instance_path, 'history'))
	os.makedirs(nowtime)
	os.chdir('./' + nowtime)
	#创建baseInfo文件并写入相应数据
	var_names = {}
	for key in user_var_input:
		var_names[key] = user_var_input[key].c_name
	for key in user_var_output:
		var_names[key] = user_var_output[key].c_name
	base_data = {'var_names' : var_names, 'interval' : settings.wirte_interval}
	with open('baseInfo', 'w+', encoding='utf-8') as f:
		f.write(json.dumps(base_data))
	#开启定时任务，定期加载数据到结构中
	timer_write = Timer(settings.wirte_interval, logRun)
	timer_write.start()

def logRun():
	global timer_write
	global data_write
	input_write = []
	output_write = []
	for key in user_var_input:
		input_write.append({key : user_var_input[key].value})
	for key in user_var_output:
		output_write.append({key : user_var_output[key].value})
	data_write.append({'input_vars' : input_write, 'output_vars' : output_write})
	timer_write = Timer(settings.wirte_interval, logRun)
	timer_write.start()

def logFinish():
	global nowtime
	global timer_write
	global data_write
	timer_write.cancel()
	timer_write = None
	nowtime = None
	with open('data', 'w+', encoding='utf-8') as f:
		f.write(json.dumps(data_write))
	data_write.clear()

"""工况执行代码块"""

#工况运行结束，释放资源
def finish():
	global timer_input
	global timer_global_entry
	global running_status
	global pause_flag
	send_logger('全部工况执行完毕' + ' 时间 '  + time.strftime('%H:%M:%S',time.localtime(time.time())))
	step_end()
	pause_flag = None
	stop_flag = False
	running_status = False
	timer_input.cancel()
	timer_input = None
	timer_global_entry.cancel()
	timer_global_entry = None

bp = Blueprint('work', __name__, url_prefix='/work')

#加载全部运行环境
def init_env():
	global user_var_input
	global user_var_output
	global user_condition
	global global_entry
	global timer
	db = get_db()
	#加载输入变量
	if (settings.debug_mode):
		send_logger('输入变量清空')
	user_var_input.clear()
	if (settings.debug_mode):
		send_logger('输入变量加载中')
	input_rows = db.execute('SELECT * from user_static_var WHERE is_input = 1').fetchall()
	for temp in input_rows:
		user_var_input[temp.get('id')] = User_var_input(temp.get('id'), temp.get('c_name'), temp.get('e_name'), temp.get('code'))
	if (settings.debug_mode):
		send_logger('输入变量加载完成')

	#输入变量开始循环加载
	makeTimer()

	#加载输出变量
	if (settings.debug_mode):
		send_logger('输出变量清空')
	user_var_output.clear()
	if (settings.debug_mode):
		send_logger('输出变量加载中')
	output_rows = db.execute('SELECT * from user_static_var WHERE is_input = 0').fetchall()
	for temp in output_rows:
		user_var_output[temp.get('id')] = User_var_output(temp.get('id'), temp.get('c_name'), temp.get('e_name'), temp.get('code'), temp.get('min_value'), temp.get('max_value'))
	if (settings.debug_mode):
		send_logger('输出变量加载完成')

	#变量加载完毕，开始加载全局工况
	if (settings.debug_mode):
		send_logger('全局工况清空')
	global_entry.clear()
	if (settings.debug_mode):
		send_logger('全局工况加载中')
	global_entry_rows = db.execute('SELECT * from user_global_entry WHERE open = 1').fetchall()
	for temp in global_entry_rows:
		#如果该时间频率的列表还未创建，则创建相应的列表
		if (global_entry.get(temp.get('multiple')) == None):
			global_entry[temp.get('multiple')] = []
		#将全局工况加载入执行列表中
		global_entry[temp.get('multiple')].append(temp)
	if (settings.debug_mode):
		send_logger('全局工况加载完成')
	#加载完毕后输出测试
	# for key in global_entry:
	# 	for temp in global_entry[key]:
	# 		send_logger('全局工况名称:' + temp.get('c_name') + ' ，执行频率:' + str(key))

	#全局工况开始运行
	runGlobalEntry()
	if (settings.debug_mode):
		send_logger('全局开始运行')

	#加载工况及条目
	if (settings.debug_mode):
		send_logger('运行工况清空')
	user_condition.clear()
	if (settings.debug_mode):
		send_logger('运行工况加载中')
	#首先将工况加载为字典，id作为其主键
	output_rows = db.execute('SELECT * FROM user_condition').fetchall()
	for temp in output_rows:
		user_condition[temp.get('id')] = User_condition(temp.get('id'), temp.get('c_name'))
	#循环遍历工况，为每个工况加载条目，在条目中需要加载变量计算code
	for key in user_condition:
		#按序加载工况条目，填充进入工况对象
		output_rows = db.execute(
			'SELECT * from user_condition_entry WHERE con_id = ? ORDER BY seq ASC',
			(key,)
		).fetchall()
		for temp in output_rows:
			#创建一个条目并填充进入工况中的list
			temp_entry = User_condition_entry(temp.get('id'), temp.get('con_id'), temp.get('duration'), temp.get('code'), user_condition[key].c_name)
			#查询条目中的变量计算，并填充进入条目
			entry_cal = db.execute(
				'SELECT * from user_var_entry WHERE con_id = ? AND entry_id = ?',
				(key, temp.get('id'))
			).fetchall()
			temp_entry.var_entry_list = entry_cal
			#将entry条目保存至工况
			user_condition[key].entry_list.append(temp_entry)
		#遍历本条工况中的entry_list，为所有条目制定next属性
		for x in range(len(user_condition[key].entry_list)):
			if (x < len(user_condition[key].entry_list) - 1):
				user_condition[key].entry_list[x].next_entry = user_condition[key].entry_list[x + 1]
		if (settings.debug_mode):
			send_logger('工况 ' + user_condition[key].c_name + ' 加载完成')
	if (settings.debug_mode):
		send_logger('运行工况全部加载完成')

	#刷新前端的step
	refrash_step()

"""  工况执行相关代码块  """

#执行运行(采用线程方式)
@bp.route('/run/<con_id>')
def run(con_id):
	global running_status
	global pause_flag
	#这里是有app环境的
	if (not running_status):
		running_status = True
		pause_flag = threading.Event()#事件用作线程暂停的标记
		threading.Thread(target=do_run,args=(pause_flag, con_id)).start()
		return json.dumps({'msg' : 'ok'})
	return json.dumps({'msg' : 'err'})


def do_run(flag, con_id):
	global user_condition
	with app.app_context():
		flag.set()
		init_env()
		user_condition[int(con_id)].run(flag)
		finish()


#运行并记录
@bp.route('/runAndLog/<con_id>')
def runAndLog(con_id):
	global pause_flag
	global running_status
	if (not running_status):
		running_status = True
		pause_flag = threading.Event()#事件用作线程暂停的标记
		threading.Thread(target=do_runAndLog,args=(pause_flag, con_id)).start()
		return json.dumps({'msg' : 'ok'})
	return json.dumps({'msg' : 'err'})

def do_runAndLog(flag, con_id):
	global user_condition
	with app.app_context():
		flag.set()
		init_env()
		logStart()
		user_condition[int(con_id)].run(flag)
		logFinish()
		finish()

#运行用户指定的工况，指定的条目。并且用户选择记录与否
@bp.route('/runTheOne', methods=['POST'])
def runTheOne():
	global pause_flag
	global running_status
	if (not running_status):
		running_status = True
		pause_flag = threading.Event()#事件用作线程暂停的标记
		if request.form.get('mode') == 'run':
			threading.Thread(target=do_runTheOne,args=(pause_flag, request.form.get('conId'), request.form.get('entry'))).start()
		elif request.form.get('mode') == 'run&log':
			threading.Thread(target=do_runTheOne_log,args=(pause_flag, request.form.get('conId'), request.form.get('entry'))).start()
		return json.dumps({'msg' : 'ok'})
	return json.dumps({'msg' : 'err'})

def do_runTheOne(flag, con_id, entry_id):
	global user_condition
	with app.app_context():
		flag.set()
		init_env()
		for entry in user_condition[int(con_id)].entry_list:
			if entry.id == int(entry_id):
				entry.run(flag)
		finish()

def do_runTheOne_log(flag, con_id, entry_id):
	global user_condition
	with app.app_context():
		flag.set()
		init_env()
		logStart()
		for entry in user_condition[int(con_id)].entry_list:
			if entry.id == int(entry_id):
				entry.run(flag)
		logFinish()
		finish()

#前端获取变量展示刷新频率
@bp.route('/frontInterval')
def frontInterval():
	global settings
	return json.dumps(settings.front_interval)

#向前端返回所有变量状态
@bp.route('/showAll')
def showAll():
	global user_var_input
	global user_var_output
	global input_list
	global output_list
	input_list.clear()
	output_list.clear()
	for key in user_var_input:
		input_list.append({'name' : user_var_input[key].c_name,  'value' : user_var_input[key].value})
	for key in user_var_output:
		output_list.append({'name' : user_var_output[key].c_name,  'value' : user_var_output[key].value})
	result = {
		'input' : input_list,
		'output' : output_list
	}
	return json.dumps(result)

#获取执行记录历史
@bp.route('/getRecords')
def getRecords():
	os.chdir(os.path.join(app.instance_path, 'history'))
	result = os.listdir()
	return json.dumps(result)

@bp.route('/getRecord/<record_name>')
def getRecord(record_name):
	os.chdir(os.path.join(app.instance_path, 'history', record_name))
	with open('baseInfo', 'r', encoding='utf-8') as f:
		baseInfo = json.loads(f.read())
	with open('data', 'r', encoding='utf-8') as f:
		data = json.loads(f.read())
	result = {'baseInfo' : baseInfo, 'data' : data}
	return json.dumps(result)

#暂停/继续功能
@bp.route('/pause_resume')
def pause_resume():
	global pause_flag
	if pause_flag:
		if pause_flag.isSet():
			pause_flag.clear()
			return json.dumps({'status': 'pause'})
		else:
			pause_flag.set()
			return json.dumps({'status': 'resume'})
	

#停止执行功能
@bp.route('/stop')
def stop():
	global stop_flag
	stop_flag['flag'] = True
	return json.dumps({'msg' : 'ok'})