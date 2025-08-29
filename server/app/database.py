"""
High-performance MongoDB connection pool for enterprise-scale concurrency
Supports 1000+ concurrent users with optimized connection management
"""

from pymongo import MongoClient
from .config import Config
import threading


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # High-performance MongoDB connection pool for 1000+ concurrent users
        self.client = MongoClient(
            Config.get_mongo_uri(),
            maxPoolSize=Config.DATABASE_POOL_SIZE,  # Maximum connections in pool
            minPoolSize=10,  # Minimum connections to maintain
            maxIdleTimeMS=Config.POOL_RECYCLE * 1000,  # Connection idle timeout
            waitQueueTimeoutMS=Config.POOL_TIMEOUT * 1000,  # Wait timeout for connection
            socketTimeoutMS=Config.SOCKET_TIMEOUT * 1000,  # Socket timeout
            connectTimeoutMS=30000,  # Connection timeout (30s)
            serverSelectionTimeoutMS=30000,  # Server selection timeout
            heartbeatFrequencyMS=10000,  # Heartbeat frequency
            retryWrites=True,  # Enable retryable writes
            retryReads=True,   # Enable retryable reads
            maxConnecting=20,  # Maximum concurrent connection attempts
        )
        
        self.db = self.client.get_default_database()
        
        # Cache collections for performance
        self._collections = {}
        
        self._initialized = True
    
    def get_collection(self, name):
        """Get a collection with caching for performance"""
        if name not in self._collections:
            self._collections[name] = self.db[name]
        return self._collections[name]
    
    @property 
    def users(self):
        return self.get_collection('users')
    
    @property
    def sessions(self):
        return self.get_collection('sessions')
    
    @property
    def templates(self):
        return self.get_collection('templates')
    
    @property
    def questions(self):
        return self.get_collection('questions')
    
    @property
    def interviews(self):
        return self.get_collection('interviews')
    
    @property
    def coding_challenges(self):
        return self.get_collection('coding_challenges')
    
    @property
    def interview_sessions(self):
        return self.get_collection('interview_sessions')
    
    @property
    def evaluations(self):
        return self.get_collection('evaluations')
    
    def close(self):
        """Close all connections"""
        if hasattr(self, 'client'):
            self.client.close()


# Global database manager instance
db_manager = DatabaseManager()

# Convenient access to collections
users_collection = db_manager.users
sessions_collection = db_manager.sessions
templates_collection = db_manager.templates
questions_collection = db_manager.questions
interviews_collection = db_manager.interviews
coding_challenges_collection = db_manager.coding_challenges
interview_sessions_collection = db_manager.interview_sessions
evaluations_collection = db_manager.evaluations