const mysql = require('mysql2/promise');
const fs = require('fs/promises');
const path = require('path');

const pool = mysql.createPool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  multipleStatements: true, // Needed for running schema.sql
});

async function initDb() {
  const connection = await pool.getConnection();
  try {
    // 1. Run schema.sql
    const schemaPath = path.join(__dirname, 'sql', 'schema.sql');
    const schemaSql = await fs.readFile(schemaPath, 'utf-8');
    const statements = schemaSql.split(';').filter(s => s.trim());
    for (const statement of statements) {
      if (statement) {
        await connection.query(statement);
      }
    }

    // 2. Ensure 'username' column exists in 'vote' table
    const [usernameColumn] = await connection.execute(
      `SELECT 1
       FROM INFORMATION_SCHEMA.COLUMNS
       WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'vote' AND COLUMN_NAME = 'username'`,
      [process.env.DB_NAME]
    );
    if (usernameColumn.length === 0) {
      await connection.execute(
        `ALTER TABLE vote ADD COLUMN username VARCHAR(50) NOT NULL AFTER option_id;`
      );
    }

    // 3. Ensure unique index on (poll_id, username)
    const [uniqueIndex] = await connection.execute(
      `SELECT 1
       FROM INFORMATION_SCHEMA.STATISTICS
       WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'vote' AND INDEX_NAME = 'uniq_vote_username'`,
      [process.env.DB_NAME]
    );
    if (uniqueIndex.length === 0) {
      await connection.execute(
        `CREATE UNIQUE INDEX uniq_vote_username ON vote (poll_id, username);`
      );
    }

    // 4. Seed data if poll table is empty
    const [[{ count }]] = await connection.execute('SELECT COUNT(*) as count FROM poll');
    if (count === 0) {
      const [pollResult] = await connection.execute(
        'INSERT INTO poll (question) VALUES (?)',
        ['Which gum flavor is best?']
      );
      const pollId = pollResult.insertId;
      const options = ['Mint', 'Strawberry', 'Grape', 'Cinnamon'];
      for (const option of options) {
        await connection.execute(
          'INSERT INTO poll_option (poll_id, label) VALUES (?, ?)',
          [pollId, option]
        );
      }
    }
  } finally {
    connection.release();
  }
}

async function getPollWithCounts(username) {
  const connection = await pool.getConnection();
  try {
    const [[poll]] = await connection.execute('SELECT id, question FROM poll LIMIT 1');
    if (!poll) {
      return null;
    }

    const [options] = await connection.execute(
      `SELECT
         po.id,
         po.label,
         COUNT(v.id) AS count
       FROM poll_option po
       LEFT JOIN vote v ON v.option_id = po.id
       WHERE po.poll_id = ?
       GROUP BY po.id
       ORDER BY po.id`,
      [poll.id]
    );

    const result = {
      poll,
      options,
      me: {
        username: null,
        hasVoted: false,
        optionId: null,
      },
    };

    if (username) {
      const normalizedUsername = username.trim().toLowerCase();
      if (normalizedUsername) {
        result.me.username = normalizedUsername;
        const [[userVote]] = await connection.execute(
          'SELECT option_id FROM vote WHERE poll_id = ? AND username = ? LIMIT 1',
          [poll.id, normalizedUsername]
        );
        if (userVote) {
          result.me.hasVoted = true;
          result.me.optionId = userVote.option_id;
        }
      }
    }

    return result;
  } finally {
    connection.release();
  }
}

async function insertVote(optionId, username) {
  const normalizedUsername = (username || '').trim().toLowerCase();
  const usernameRegex = /^[a-z0-9_]{3,20}$/;
  if (!usernameRegex.test(normalizedUsername)) {
    const err = new Error('Invalid username format.');
    err.isValidation = true;
    throw err;
  }

  const connection = await pool.getConnection();
  try {
    const [[option]] = await connection.execute(
      `SELECT po.poll_id FROM poll_option po JOIN poll p ON p.id = po.poll_id WHERE po.id = ?`,
      [optionId]
    );

    if (!option) {
      const err = new Error('Invalid option ID.');
      err.isValidation = true;
      throw err;
    }

    await connection.execute(
      'INSERT INTO vote (poll_id, option_id, username) VALUES (?, ?, ?)',
      [option.poll_id, optionId, normalizedUsername]
    );

    return { ok: true };
  } catch (error) {
    if (error.code === 'ER_DUP_ENTRY') {
      const err = new Error('Already voted');
      err.isDuplicate = true;
      throw err;
    }
    throw error;
  } finally {
    connection.release();
  }
}

module.exports = { initDb, getPollWithCounts, insertVote };
