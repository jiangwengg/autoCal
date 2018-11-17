class Settings():
	"""存储系统运行配置"""
	def __init__(self):
		#输入变量刷新速率(单位秒)
		self.input_interval = 2

		#前端变量刷新速率(单位毫秒)
		self.front_interval = 2000

		#是否开启debug模式(开启后控制台会输出大量运行信息)
		self.debug_mode = False

		#全局工况基础刷新速率(单位秒)
		self.global_base_interval = 0.05

		#记录文件写入速率
		self.wirte_interval = 1

#提供一个实例供各处调用
settings = Settings()
