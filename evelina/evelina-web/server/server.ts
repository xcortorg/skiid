import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import cookieParser from 'cookie-parser';
import authRouter from './auth.js';
import pg from 'pg';
import { verifyToken } from './auth';
import { getLoginAttempts } from './services/dbService';

dotenv.config();

// ES Module dirname polyfill
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 5000;
const isProduction = process.env.NODE_ENV === 'production';
const clientUrl = process.env.CLIENT_URL || (isProduction ? 'https://evelina.bot' : 'http://localhost:3000');
const API_BASE_URL = process.env.EXTERNAL_API_URL || 'https://v1.evelina.bot';
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || 'development-key-only';

// CORS options mit stricter Konfiguration
const corsOptions = {
  origin: (origin: string | undefined, callback: (err: Error | null, allow?: boolean) => void) => {
    // Erlaube Anfragen ohne Origin (z.B. lokale Tests, Postman)
    if (!origin) {
      return callback(null, true);
    }
    
    // Origin gegen erlaubte URLs prüfen
    const allowedOrigins = [clientUrl];
    if (isProduction === false) {
      // Im Entwicklungsmodus auch localhost erlauben
      allowedOrigins.push('http://localhost:5173', 'http://127.0.0.1:5173');
    }
    
    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error(`CORS-Fehler: Die Origin "${origin}" ist nicht erlaubt`));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'X-API-Key']
};

// Middleware
app.use(express.json());
app.use(cors(corsOptions));
app.use(cookieParser()); // Cookie-Parser für JWT-Token

// Logging Middleware für Debugging
app.use((req, res, next) => {
  // Nur GET Requests oder Requests, die nicht nur "/" sind loggen
  if (req.method !== 'POST' || req.url !== '/') {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
  }
  next();
});

// Browser-Zugriff-Blocker für API-Endpunkte
// Diese Middleware blockiert direkte Browser-Navigation zu API-URLs
app.use((req, res, next) => {
  const path = req.path;
  
  // Prüfe, ob es sich um einen API-Pfad handelt
  if (path.startsWith('/api/')) {
    const accept = req.get('Accept') || '';
    const userAgent = req.get('User-Agent') || '';
    const referer = req.get('Referer');
    const xRequestedWith = req.get('X-Requested-With');
    const apiKey = req.get('X-API-Key');
    
    // Erlaube den Zugriff mit gültigem API-Schlüssel
    if (apiKey && apiKey === INTERNAL_API_KEY) {
      return next();
    }
    
    // Eine direkte Browser-Anfrage könnte sein:
    // 1. Wenn jemand die URL direkt in die Browser-Adressleiste eingibt (kein Referer)
    // 2. Wenn der Accept-Header HTML enthält (Browser möchte HTML anzeigen)
    // 3. Wenn der User-Agent auf einen Browser hinweist
    // 4. Wenn keine speziellen API-Headers wie X-Requested-With gesetzt sind
    const isDirect = (
      ((!referer || !referer.includes('localhost:5173')) && accept.includes('text/html')) || 
      (userAgent.includes('Mozilla') && 
       req.method === 'GET' &&
       !xRequestedWith && 
       !apiKey &&
       (accept.includes('text/html') || accept === '*/*'))
    );
    
    if (isDirect) {
      console.log('Blockiere direkten Browser-Zugriff auf API:', path);
      console.log('Accept:', accept);
      console.log('User-Agent:', userAgent);
      console.log('Referer:', referer);
      
      return res.status(403).send(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>Zugriff verweigert</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 50px; text-align: center; color: #333; }
              h1 { color: #d9534f; }
              p { max-width: 600px; margin: 20px auto; }
              a { color: #007bff; text-decoration: none; }
              a:hover { text-decoration: underline; }
            </style>
          </head>
          <body>
            <h1>Zugriff verweigert</h1>
            <p>Diese API ist nur für die Verwendung durch autorisierte Anwendungen bestimmt und kann nicht direkt über den Browser aufgerufen werden.</p>
            <p><a href="/">Zurück zur Startseite</a></p>
          </body>
        </html>
      `);
    }
    
    // Für nicht-Browser-Anfragen: Überprüfe Origin/Referer im Produktionsmodus
    if (isProduction) {
      const origin = req.get('Origin');
      
      // Wenn kein Referer oder Origin vorhanden, verweigern
      if (!referer && !origin) {
        return res.status(403).json({
          error: 'Zugriff verweigert: Fehlende Herkunftsinformationen'
        });
      }
      
      try {
        const url = referer ? new URL(referer) : new URL(origin as string);
        const allowedHosts = [new URL(clientUrl).hostname];
        
        if (!allowedHosts.includes(url.hostname)) {
          return res.status(403).json({
            error: 'Zugriff verweigert: Unerlaubte Herkunft'
          });
        }
      } catch (err) {
        return res.status(403).json({
          error: 'Zugriff verweigert: Ungültige Herkunftsinformationen'
        });
      }
    }
  }
  
  next();
});

// Middleware, um direkte Zugriffe über den Browser auf API-URLs zu verhindern
// Diese muss VOR den API-Routen platziert werden
app.use('/api/*', (req, res, next) => {
  // Nur bei der ersten Implementierung wurden bereits alle Prüfungen gemacht
  next();
});

// Proxy route for commands API
app.get('/api/commands', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/commands`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch commands from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy commands request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for shards API
app.get('/api/shards', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/shards`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch shards from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy shards request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for  API
app.get('/api/team', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/team`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch team data from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy team request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for reviews API
app.get('/api/reviews', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/reviews`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch reviews from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy reviews request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for history API
app.get('/api/history', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch history data from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy history request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for avatars API (all)
app.get('/api/avatars', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/avatars`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch avatars from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy avatars request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for avatar of specific user
app.get('/api/avatars/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    
    const response = await fetch(`${API_BASE_URL}/avatars/${userId}`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch user avatars from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy avatars request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for templates API
app.get('/api/templates', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/templates`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch templates from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy templates request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for feedback API
app.get('/api/feedback', async (req, res) => {
  try {
    const response = await fetch(`${API_BASE_URL}/feedback`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch feedback from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy feedback request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Proxy route for user API
app.get('/api/user/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;

    const response = await fetch(`${API_BASE_URL}/user/${userId}`);
    
    if (!response.ok) {
      return res.status(response.status).json({
        error: 'Failed to fetch user data from API server'
      });
    }
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to proxy user request:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
  }
});

// Economy logs API endpoint
app.get('/api/logs/economy/:userId', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    const userId = req.params.userId;
    
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT user_id, action, type, amount, cash, card, created FROM economy_logs WHERE user_id = $1 ORDER BY created DESC',
      [userId]
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch economy logs:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Get all user blacklists
app.get('/api/blacklist/user/users', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT user_id, moderator_id, duration, reason, timestamp FROM blacklist_user ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all user blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Get all user command blacklists
app.get('/api/blacklist/user/commands', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT user_id, moderator_id, command, duration, reason, timestamp FROM blacklist_command ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all command blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Get all user cog blacklists
app.get('/api/blacklist/user/cogs', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT user_id, moderator_id, cog, duration, reason, timestamp FROM blacklist_cog ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all cog blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Server Blacklist API endpoints

// Get all server blacklists
app.get('/api/blacklist/server/servers', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT guild_id, moderator_id, duration, reason, timestamp FROM blacklist_server ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all server blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Get all server command blacklists
app.get('/api/blacklist/server/commands', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT guild_id, moderator_id, command, duration, reason, timestamp FROM blacklist_command_server ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all server command blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Get all server cog blacklists
app.get('/api/blacklist/server/cogs', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    // Database connection using environment variables
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Query the database
    const result = await pool.query(
      'SELECT guild_id, moderator_id, cog, duration, reason, timestamp FROM blacklist_cog_server ORDER BY timestamp DESC'
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch all server cog blacklists:', error);
    let errorMessage = 'Internal server error';
    
    // Provide more specific error messages for different types of errors
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }
    
    res.status(500).json({
      error: errorMessage
    });
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
});

// Activity messages API endpoint (per user per day)
app.get('/api/activity/messages', async (req, res) => {
  let pool: pg.Pool | null = null;
  try {
    const serverId = req.query.server_id as string;
    const timeRange = req.query.time_range as string || 'all';

    if (!serverId) {
      return res.status(400).json({
        error: 'Server ID is required'
      });
    }

    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    let sql = `
      SELECT 
        user_id,
        message_date, 
        SUM(message_count) AS total_messages
      FROM 
        activity_messages 
      WHERE 
        server_id = $1
    `;

    const params: any[] = [serverId];

    if (timeRange !== 'all') {
      const days = parseInt(timeRange.replace('d', ''));
      if (!isNaN(days)) {
        sql += ' AND message_date >= $2';
        const date = new Date();
        date.setDate(date.getDate() - days);
        params.push(date.toISOString().split('T')[0]);
      }
    }

    sql += ' GROUP BY user_id, message_date ORDER BY message_date ASC, user_id ASC';

    const result = await pool.query(sql, params);

    res.json(result.rows);
  } catch (error) {
    console.error('Failed to fetch activity messages:', error);
    let errorMessage = 'Internal server error';

    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        errorMessage = 'Failed to connect to database';
      } else if (error.message.includes('relation')) {
        errorMessage = 'Table not found in database';
      }
    }

    res.status(500).json({
      error: errorMessage
    });
  } finally {
    if (pool) {
      try {
        await pool.end();
      } catch (err) {
        console.error('Error closing database connection:', err);
      }
    }
  }
});

// Login attempts API endpoint (protected for team members)
app.get('/api/logs/logins', verifyToken, async (req, res) => {
  let pool: pg.Pool | null = null;
  
  try {
    // @ts-ignore - req.user is added by verifyToken middleware
    const userId = req.user?.id;

    // Database connection
    const { Pool } = pg;
    pool = new Pool({
      host: process.env.DB_HOST || 'database.exitscam.xyz',
      port: parseInt(process.env.DB_PORT || '6432'),
      database: process.env.DB_NAME || 'postgres',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'K3nWdPq82YtLXR6MGz0vHbCa'
    });

    // Check if user is a team member (you can refine this based on your actual team check logic)
    const teamMembers = await pool.query('SELECT user_id FROM team_members');
    const isTeamMember = teamMembers.rows.some(member => member.user_id === userId);
    
    if (!isTeamMember) {
      return res.status(403).json({ error: 'Forbidden: Only team members can access login logs' });
    }

    // Get query parameters
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 50;
    const filterUserId = req.query.userId as string || undefined;

    // Get login attempts
    const logins = await getLoginAttempts(page, limit, filterUserId);
    
    res.json(logins);
  } catch (error) {
    console.error('Failed to fetch login attempts:', error);
    res.status(500).json({
      error: 'Internal server error'
    });
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
});

// Auth routes
app.use('/api/auth', authRouter);

// Serve static files from the dist directory (only in production)
if (isProduction) {
  const distPath = path.resolve(__dirname, '../dist');
  console.log(`Serving static files from: ${distPath}`);
  app.use(express.static(distPath));
}

// Alle anderen Anfragen an das Frontend weiterleiten (für SPA-Routing)
app.get('*', (req, res) => {
  if (isProduction) {
    res.sendFile(path.resolve(__dirname, '../dist/index.html'));
  } else {
    res.redirect(clientUrl);
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`Environment: ${isProduction ? 'production' : 'development'}`);
  console.log(`Open ${clientUrl} in your browser`);
}); 