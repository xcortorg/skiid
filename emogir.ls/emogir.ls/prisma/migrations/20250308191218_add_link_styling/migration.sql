-- AlterTable
ALTER TABLE "Link" ADD COLUMN "backgroundColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "borderColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "gap" TEXT;
ALTER TABLE "Link" ADD COLUMN "hoverColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "hoverTextColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "iconBgColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "iconBorderRadius" TEXT;
ALTER TABLE "Link" ADD COLUMN "iconColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "iconSize" TEXT;
ALTER TABLE "Link" ADD COLUMN "primaryTextColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "secondaryTextColor" TEXT;
ALTER TABLE "Link" ADD COLUMN "textSize" TEXT;

-- CreateTable
CREATE TABLE "appearance" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "displayName" TEXT,
    "bio" TEXT,
    "avatar" TEXT,
    "layoutStyle" TEXT,
    "containerBackgroundColor" TEXT,
    "containerBackdropBlur" TEXT,
    "containerBorderColor" TEXT,
    "containerBorderWidth" TEXT,
    "containerBorderRadius" TEXT,
    "containerGlowColor" TEXT,
    "containerGlowIntensity" TEXT,
    "glassEffect" BOOLEAN DEFAULT false,
    "backgroundUrl" TEXT,
    "avatarSize" TEXT,
    "avatarBorderWidth" TEXT,
    "avatarBorderColor" TEXT,
    "avatarBorderRadius" TEXT,
    "avatarGlowColor" TEXT,
    "avatarGlowIntensity" TEXT,
    "titleColor" TEXT,
    "titleSize" TEXT,
    "titleWeight" TEXT,
    "usernameColor" TEXT,
    "usernameSize" TEXT,
    "bioColor" TEXT,
    "bioSize" TEXT,
    "linksBackgroundColor" TEXT,
    "linksHoverColor" TEXT,
    "linksBorderColor" TEXT,
    "linksGap" TEXT,
    "linksPrimaryTextColor" TEXT,
    "linksSecondaryTextColor" TEXT,
    "linksHoverTextColor" TEXT,
    "linksTextSize" TEXT,
    "linksIconSize" TEXT,
    "linksIconColor" TEXT,
    "linksIconBgColor" TEXT,
    "linksIconBorderRadius" TEXT,
    "discordPresenceBgColor" TEXT,
    "discordPresenceBorderColor" TEXT,
    "discordPresenceAvatarSize" TEXT,
    "discordPresenceTextColor" TEXT,
    "discordPresenceSecondaryColor" TEXT,
    "discordGuildBgColor" TEXT,
    "discordGuildBorderColor" TEXT,
    "discordGuildAvatarSize" TEXT,
    "discordGuildTitleColor" TEXT,
    "discordGuildButtonBgColor" TEXT,
    "discordGuildButtonHoverColor" TEXT,
    "clickEffectEnabled" BOOLEAN DEFAULT false,
    "clickEffectText" TEXT,
    "clickEffectColor" TEXT,
    "gradientEnabled" BOOLEAN DEFAULT false,
    "gradientColor" TEXT,
    "gradientType" TEXT,
    "gradientDirection" TEXT,
    "statsEnabled" BOOLEAN DEFAULT true,
    "statsColor" TEXT,
    "statsBgColor" TEXT,
    "font" TEXT,
    "fontSize" TEXT,
    "fontWeight" TEXT,
    CONSTRAINT "appearance_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "appearance_userId_key" ON "appearance"("userId");
