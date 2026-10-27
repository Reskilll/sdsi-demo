const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync(':memory:');
db.exec('CREATE TABLE t (a INTEGER)');
db.prepare('INSERT INTO t VALUES (?)').run(1);
console.log('NODE_SQLITE_OK', JSON.stringify(db.prepare('SELECT * FROM t').all()));
db.close();
