PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT UNIQUE,
  regDate INTEGER,
  lastLogin INTEGER,
  timesviewed INTEGER,
  UNIQUE(user_id, nickname));
CREATE TABLE IF NOT EXISTS users_profile(
  user_id INTEGER PRIMARY KEY,
  firstname TEXT,
  lastname TEXT,
  email TEXT,
  website TEXT,
  picture TEXT,
  mobile TEXT,
  skype TEXT,
  age INTEGER,
  residence TEXT,
  gender TEXT,
  signature TEXT,
  avatar TEXT,
  FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS friends (
  user_id INTEGER,
  friend_id INTEGER,
  PRIMARY KEY(user_id, friend_id),
  FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY(friend_id) REFERENCES users(user_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS messages(
  message_id INTEGER PRIMARY KEY,
  title TEXT,
  body TEXT,
  timestamp INTEGER,
  ip TEXT,
  timesviewed INTEGER,
  reply_to INTEGER,
  user_nickname TEXT,
  user_id INTEGER,
  editor_nickname TEXT,
  FOREIGN KEY(reply_to) REFERENCES messages(message_id) ON DELETE CASCADE,
  FOREIGN KEY(user_id,user_nickname) REFERENCES users(user_id, nickname) ON DELETE SET NULL);


COMMIT;
PRAGMA foreign_keys=ON;
