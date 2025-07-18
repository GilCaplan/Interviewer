from pymongo import MongoClient

from .cide_executor import logger
from .config import Config


def get_db_connection():
	"""
    Get a MongoDB connection using the configured URI

    Returns:
        MongoClient: MongoDB client instance
    """

	try:
		client = MongoClient(Config.MONGO_URI)
		return client
	except Exception as e:
		logger.error(f"Failed to connect to MongoDB: {str(e)}")
		raise e


def get_db():
	"""
    Get the default database from the MongoDB client

    Returns:
        Database: The default database instance
    """
	client = get_db_connection()
	return client.get_default_database()


def get_templates_collection():
	"""
    Get the templates collection from the database

    Returns:
        Collection: The templates collection instance
    """
	db = get_db()
	return db['templates']


def get_sessions_collection():
	"""
    Get the templates collection from the database

    Returns:
        Collection: The templates collection instance
    """
	db = get_db()
	return db['sessions']