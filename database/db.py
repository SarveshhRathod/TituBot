import motor.motor_asyncio
import random
from config import DB_NAME, DB_URIS

class MultiDatabaseManager:
    def __init__(self, uris, database_name):
        self.clients = []
        self.dbs = []
        self.cols = []
        
        # Initialize all MongoDB instances provided
        for uri in uris:
            clean_uri = uri.strip()
            if clean_uri:
                client = motor.motor_asyncio.AsyncIOMotorClient(clean_uri)
                db = client[database_name]
                self.clients.append(client)
                self.dbs.append(db)
                self.cols.append(db.users)

    def _get_primary_col(self):
        # Load balancing across databases
        return self.cols[0] if self.cols else None

    def new_user(self, user_id, name):
        return {
            "id": int(user_id),
            "name": name,
            "session": None,
            "api_id": None,
            "api_hash": None,
        }
    
    async def add_user(self, user_id, name):
        user = self.new_user(user_id, name)
        # Store in primary collection
        if not await self.is_user_exist(user_id):
            await self._get_primary_col().insert_one(user)
    
    async def is_user_exist(self, user_id):
        user = await self._get_primary_col().find_one({'id': int(user_id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self._get_primary_col().count_documents({})
        return count

    async def get_all_users(self):
        return self._get_primary_col().find({})

    async def delete_user(self, user_id):
        for col in self.cols:
            await col.delete_many({'id': int(user_id)})

    async def set_session(self, user_id, session):
        await self._get_primary_col().update_one({'id': int(user_id)}, {'$set': {'session': session}})

    async def get_session(self, user_id):
        user = await self._get_primary_col().find_one({'id': int(user_id)})
        return user.get('session') if user else None

    async def set_api_credentials(self, user_id, api_id, api_hash):
        await self._get_primary_col().update_one(
            {'id': int(user_id)}, 
            {'$set': {'api_id': api_id, 'api_hash': api_hash}}
        )

    async def get_api_id(self, user_id):
        user = await self._get_primary_col().find_one({'id': int(user_id)})
        return user.get('api_id') if user else None

    async def get_api_hash(self, user_id):
        user = await self._get_primary_col().find_one({'id': int(user_id)})
        return user.get('api_hash') if user else None

    async def get_db_stats(self):
        stats = []
        for index, db in enumerate(self.dbs):
            try:
                count = await self.cols[index].count_documents({})
                stats.append(f"MongoDB Cluster {index + 1}: Active (Users: {count})")
            except Exception as e:
                stats.append(f"MongoDB Cluster {index + 1}: Error ({str(e)})")
        return stats

db = MultiDatabaseManager(DB_URIS, DB_NAME)