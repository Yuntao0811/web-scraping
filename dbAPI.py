import logging
import pandas as pd
import numpy as np
import contextlib

from sqlalchemy import create_engine, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy.inspection import inspect

Base = declarative_base()


class dbIO():
	engine = create_engine('mysql+mysqlconnector://root:allan19950601@localhost:3306/condo')
	#engine = create_engine('sqlite:///C:/Users/luntaixia/Desktop/testInv.db')
	DBSession = sessionmaker(bind = engine)

	@ classmethod
	def register(cls):
		# use only once when initializing tables into db
		Base.metadata.create_all(cls.engine)

	@ classmethod
	@ contextlib.contextmanager
	def get_session(cls, errormsg : str = "reason Unknown") -> Session:
		"""return the session object to operate

		:param errormsg:
		:return: Session object

		example:
		>>> with dbIO.get_session() as s:
		>>>     #do something here
		"""
		session = cls.DBSession()
		try:
			yield session
			session.commit()
		except Exception as e:
			session.rollback()
			logging.error("Error Occured: %s\n%s" % (e.args, errormsg))
		finally:
			session.close()

	@ classmethod
	def insert(cls, table : Base, record : dict) -> None:
		"""insert a record into db

		:param table: table class
		:param record: dict of record to insert
		:return: None

		example:
		>>> x = {"fund_id" : "160023", "date" : "2005-09-02", "net_value" : 1.0102, "full_value" : 3.0102, "div" : 0.234, "pnl" : 0.2341}
		>>> dbIO.insert(MutualFundHist, x)
		"""
		with dbIO.get_session() as s:
			s.add(table(**record))

	@ classmethod
	def update(cls, table : Base, primary_kvs : dict, record : dict) -> None:
		"""update record by looking at primary key

		:param table: table class
		:param primary_kvs: dict of primary key-value pairs, use to find which record(s) to update
		:param record: dict of new record
		:return: None

		example:
		>>> p = {"fund_id" : "150234", "date" : "2005-09-09"}  # use to find which records to update_all
		>>> r = {"net_value" : 0.4456}  # the new record to save to db
		>>> dbIO.update(MutualFundHist, p, r)
		is equivalent to:
		UPDATE MutualFundHist
		SET net_value = 0.4456
		WHERE fund_id = '150234' AND date = '2005-09-09';
		"""
		with dbIO.get_session() as s:
			#s.query(table).filter(table.fund_id == "150234").update_all(r)
			conditions = [getattr(table, k) == v for k, v in primary_kvs.items()]
			s.query(table).filter(and_(*conditions)).update_all(record)

	@ classmethod
	def delete(cls, table : Base, primary_kvs : dict) -> None:
		"""delete record by looking at primary key

		:param table: table class
		:param primary_kvs: dict of primary key-value pairs, use to find which record(s) to update_all
		:return: None

		example:
		>>> p = {"fund_id" : "150234", "date" : "2005-09-09"}  # use to find which records to update_all
		>>> dbIO.delete(MutualFundHist, p)
		is equivalent to:
		DELETE FROM MutualFundHist
		WHERE fund_id = '150234' AND date = '2005-09-09';
		"""
		with dbIO.get_session() as s:
			conditions = [getattr(table, k) == v for k, v in primary_kvs.items()]
			s.query(table).filter(and_(*conditions)).delete()


	@ classmethod
	def modify_sql(cls, sql : str, *args, errormsg : str = "reason Unknown") -> None:
		"""execute original sql (not query)

		:param sql: sql string
		:param args: arguments to fill in sql template
		:param errormsg: error message to display when error occurred
		:return: None

		example:
		>>> sql = 'UPDATE MutualFundHist SET net_value = %s WHERE fund_id = %s AND date = %s;'
		>>> dbIO.modify_sql(sql, 0.7456, '150234', '2005-09-09')
		"""
		with cls.engine.connect() as conn:
			try:
				conn.execute(sql, *args)
			except Exception as e:
				logging.error("Error Occured: %s\n%s" % (e.args, errormsg))

	@ classmethod
	def query_df(cls, query : Query) -> pd.DataFrame:
		"""making query directly

		:param query: Query statement
		:return: resulting dataframe

		example:
		>>> with dbIO.get_session() as s:
		>>>     query = s.query(MutualFundHist).filter(MutualFundHist.fund_id == "160023")
		>>>
		>>> df = dbIO.query_df(query)
		"""
		return pd.read_sql(query.statement, query.session.bind).replace({None : np.nan})

	@ classmethod
	def query_sql_df(cls, sql : str, *args, errormsg : str = "reason Unknown") -> pd.DataFrame:
		"""using original sql to make queries

		:param sql: the sql template
		:param args: the argument list to fill in the sql template
		:param errormsg: message to display when encoutering errors
		:return: the result dataframe

		example:
		>>> sql = "select * from mutualfundhist where fund_id = %s"
		>>> r = dbIO.query_sql_df(sql, '160023')
		"""
		with cls.engine.connect() as conn:
			try:
				r = conn.execute(sql, *args)
			except Exception as e:
				logging.error("Error Occured: %s\n%s" % (e.args, errormsg))
				df = pd.DataFrame({})
			else:
				headrs = [ i[0] for i in r.cursor.description ]
				df = pd.DataFrame.from_records(r, columns = headrs, coerce_float = True)
			finally:
				return df

	@ classmethod
	def insert_df(cls, table : Base, df : pd.DataFrame) -> None:
		"""save a pandas table into database

		:param table: table class
		:param df: the pandas Dataframe to save into db
		:return: None

		example:
		>>> df = pd.DataFrame({
		>>>     "fund_id" : ["160023", "160023", "160023", "150234"],
		>>>     "date" : ["2005-09-09", "2005-09-02", "2005-08-31", "2005-09-09"],
		>>>     "net_value" : [1.0234, 1.0102, 1.0456, 0.9876],
		>>>     "full_value" : [3.0234, 3.0102, 3.0456, 2.9876],
		>>>     "div" : [None, 0.234, None, None],
		>>>     "split_ratio" : [1.0034, None, None, 1.2232],
		>>>     "pnl" : [0.2334, 0.2341, -0.1442, -0.0032],
		>>> })
		>>> dbIO.insert_df(MutualFundHist, df)
		"""
		records = df2Tables(df, table)

		with dbIO.get_session() as s:
			s.add_all(records)


def getPrimaryKeys(table : Base) -> list:
	return [key.name for key in inspect(table).primary_key]

def df2Tables(df : pd.DataFrame, table : Base) -> list:
	records = []
	for row in df.replace({np.nan: None}).to_dict(orient = "records"):
		records.append(table(**row))

	return records

# def tables2Df(tables : list) -> pd.DataFrame:
#     records = [t.to_dict() for t in tables]
#     return pd.DataFrame.from_records(records)


if __name__ == '__main__':

	dbIO.register()