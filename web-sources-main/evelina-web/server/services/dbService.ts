import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// Create a reusable database connection function
export const getDbPool = () => {
  const { Pool } = pg;
  return new Pool({
    host: process.env.DB_HOST || 'database.exitscam.xyz',
    port: parseInt(process.env.DB_PORT || '6432'),
    database: process.env.DB_NAME || 'postgres',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
  });
};

// Save OAuth login attempt to database
export const saveLoginAttempt = async (userId: string, ipAddress: string) => {
  let pool: pg.Pool | null = null;
  
  try {
    pool = getDbPool();
    
    // Create the table if it doesn't exist yet
    await pool.query(`
      CREATE TABLE IF NOT EXISTS login_attempts (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        ip_address VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP NOT NULL DEFAULT NOW()
      )
    `);
    
    // Insert the login attempt
    await pool.query(
      'INSERT INTO login_attempts (user_id, ip_address) VALUES ($1, $2)',
      [userId, ipAddress]
    );
    
    console.log(`Logged login attempt for user ${userId} from IP ${ipAddress}`);
    return true;
  } catch (error) {
    console.error('Failed to save login attempt:', error);
    return false;
  } finally {
    // Make sure we close the pool even if there was an error
    if (pool) {
      try {
        await pool.end();
      } catch (err) {
        console.error('Error closing database connection:', err);
      }
    }
  }
};

// Retrieve login attempts with pagination
export const getLoginAttempts = async (page: number = 1, limit: number = 50, userId?: string) => {
  let pool: pg.Pool | null = null;
  
  try {
    pool = getDbPool();
    const offset = (page - 1) * limit;
    
    let query = 'SELECT * FROM login_attempts';
    const params: any[] = [];
    
    // Filter by userId if provided
    if (userId) {
      query += ' WHERE user_id = $1';
      params.push(userId);
      query += ' ORDER BY timestamp DESC LIMIT $2 OFFSET $3';
      params.push(limit, offset);
    } else {
      query += ' ORDER BY timestamp DESC LIMIT $1 OFFSET $2';
      params.push(limit, offset);
    }
    
    const result = await pool.query(query, params);
    
    // Get total count for pagination
    const countQuery = userId 
      ? 'SELECT COUNT(*) FROM login_attempts WHERE user_id = $1'
      : 'SELECT COUNT(*) FROM login_attempts';
    
    const countParams = userId ? [userId] : [];
    const countResult = await pool.query(countQuery, countParams);
    const totalCount = parseInt(countResult.rows[0].count);
    
    return {
      data: result.rows,
      pagination: {
        total: totalCount,
        page,
        limit,
        pages: Math.ceil(totalCount / limit)
      }
    };
  } catch (error) {
    console.error('Failed to retrieve login attempts:', error);
    throw error;
  } finally {
    // Make sure we close the pool even if there was an error
    if (pool) {
      try {
        await pool.end();
      } catch (err) {
        console.error('Error closing database connection:', err);
      }
    }
  }
}; 