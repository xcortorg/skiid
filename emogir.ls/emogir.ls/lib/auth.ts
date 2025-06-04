import { AuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { db } from "./db";
import bcrypt from "bcryptjs";
import { authenticator } from "otplib";
import { verifyTurnstileToken } from "./turnstile";
import { getClientInfo } from "@/lib/clientinfo";
import { getIpLocation } from "@/lib/location";
import { headers } from "next/headers";
import { redis } from "@/lib/redis";
import { Resend } from "resend";
import { verifyBackupCode } from "./2fa";

const resend = new Resend(process.env.RESEND_API_KEY);

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      email: string;
      username: string; // this is our slug
      name?: string | null; // this is our displayName
      image?: string | null;
      onboarding?: boolean;
    };
  }
}

export const authOptions: AuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, //30d
  },
  pages: {
    signIn: "/login",
    signOut: "/signout",
    error: "/login",
  },
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        code: { label: "2FA Code", type: "text" },
        isBackupCode: { label: "Is Backup Code", type: "text" },
        turnstileToken: { label: "Turnstile Token", type: "text" },
        verified: { label: "Verified", type: "text" },
      },
      async authorize(credentials) {
        if (
          !credentials?.email ||
          !credentials?.password ||
          !credentials?.turnstileToken
        ) {
          throw new Error("Missing credentials");
        }

        const isValidToken = await verifyTurnstileToken(
          credentials.turnstileToken,
        );
        if (!isValidToken) {
          throw new Error("Invalid challenge response");
        }

        const user = await db.user.findUnique({
          where: { email: credentials.email },
          select: {
            id: true,
            email: true,
            password: true,
            username: true,
            name: true,
            image: true,
            twoFactorEnabled: true,
            twoFactorSecret: true,
            backupCodes: true,
            onboarding: true,
          },
        });

        if (!user || !user.password) {
          throw new Error("Invalid credentials");
        }

        const isValid = await bcrypt.compare(
          credentials.password,
          user.password,
        );
        if (!isValid) {
          throw new Error("Invalid credentials");
        }

        if (user.twoFactorEnabled && !credentials.code) {
          throw new Error("2FA_REQUIRED");
        }

        if (user.twoFactorEnabled && credentials.code) {
          if (credentials.isBackupCode === "true") {
            const backupCodes = JSON.parse(user.backupCodes || "[]");

            if (!verifyBackupCode(credentials.code, user.backupCodes!)) {
              throw new Error("Invalid backup code");
            }

            const updatedBackupCodes = backupCodes.filter(
              (code: string) => code !== credentials.code,
            );
            await db.user.update({
              where: { id: user.id },
              data: {
                backupCodes: JSON.stringify(updatedBackupCodes),
                lastTwoFactorAt: new Date(),
              },
            });
          } else {
            const isValidCode = authenticator.verify({
              token: credentials.code,
              secret: user.twoFactorSecret!,
            });

            if (!isValidCode) {
              throw new Error("Invalid 2FA code");
            }

            await db.user.update({
              where: { id: user.id },
              data: { lastTwoFactorAt: new Date() },
            });
          }
        }

        return {
          id: user.id,
          email: user.email,
          username: user.username,
          name: user.name,
          image: user.image,
          credentials: {
            verified: credentials.verified,
            code: credentials.code,
          },
        };
      },
    }),
  ],
  callbacks: {
    async signIn({ user }) {
      if (!user.id) return false;

      try {
        const headersList = await headers();
        const clientInfo = await getClientInfo();
        const ipAddress = headersList.get("x-forwarded-for") || "unknown";
        const location = await getIpLocation(ipAddress);

        const credentials = (user as any).credentials;
        console.log("SignIn attempt:", {
          userId: user.id,
          ipAddress,
          hasExistingCredentials: !!credentials,
          verified: credentials?.verified,
        });

        const userSettings = await db.user.findUnique({
          where: { id: user.id },
          select: {
            newLoginVerification: true,
            onboarding: true,
            twoFactorEnabled: true,
            email: true,
          },
        });

        if (!userSettings?.email) {
          console.error("No email found for user");
          return false;
        }

        console.log("User settings:", userSettings);

        const existingSession = await db.session.findFirst({
          where: {
            userId: user.id,
            ipAddress: ipAddress,
            verified: true,
            isActive: true,
          },
        });

        console.log("Existing session:", existingSession);
        console.log(
          "Needs verification:",
          userSettings.newLoginVerification ?? true,
        );

        if (!existingSession && credentials?.verified !== "true") {
          const isLimited = await isEmailRateLimited(user.id);
          if (isLimited) {
            console.log("Email rate limit exceeded for user:", user.id);
            throw new Error(
              "Too many verification attempts. Please try again later.",
            );
          }

          console.log("Sending verification email");
          const verificationCode = Math.floor(
            100000 + Math.random() * 900000,
          ).toString();

          try {
            const emailResult = await resend.emails.send({
              from: "Emogir.ls <noreply@emogir.ls>",
              to: userSettings.email,
              subject: "Verify your login",
              html: `
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta content="width=device-width" name="viewport" />
                    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type" />
                    <title>Verify your login</title>
                  </head>
                  <body style="background-color: #0f0a14; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;">
                    <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 600px; width: 100%; margin: 0 auto;">
                      <tr>
                        <td style="padding: 40px 20px;">
                          <div style="background: linear-gradient(180deg, #231623 0%, #1a121a 100%); border-radius: 16px; padding: 40px; margin-bottom: 30px; border: 1px solid #4a2a4a;">
                            <h1 style="margin: 0 0 20px 0; font-size: 24px; color: #ffffff; text-align: center;">
                              Verify Your Login
                            </h1>
                            
                            <p style="margin: 0 0 20px 0; line-height: 1.6; color: #a67ba6; text-align: center;">
                              We detected a login attempt from a new location. For your security, please verify that this was you.
                            </p>

                            <div style="background: #1a121a; border: 1px solid #4a2a4a; border-radius: 8px; padding: 20px; margin: 30px 0;">
                              <p style="margin: 0 0 10px 0; color: #a67ba6; font-size: 14px; text-align: center;">
                                Location
                              </p>
                              <p style="margin: 0; color: #ffffff; font-size: 16px; text-align: center;">
                                ${
                                  location
                                    ? `${location.city}, ${location.country}`
                                    : "Unknown Location"
                                }
                              </p>
                            </div>

                            <div style="background: #1a121a; border: 1px solid #4a2a4a; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                              <p style="margin: 0 0 10px 0; color: #a67ba6; font-size: 14px; text-align: center;">
                                Your Verification Code
                              </p>
                              <p style="margin: 0; color: #ff3379; font-size: 32px; font-weight: bold; letter-spacing: 4px; text-align: center;">
                                ${verificationCode}
                              </p>
                            </div>

                            <p style="margin: 0; color: #a67ba6; font-size: 14px; text-align: center;">
                              This code will expire in 10 minutes.<br/>
                              If you didn't attempt to log in, please change your password immediately.
                            </p>
                          </div>

                          <div style="text-align: center;">
                            <p style="margin: 0; color: #a67ba6; font-size: 12px;">
                              © 2024 Emogir.ls. All rights reserved.
                            </p>
                          </div>
                        </td>
                      </tr>
                    </table>
                  </body>
                </html>
              `,
            });
            console.log("Verification email sent, returning false");

            await redis.set(
              `verification:${user.id}:${ipAddress}`,
              verificationCode,
              { ex: 600 },
            );
            return false;
          } catch (emailError) {
            console.error("Failed to send email:", emailError);
            throw emailError;
          }
        }

        if (credentials?.verified === "true") {
          await createSession(user.id, clientInfo, ipAddress, location);
          return true;
        }

        if (existingSession) {
          await db.session.update({
            where: { id: existingSession.id },
            data: { lastActive: new Date() },
          });
          return true;
        }

        return false;
      } catch (error) {
        console.error("SignIn callback error:", error);
        return false;
      }
    },
    async session({ session, token }) {
      if (session.user && token.sub) {
        await db.session.updateMany({
          where: {
            userId: token.sub,
            isActive: true,
          },
          data: {
            lastActive: new Date(),
          },
        });

        const user = await db.user.findUnique({
          where: { id: token.sub },
          select: {
            id: true,
            name: true,
            email: true,
            image: true,
            username: true,
            onboarding: true,
          },
        });

        if (user) {
          session.user = {
            ...session.user,
            id: user.id,
            name: user.name,
            username: user.username,
            image: user.image,
            onboarding: user.onboarding,
          };
        }
      }
      return session;
    },
    async jwt({ token, user }) {
      if (user) {
        return {
          ...token,
          id: user.id,
          username: user.username,
          image: user.image,
        };
      }
      return token;
    },
  },
};

export async function registerUser({
  email,
  slug, // we'll use this as username in the database kinda whatever
  password,
  displayName, // we'll use this as name in the database
}: {
  email: string;
  slug: string;
  password: string;
  displayName?: string;
}) {
  const exists = await db.user.findFirst({
    where: {
      OR: [
        { email },
        { username: slug }, // using username field for slug
      ],
    },
  });

  if (exists) {
    throw new Error("Email or slug already taken");
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  const user = await db.user.create({
    data: {
      email,
      username: slug, // using username field for slug
      name: displayName || slug, // using name field for displayName
      password: hashedPassword,
    },
  });

  return {
    id: user.id,
    email: user.email,
    username: user.username, // return as slug
    name: user.name, // return as displayName
  };
}

function normalizeIp(ip: string): string {
  if (ip === "::1") return "127.0.0.1";

  if (ip.startsWith("::ffff:")) {
    return ip.substring(7);
  }

  return ip;
}

async function createSession(
  userId: string,
  clientInfo: any,
  ipAddress: string,
  location: any,
) {
  const normalizedIp = normalizeIp(ipAddress);

  try {
    const existingSession = await db.session.findFirst({
      where: {
        userId,
        ipAddress: normalizedIp,
        isActive: true,
      },
    });

    if (existingSession) {
      return db.session.update({
        where: { id: existingSession.id },
        data: {
          lastActive: new Date(),
          verified: true,
          deviceInfo: JSON.stringify(clientInfo || {}),
        },
      });
    }

    const inactiveSession = await db.session.findFirst({
      where: {
        userId,
        ipAddress: normalizedIp,
        isActive: false,
      },
    });

    if (inactiveSession) {
      return db.session.update({
        where: { id: inactiveSession.id },
        data: {
          lastActive: new Date(),
          verified: true,
          isActive: true,
          deviceInfo: JSON.stringify(clientInfo || {}),
          location: location
            ? `${location.city}, ${location.country}`
            : "unknown",
        },
      });
    }

    return db.session.create({
      data: {
        userId,
        deviceInfo: JSON.stringify(clientInfo || {}),
        ipAddress: normalizedIp,
        location: location
          ? `${location.city}, ${location.country}`
          : "unknown",
        isActive: true,
        verified: true,
      },
    });
  } catch (error) {
    console.error("Session creation error:", error);
    throw error;
  }
}

async function isEmailRateLimited(userId: string): Promise<boolean> {
  const key = `email_limit:${userId}`;
  const attempts = await redis.incr(key);

  if (attempts === 1) {
    await redis.expire(key, 3600);
  }

  return attempts > 5;
}
