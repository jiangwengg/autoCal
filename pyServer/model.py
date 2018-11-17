from ctypes import *
import os
import time

from .work import user_var_output, user_condition, stop_flag
from .settings import settings

from pyServer import send_logger, send_step

#从系统获得DLL文件
# os.chdir("C:\\Users\\HYG\\Desktop\\UniEPA")
# libc = CDLL("UniSup.dll")

#定义自定义变量父类
#父类包含用户定义参数，以及初始化时的hash值
class User_var():
	def __init__(self, id, c_name, e_name, code):
		self.id = id
		self.c_name = c_name
		self.e_name = e_name
		self.code = code
		#生产方法
		#self.hash = libc.UniGetHash(self.code)
		#测试方法
		self.hash = self.id
		#生产方法
		#self.value = libc.UniGetValue(c_ulong(self.hash))
		#测试方法
		self.value = self.id

	def to_string(self):
		return 'id=' + str(self.id) + ' c_name=' + self.c_name + ' e_name=' + self.e_name + ' code=' + self.code

#定义输入参数类
class User_var_input(User_var):
	def __init__(self, id, c_name, e_name, code):
		super().__init__(id, c_name, e_name, code)

	#重置value方法，可被定时器调用
	def set_value(self):
		if (settings.debug_mode):
			send_logger('获取变量:' + self.c_name + ' 值' + str(self.value))
		#生产方法
		#self.value = libc.UniGetValue(c_ulong(self.hash))
		#测试方法
		self.value = self.id

#定义输出参数类
class User_var_output(User_var):
	def __init__(self, id, c_name, e_name, code, min_value, max_value):
		super().__init__(id, c_name, e_name, code)
		self.min_value = min_value
		self.max_value = max_value

	#将现有值写入DLL，可被触发调用
	def put_value(self):
		#首先将输出变量约束在阈值范围内
		if (self.max_value and self.value > self.max_value):
			self.value = self.max_value
		if (self.min_value and self.value < self.min_value):
			self.value = self.min_value
		#然后执行写入dll
		if (settings.debug_mode):
			send_logger('写入变量:' + self.c_name + ' 值:' + str(self.value))
		#生产方法
		#libc.UniSetValue(c_ulong(self.get_hash()),c_float(self.value))
		#测试方法




#定义自定义工况
class User_condition():
	def __init__(self, id, c_name):
		self.id = id
		self.c_name = c_name
		self.entry_list = []

	#工况执行
	def run(self, pause_flag):
		if (self.entry_list):
			send_logger('执行工况 ' + self.c_name + ' ' + time.strftime('%H:%M:%S',time.localtime(time.time())))
			self.entry_list[0].run(pause_flag)
		else:
			send_logger('工况 ' + self.c_name + ' 中没有内容，停止运行')

#定义工况条目
class User_condition_entry():
	def __init__(self, id, con_id, duration, code, con_name):
		self.id = id
		self.con_id = con_id
		self.duration = duration
		self.code = code
		self.con_name = con_name
		self.var_entry_list = []
		self.next_entry = None

	def run(self, pause_flag):
		if (stop_flag['flag']):
			send_logger('用户停止工况执行'  + ' 时间 '  + time.strftime('%H:%M:%S',time.localtime(time.time())))
			return
		#工况暂停功能，线程挂起
		pause_flag.wait()
		global user_var_output
		global user_condition
		global running_status
		#向前端发送执行通知
		send_step(self.con_id, self.id, self.con_name)
		send_logger('工况 ' + self.con_name + ' 条目id ' + str(self.id) + ' 时间 '  + time.strftime('%H:%M:%S',time.localtime(time.time())))
		#执行自定义脚本
		if (self.code):
			exec(self.code)
		#执行变量赋值语句
		if (self.var_entry_list):
			for temp in self.var_entry_list:
				#code存在则执行操作
				if (temp.get('code')):
					try:
						code_str = temp.get('code')
						#处理赋值语句
						if (code_str.startswith('=')):
							#去除等号
							code_str = code_str[1:]
							#处理正负数赋值
							user_var_output[temp.get('var_id')].value = float(code_str)
						#处理计算语句(直接以加号，减号开始的语句)
						else:
							exec("user_var_output[temp.get('var_id')].value = user_var_output[temp.get('var_id')].value" + temp.get('code'))
					except:
						send_logger('工况' + self.con_name + ' 条目 ' + str(self.id) + ' 中的变量输入有误，变量ID ' + str(temp.get('var_id')) + ' 变量语句 ' + temp.get('code'))
					else:
						user_var_output[temp.get('var_id')].put_value()
		#消耗执行时间
		time.sleep(self.duration)
		if (self.next_entry):
			self.next_entry.run(pause_flag)
		else:
			send_logger('工况 ' + self.con_name + ' 条目全部执行完毕' + ' 时间 '  + time.strftime('%H:%M:%S',time.localtime(time.time())))
				