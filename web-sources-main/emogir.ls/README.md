# Emogir.ls

A profile customization platform with advanced theming, integrations, and security features.

## Development Setup

1. Clone and install dependencies:

```bash
git clone <repository-url>
cd emogir.ls
pnpm install
```

2. Set up environment variables:

```bash
cp .env.example .env
```

Required variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `NEXTAUTH_SECRET`: JWT signing key
- `TURNSTILE_SECRET_KEY`: Cloudflare Turnstile secret
- `LASTFM_API_KEY` & `LASTFM_SECRET`: Last.fm API credentials

3. Initialize database:

```bash
npx prisma generate
npx prisma db push
```

4. Run development server:

```bash
pnpm dev
```

## Architecture

- **Framework**: Next.js 14 (App Router)
- **Database**: PostgreSQL + Prisma ORM
- **Caching**: Redis
- **Auth**: NextAuth.js + 2FA
- **UI**: Tailwind CSS + Shadcn/ui

## Key Features

- Advanced profile customization
- 2FA with backup codes
- Rate limiting
- Session management
- Last.fm integration
- Discord presence
- Custom themes

## API Routes

- `/api/auth/*`: Authentication endpoints
- `/api/account/*`: User account management
- `/api/profile/*`: Public profile data
- `/api/integrations/*`: Third-party services

## Security

- CSRF protection
- Rate limiting
- Turnstile verification
- Session tracking
- Password hashing (Argon2)
