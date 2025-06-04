import express from 'express';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import { randomBytes } from 'crypto';
import { saveLoginAttempt } from './services/dbService';

dotenv.config();

const router = express.Router();
const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID || '';
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET || '';
const DISCORD_REDIRECT_URI = process.env.DISCORD_REDIRECT_URI || 'http://localhost:5000/api/auth/discord/callback';
const JWT_SECRET = process.env.JWT_SECRET || randomBytes(32).toString('hex');
const JWT_EXPIRY = '24h';

if (!DISCORD_CLIENT_ID || !DISCORD_CLIENT_SECRET) {
  console.error('Discord OAuth credentials are not configured. Please set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET environment variables.');
}

// Initiiere Discord OAuth Flow
router.get('/discord', (req, res) => {
  const scope = 'identify email';
  const discordAuthUrl = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(
    DISCORD_REDIRECT_URI
  )}&response_type=code&scope=${encodeURIComponent(scope)}`;

  res.redirect(discordAuthUrl);
});

// Discord OAuth2 callback
router.get('/discord/callback', async (req, res) => {
  const { code } = req.query;
  
  if (!code) {
    return res.status(400).json({ error: 'Authorization code not provided' });
  }

  try {
    // Exchange code for token
    const tokenResponse = await fetch('https://discord.com/api/oauth2/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: DISCORD_CLIENT_ID,
        client_secret: DISCORD_CLIENT_SECRET,
        grant_type: 'authorization_code',
        code: code.toString(),
        redirect_uri: DISCORD_REDIRECT_URI,
        scope: 'identify email',
      }),
    });

    const tokenData = await tokenResponse.json();
    
    if (!tokenResponse.ok) {
      console.error('Discord token error:', tokenData);
      return res.status(400).json({ error: 'Failed to exchange code for token' });
    }

    // Get user info from Discord
    const userResponse = await fetch('https://discord.com/api/users/@me', {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
    });

    const userData = await userResponse.json();
    
    if (!userResponse.ok) {
      console.error('Discord user info error:', userData);
      return res.status(400).json({ error: 'Failed to get user info from Discord' });
    }

    // Extract and normalize the IP address, preferring IPv4 over IPv6
    let ipAddress: string = 'unknown';
    
    // Try to extract from X-Forwarded-For header first (common in proxy setups)
    const extractIpFromForwardedFor = (forwardedForHeader: string | string[]): string => {
      let ips: string[] = [];
      
      if (Array.isArray(forwardedForHeader)) {
        // If it's an array, flatten and split by commas
        forwardedForHeader.forEach(header => {
          ips = ips.concat(header.split(',').map(ip => ip.trim()));
        });
      } else {
        // If it's a string, just split by commas
        ips = forwardedForHeader.split(',').map(ip => ip.trim());
      }
      
      // Look for the first IPv4 address
      const ipv4 = ips.find(ip => /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(ip));
      if (ipv4) return ipv4;
      
      // If no IPv4 found, return the first IP (regardless of type)
      return ips[0] || 'unknown';
    };
    
    // Try X-Forwarded-For header first
    const forwardedFor = req.headers['x-forwarded-for'];
    if (forwardedFor) {
      ipAddress = extractIpFromForwardedFor(forwardedFor);
    } 
    // Then try direct socket address
    else if (req.socket && req.socket.remoteAddress) {
      const remoteAddr = req.socket.remoteAddress;
      
      // Check if it's an IPv4 address
      if (/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(remoteAddr)) {
        ipAddress = remoteAddr;
      }
      // Check if it's an IPv6 with embedded IPv4
      else if (remoteAddr.startsWith('::ffff:') && /^::ffff:(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(remoteAddr)) {
        ipAddress = remoteAddr.substring(7); // Extract the IPv4 part
      }
      // Handle localhost IPv6
      else if (remoteAddr === '::1') {
        ipAddress = '127.0.0.1';
      }
      // Use IPv6 as fallback
      else {
        ipAddress = remoteAddr;
      }
    }
    
    console.log(`User ${userData.username} (${userData.id}) login from IP: ${ipAddress}`);
    
    // Save login attempt to database
    await saveLoginAttempt(userData.id, ipAddress);

    // Generate JWT token
    const token = jwt.sign({
      id: userData.id,
      username: userData.username,
      email: userData.email,
      avatar: userData.avatar,
    }, JWT_SECRET, {
      expiresIn: JWT_EXPIRY
    });

    // Send JWT in a secure, http-only cookie
    res.cookie('auth_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production', // Set to true in production
      sameSite: 'strict',
      maxAge: 24 * 60 * 60 * 1000, // 24 hours
    });

    // Redirect to frontend
    res.redirect(process.env.CLIENT_URL || 'http://localhost:3000');
  } catch (error) {
    console.error('Discord authentication error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

// Get current user info
router.get('/me', verifyToken, (req, res) => {
  // @ts-ignore
  res.json(req.user);
});

// Logout route
router.post('/logout', (req, res) => {
  res.clearCookie('auth_token');
  res.json({ success: true, message: 'Logged out successfully' });
});

// Middleware to verify JWT token
export function verifyToken(req: express.Request, res: express.Response, next: express.NextFunction) {
  const token = req.cookies.auth_token;

  if (!token) {
    return res.status(401).json({ error: 'Access denied. No token provided.' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    // @ts-ignore
    req.user = decoded;
    next();
  } catch (error) {
    res.status(400).json({ error: 'Invalid token.' });
  }
}

export default router; 