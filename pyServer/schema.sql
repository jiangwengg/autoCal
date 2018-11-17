DROP TABLE IF EXISTS user_condition;

CREATE TABLE [user_condition](
  [id] INTEGER PRIMARY KEY AUTOINCREMENT, 
  [c_name] VARCHAR2(50) NOT NULL);

DROP TABLE IF EXISTS user_condition_entry;

CREATE TABLE [user_condition_entry](
  [id] INTEGER PRIMARY KEY AUTOINCREMENT, 
  [con_id] INTEGER NOT NULL, 
  [seq] INTEGER NOT NULL, 
  [duration] INTEGER NOT NULL DEFAULT 0, 
  [code] VARCHAR2(200));

DROP TABLE IF EXISTS user_global_entry;

CREATE TABLE [user_global_entry](
  [id] INTEGER PRIMARY KEY AUTOINCREMENT, 
  [c_name] VARCHAR2(50) NOT NULL, 
  [multiple] INTEGER NOT NULL, 
  [code] VARCHAR2(200), 
  [input_var] INTEGER, 
  [input_code] VARCHAR2(50), 
  [output_var] INTEGER, 
  [output_code] VARCHAR2(50), 
  [open] BOOLEAN NOT NULL);

DROP TABLE IF EXISTS user_static_var;

CREATE TABLE [user_static_var](
  [id] INTEGER PRIMARY KEY AUTOINCREMENT, 
  [c_name] VARCHAR2(50) NOT NULL, 
  [e_name] VARCHAR2(50) NOT NULL, 
  [code] VARCHAR2(100) NOT NULL UNIQUE, 
  [min_value] DOUBLE, 
  [max_value] DOUBLE, 
  [is_input] BOOLEAN NOT NULL);

DROP TABLE IF EXISTS user_var_condition;

CREATE TABLE [user_var_condition](
  [con_id] INTEGER NOT NULL, 
  [var_id] INTEGER NOT NULL);

DROP TABLE IF EXISTS user_var_entry;

CREATE TABLE [user_var_entry](
  [id] INTEGER PRIMARY KEY AUTOINCREMENT, 
  [con_id] INTEGER NOT NULL, 
  [entry_id] INTEGER NOT NULL, 
  [var_id] INTEGER NOT NULL, 
  [code] VARCHAR2(40) NOT NULL);