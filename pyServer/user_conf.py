#用户进行系统配置接口
#系统配置的持久化保存
import json
import xlwt
import xlrd
import os
import datetime

from flask import (
	Blueprint, g, render_template, url_for, request, send_from_directory
)
from pyServer import app
from .db import get_db
from .utils import list_to_arr

bp = Blueprint('manager', __name__, url_prefix='/manager')

#查询所有数据库中保存的用户自定义变量的接口
@bp.route('/getVar_all/<is_input>')
def getVar_input(is_input):
	db = get_db()
	result = db.execute('SELECT * from user_static_var WHERE is_input = ' + is_input).fetchall()
	return json.dumps(result)

#获取一个特定的变量信息
@bp.route('/getVar/<id>')
def getVarById(id):
	db = get_db()
	result = db.execute('SELECT * from user_static_var WHERE id = ' + id).fetchone()
	return json.dumps(result)

#新增自定义变量，保证code唯一
@bp.route('/createVar', methods=['POST'])
def createVar():
	db = get_db()
	rows = db.execute('SELECT * from user_static_var WHERE code = \'' + request.form['code'] + '\'').fetchone()
	if (rows):
		return json.dumps({'msg' : 'dup'})
	else:
		db.execute(
			'INSERT INTO user_static_var (c_name, e_name, code, is_input, min_value, max_value) VALUES (?, ?, ?, ?, ?, ?)',
			(request.form['c_name'], request.form['e_name'], request.form['code'], request.form['is_input'], request.form['min_value'], request.form['max_value'])
		)
		db.commit()
		return json.dumps({'msg' : 'ok'})

#变量修改方法POST
@bp.route('/modifyVar', methods=['POST'])
def modifyVar():
	db = get_db()
	#仍然需要确保code的唯一性
	rows = db.execute('SELECT * from user_static_var WHERE code = \'' + request.form['code'] + '\'').fetchone()
	if (rows and str(rows.get('id')) != request.form['id']):
		return json.dumps({'msg' : 'dup'})
	else :
		db.execute(
			'UPDATE user_static_var SET c_name = ?, e_name = ?, code = ?, is_input = ?, min_value = ?, max_value = ? WHERE id = ?',
			(request.form['c_name'], request.form['e_name'], request.form['code'], request.form['is_input'], request.form['min_value'], request.form['max_value'], request.form['id'])
		)
		db.commit()
		return json.dumps({'msg' : 'ok'})

#删除变量
@bp.route('/deleteVar', methods=['GET'])
def deleteVar():
	db = get_db()
	var_id = request.args.to_dict().get('id', '')
	if (var_id):
		#查看工况是否使用了变量
		rows = db.execute(
			'SELECT * from user_var_condition WHERE var_id = ' + var_id
		).fetchall()
		if (rows):
			return json.dumps({'msg' : 'in_use'})
		#查看全局工况是否使用了改变量
		rows = db.execute(
			'SELECT * from user_global_entry WHERE input_var = ? OR output_var = ?',
			(var_id, var_id)
		).fetchall()
		if (rows):
			return json.dumps({'msg' : 'in_use'})
		#没有被使用则可以删除
		db.execute(
			'DELETE FROM user_static_var WHERE id = ' + var_id
		)
		db.commit()
		return json.dumps({'msg' : 'ok'})
	

#查询所有数据库中保存的工况
@bp.route('/getCondition')
def getCondition():
	db = get_db()
	result = db.execute('SELECT * from user_condition').fetchall()
	return json.dumps(result)

#获取特定工况
@bp.route('/getCondition/<id>')
def getConditionById(id):
	db = get_db()
	con_result = db.execute('SELECT * from user_condition WHERE id = ' + id).fetchone()
	var_result = db.execute('SELECT * from user_var_condition WHERE con_id = ' + id).fetchall()
	result = {
		'con' : con_result,
		'var' : var_result
	}
	return json.dumps(result)

#删除工况
@bp.route('/delCondition/<id>')
def delConditionById(id):
	db = get_db()
	db.execute('DELETE FROM user_condition WHERE id = ' + id)
	db.execute('DELETE FROM user_condition_entry WHERE con_id = ' + id)
	db.execute('DELETE FROM user_var_entry WHERE con_id = ' + id)
	db.execute('DELETE FROM user_var_condition WHERE con_id = ' + id)
	db.commit()
	return json.dumps({'msg' : 'ok'})

#新增工况
@bp.route('/createCondition', methods=['POST'])
def createCondition():
	db = get_db()
	db.execute(
		'INSERT INTO user_condition (c_name) VALUES (?)',
		(request.form['c_name'],)
	)
	db.commit()
	return json.dumps({'msg' : 'ok'})
		

#修改工况
@bp.route('/modifyCondition', methods=['POST'])
def modifyCondition():
	db = get_db()
	db.execute('DELETE FROM user_var_condition WHERE con_id = ' + request.form['id'])
	db.execute('DELETE FROM user_condition_entry WHERE con_id = ' + request.form['id'])
	db.execute('DELETE FROM user_var_entry WHERE con_id = ' + request.form['id'])
	db.commit()
	data = request.form
	for key in data:
		if (key != 'id' and key != 'c_name'):
			db.execute(
				'INSERT INTO user_var_condition VALUES(?, ?)',
				(request.form['id'], key)
			)
	db.execute(
		'UPDATE user_condition SET c_name = ? WHERE id = ?',
		(request.form['c_name'], request.form['id'])
	)
	db.commit()
	return json.dumps({'msg' : 'ok'})

#根据工况id，加载所有条目数据
@bp.route('/getEntries/<con_id>')
def getEntries(con_id):
	db = get_db()
	result = db.execute('SELECT * from user_condition_entry WHERE con_id = ' + con_id + ' ORDER BY seq ASC').fetchall()
	return json.dumps(result)

#根据工况id,加载变量运算表达式
@bp.route('/getVarEntries/<con_id>')
def getVarEntries(con_id):
	db = get_db()
	result = db.execute('SELECT * from user_var_entry WHERE con_id = ' + con_id).fetchall()
	return json.dumps(result)

#保存工况id下的条目信息
@bp.route('/saveEntries/<con_id>', methods=['POST'])
def saveEntries(con_id):
	db = get_db()
	#删除条目表记录
	db.execute(
		'DELETE FROM user_condition_entry WHERE con_id = ' + con_id
	)
	#删除条目变量表记录
	db.execute(
		'DELETE FROM user_var_entry WHERE con_id = ' + con_id
	)
	db.commit()
	#分析数据，插入记录
	#定义变量，记录当前插入entry的seq
	s = 0
	current_entry_id = 0
	for key in request.form:
		param_arr = list_to_arr(key)
		#为当前工况的第一条数据，插入工况条目表记录(对每个条目只执行一次)
		if (int(param_arr[0]) == s):
			db.execute(
				'INSERT INTO user_condition_entry (con_id, seq, duration, code) VALUES(' + con_id + ', -1, 0, \'\')'
			)
			db.commit()
			#获取当前entry的id
			current_entry_id = db.execute('SELECT * FROM user_condition_entry WHERE con_id = ' + con_id + ' AND seq = -1').fetchone().get('id')
			#手动更新一下条目的seq
			db.execute(
				'UPDATE user_condition_entry set seq = ? WHERE id = ?',
				(param_arr[0], current_entry_id)
			)
			db.commit()
			s = s + 1
		#循环执行工况中的数据(每个语句都要提交)
		if (param_arr[1].isdigit()):
			#数字则意味着是计算条目，则为计算表做插入语句
			db.execute(
				'INSERT INTO user_var_entry (con_id, entry_id, var_id, code) VALUES(' + con_id + ', ' + str(current_entry_id) + ',' + param_arr[1] + ', \'' + request.form[key] + '\')'
			)
		else:
			#非数字意味着是工况条目，为工况表做更新语句
			if (param_arr[1] == 'code'):
				#将原有字符串中的单引号替换为双单引号，为执行SQL操作进行准备
				insert_value = request.form[key].replace("'", "''");
				#左右添加单引号，想SQL提示记录为字符串
				insert_value = '\'' + insert_value + '\''
			else:
				insert_value = request.form[key]
			db.execute(
				'UPDATE user_condition_entry SET ' + param_arr[1] + ' = ' + insert_value + ' WHERE id = ' + str(current_entry_id)
			)
		db.commit()
	return json.dumps({'msg' : 'ok'})

#获得所有全局工况
@bp.route('/getGlobalEntry')
def getGlobalEntry():
	db = get_db()
	result = db.execute('SELECT * from user_global_entry').fetchall()
	return json.dumps(result)

#创建全局工况
@bp.route('/editGlobalEntry', methods=['POST'])
def editGlobalEntry():
	db = get_db()
	db.execute(
		'UPDATE user_global_entry SET c_name = ?, multiple = ?, code = ?, input_var = ?, input_code = ?, output_var = ?, output_code = ?, open = ? WHERE id = ?',
		(request.form['c_name'], request.form['multiple'], request.form['code'], request.form['input_var'], request.form['input_code'], request.form['output_var'], request.form['output_code'], request.form['open'], request.form['id'])
	)
	db.commit()
	return json.dumps({'msg' : 'ok'})

#编辑全局工况
@bp.route('/createGlobalEntry', methods=['POST'])
def createGlobalEntry():
	db = get_db()
	db.execute(
		'INSERT INTO user_global_entry (c_name, multiple, code, input_var, input_code, output_var, output_code, open) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
		(request.form['c_name'], request.form['multiple'], request.form['code'], request.form['input_var'], request.form['input_code'], request.form['output_var'], request.form['output_code'], request.form['open'])
	)
	db.commit()
	return json.dumps({'msg' : 'ok'})

#通过Id获取一个全局工况
@bp.route('/getGlobalEntryById/<id>')
def getGlobalEntryById(id):
	db = get_db()
	result = db.execute('SELECT * from user_global_entry WHERE id = ' + id).fetchone()
	return json.dumps(result)

#通过Id删除一个全局工况
@bp.route('/delGlobalEntry/<id>')
def delGlobalEntry(id):
	db = get_db()
	db.execute('DELETE FROM user_global_entry WHERE id = ' + id)
	db.commit()
	return json.dumps({'msg' : 'ok'})

#改变一个全局工况的启用/禁用状态
@bp.route('/filpGlobalEntry/<id>')
def filpGlobalEntry(id):
	db = get_db()
	global_entry = db.execute('SELECT * from user_global_entry WHERE id = ' + id).fetchone()
	if (global_entry.get('open')):
		db.execute('UPDATE user_global_entry SET open = 0 WHERE id = ' + id)
		db.commit()
		return json.dumps({'status' : 'close'})
	else:
		db.execute('UPDATE user_global_entry SET open = 1 WHERE id = ' + id)
		db.commit()
		return json.dumps({'status' : 'open'})


"""文件上传下载代码块，Excel操作相关"""

#将现有的变量信息拿出来，装成一个xls文件存储，返回文件路径
def var_to_xls():
	#组装xls文件
	book = xlwt.Workbook(encoding='utf-8', style_compression=0)
	sheet = book.add_sheet('s1', cell_overwrite_ok=True)
	#处理列头
	sheet.write(0, 0, '中文名')
	sheet.write(0, 1, '英文名')
	sheet.write(0, 2, '链接参数')
	sheet.write(0, 3, '最小值')
	sheet.write(0, 4, '最大值')
	sheet.write(0, 5, '是否为输入变量')
	#循环处理数据内容
	db = get_db()
	rows = db.execute('SELECT * from user_static_var').fetchall()
	row_number = 1
	for row in rows:
		sheet.write(row_number, 0, row.get('c_name'))
		sheet.write(row_number, 1, row.get('e_name'))
		sheet.write(row_number, 2, row.get('code'))
		sheet.write(row_number, 3, row.get('min_value'))
		sheet.write(row_number, 4, row.get('max_value'))
		sheet.write(row_number, 5, row.get('is_input'))
		row_number = row_number + 1
	nowtime = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	os.chdir(os.path.join(app.instance_path, 'temp'))
	book.save(os.getcwd() + '/' + nowtime + '.xls')
	return nowtime + '.xls'

#将当前环境中变量配置为excel并给客户下载
@bp.route('/var_to_file')
def var_to_file():
	#首先制作excel文件并获取路径
	filename = var_to_xls()
	#然后提供文件下载
	os.chdir(os.path.join(app.instance_path, 'temp'))
	directory = os.getcwd()
	return send_from_directory(directory, filename, as_attachment=True)

#接受文件上传，处理参数导入
@bp.route('/xls_upload', methods=['GET','POST'])
def xls_upload():
	#接受上传的文件并且保存到本地
	f = request.files["file"]
	os.chdir(os.path.join(app.instance_path, 'temp'))
	nowtime = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	filename = os.getcwd() + '/' + nowtime + f.filename
	f.save(filename)
	#打开xls文件并且执行录入，返回录入结果的列表，成功或者失败
	#返回文件作为JSON格式，前端使用table进行展示
	db = get_db()
	result = []
	book = xlrd.open_workbook(filename)
	s1 = book.sheets()[0]
	for row in range(1, s1.nrows):
		#对每一个数据行的处理操作，拼接结果列表反馈给前端
		temp = {'c_name': s1.cell_value(row, 0),
			'e_name': s1.cell_value(row, 1),
			'code': s1.cell_value(row, 2),
			'is_input': s1.cell_value(row, 5)}
		#先判断code是否存在
		code = s1.cell_value(row, 2)
		exist = db.execute(
			'SELECT * from user_static_var WHERE code = \'' + code + '\''
		).fetchall()
		#如果对象存在，则记录存在
		if exist:
			temp['result'] = 'dup'
		else:
			#执行insert操作
			db.execute(
				'INSERT INTO user_static_var (c_name, e_name, code, is_input, min_value, max_value) VALUES (?, ?, ?, ?, ?, ?)',
				(s1.cell_value(row, 0), s1.cell_value(row, 1), s1.cell_value(row, 2), s1.cell_value(row, 5), s1.cell_value(row, 3), s1.cell_value(row, 4))
			)
			db.commit()
			temp['result'] = 'ok'
		result.append(temp)
	return json.dumps(result)
