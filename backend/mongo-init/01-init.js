// Create application database and a standard user
// This runs automatically on first container start

db = db.getSiblingDB('geonli');
db.createUser({
  user: 'geonli_app',
  pwd: 'geonli_app_pw',
  roles: [{ role: 'readWrite', db: 'geonli' }]
});

db.createCollection('sessions');
db.createCollection('messages');
db.createCollection('images');

db.sessions.createIndex({ userId: 1 });
db.sessions.createIndex({ sessionId: 1 }, { unique: true });
db.messages.createIndex({ sessionId: 1 });
db.images.createIndex({ sessionId: 1 }, { unique: true });
