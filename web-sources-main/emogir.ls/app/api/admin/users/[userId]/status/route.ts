import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";
import { Resend } from "resend";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];
const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(
  req: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  try {
    const session = (await getServerSession(
      authOptions as any,
    )) as Session | null;
    if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { status, reason, expiresAt, sendEmail } = await req.json();
    const resolvedParams = await params;

    if (
      ![
        "ACTIVE",
        "DISABLED",
        "BANNED",
        "RESTRICTED",
        "PENDING_REVIEW",
      ].includes(status)
    ) {
      return NextResponse.json({ error: "Invalid status" }, { status: 400 });
    }

    console.log("Status update request:", { 
      status, 
      reason, 
      expiresAt, 
      userId: resolvedParams.userId 
    });

    const user = await db.user.update({
      where: { id: resolvedParams.userId },
      data: {
        accountStatus: status,
        isDisabled: status !== "ACTIVE",
        banReason: status === "BANNED" ? reason : null,
        banExpires: status === "BANNED" ? expiresAt : null,
        disabledReason: status === "DISABLED" ? reason : null,
        disabledAt: status !== "ACTIVE" ? new Date() : null,
        disabledBy: status !== "ACTIVE" ? session.user.id : null,
      },
      select: {
        email: true,
        name: true,
        username: true,
        accountStatus: true,
      },
    });

    console.log("User updated:", user);

    if (sendEmail) {
      if (status !== "ACTIVE" && user.email) {
        const statusText =
          status === "BANNED" ? "banned" : "temporarily suspended";
        const expiryText = expiresAt
          ? `until ${new Date(expiresAt).toLocaleDateString()}`
          : "indefinitely";

        await resend.emails.send({
          from: "Emogir.ls <noreply@emogir.ls>",
          to: user.email,
          subject: `Account ${statusText} - Emogir.ls`,
          html: `
            <!DOCTYPE html>
            <html>
              <head>
                <meta content="width=device-width" name="viewport" />
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type" />
                <title>Account ${statusText}</title>
              </head>
              <body style="background-color: #0f0a14; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;">
                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 600px; width: 100%; margin: 0 auto;">
                  <tr>
                    <td style="padding: 40px 20px;">
                      <div style="background: linear-gradient(180deg, #231623 0%, #1a121a 100%); border-radius: 16px; padding: 40px; margin-bottom: 30px; border: 1px solid #4a2a4a;">
                        <h1 style="margin: 0 0 20px 0; font-size: 24px; color: #ffffff; text-align: center;">
                          Account ${statusText}
                        </h1>
                        
                        <p style="margin: 0 0 20px 0; line-height: 1.6; color: #a67ba6; text-align: center;">
                          Your account has been ${statusText} ${expiryText}.
                        </p>

                        ${
                          reason
                            ? `
                          <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 20px; margin: 20px 0; color: #a67ba6;">
                            <strong style="color: #ffffff">Reason:</strong><br/>
                            ${reason}
                          </div>
                        `
                            : ""
                        }

                        <p style="margin: 20px 0; color: #a67ba6; text-align: center;">
                          If you believe this was done in error, please contact our support team.
                        </p>

                        <div style="text-align: center; margin-bottom: 30px;">
                          <a href="${
                            process.env.NEXTAUTH_URL
                          }/support" style="display: inline-block; padding: 15px 30px; background: linear-gradient(45deg, #ff3379, #ff6b6b); border-radius: 8px; color: white; text-decoration: none; font-weight: 500;">
                            Contact Support
                          </a>
                        </div>
                      </div>

                      <div style="text-align: center;">
                        <p style="margin: 0; color: #a67ba6; font-size: 12px;">
                          © 2025 Emogir.ls. All rights reserved.
                        </p>
                      </div>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
          `,
        });
      }

      if (
        status === "ACTIVE" &&
        user.email &&
        user.accountStatus !== "ACTIVE"
      ) {
        await resend.emails.send({
          from: "Emogir.ls <noreply@emogir.ls>",
          to: user.email,
          subject: "Account Restored - Emogir.ls",
          html: `
            <!DOCTYPE html>
            <html>
              <head>
                <meta content="width=device-width" name="viewport" />
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type" />
                <title>Account Restored</title>
              </head>
              <body style="background-color: #0f0a14; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;">
                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 600px; width: 100%; margin: 0 auto;">
                  <tr>
                    <td style="padding: 40px 20px;">
                      <div style="background: linear-gradient(180deg, #231623 0%, #1a121a 100%); border-radius: 16px; padding: 40px; margin-bottom: 30px; border: 1px solid #4a2a4a;">
                        <h1 style="margin: 0 0 20px 0; font-size: 24px; color: #ffffff; text-align: center;">
                          Account Restored
                        </h1>
                        
                        <p style="margin: 0 0 20px 0; line-height: 1.6; color: #a67ba6; text-align: center;">
                          Your account has been restored and is now fully functional.
                        </p>

                        <div style="text-align: center; margin-bottom: 30px;">
                          <a href="${process.env.NEXTAUTH_URL}" style="display: inline-block; padding: 15px 30px; background: linear-gradient(45deg, #ff3379, #ff6b6b); border-radius: 8px; color: white; text-decoration: none; font-weight: 500;">
                            Go to Dashboard
                          </a>
                        </div>
                      </div>

                      <div style="text-align: center;">
                        <p style="margin: 0; color: #a67ba6; font-size: 12px;">
                          © 2025 Emogir.ls. All rights reserved.
                        </p>
                      </div>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
          `,
        });
      }
    }

    await db.adminLog.create({
      data: {
        action: `ACCOUNT_${status}`,
        targetUserId: resolvedParams.userId,
        adminId: session.user.id,
        metadata: {
          reason,
          expiresAt,
          previousStatus: user.accountStatus,
        },
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Status update error:", error);
    return NextResponse.json(
      { error: "Failed to update status" },
      { status: 500 },
    );
  }
}
