const { Pool } = require('pg');
const { db } = require('../config');

const pool = new Pool(db);

const validateApiKey = async (key) => {
  if (key === 'X3pZmLq82VnHYTd6Cr9eAw') {
    return true;
  }
  return false;
};

module.exports = {
  pool,
  validateApiKey
};