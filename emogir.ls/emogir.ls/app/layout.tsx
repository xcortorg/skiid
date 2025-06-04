import type { Metadata } from "next";
import localFont from "next/font/local";
import {
  Inter,
  Outfit,
  Space_Grotesk,
  Plus_Jakarta_Sans,
  Sora,
} from "next/font/google";
import "./globals.css";
import SiteLayout from "@/components/layouts/site-layout";
import NextTopLoader from "nextjs-toploader";
import { SessionProvider } from "@/components/auth/session-provider";
import Script from "next/script";
import { ToastProvider } from "@/components/ui/toast-provider";

const satoshi = localFont({
  src: [
    {
      path: "../public/fonts/Satoshi-Regular.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../public/fonts/Satoshi-Medium.woff2",
      weight: "500",
      style: "normal",
    },
    {
      path: "../public/fonts/Satoshi-Bold.woff2",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-satoshi",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta-sans",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
});

export const metadata: Metadata = {
  title: "emogir.ls: your socials, in one place.",
  description:
    "a premium solution for e-mails, image uploading & digital portfolios. showcase your online presence with customizable profiles, secure image hosting, and professional email management.",
  icons: {
    icon: "/favicon.ico",
  },
  openGraph: {
    title: "emogir.ls: your socials, in one place.",
    description:
      "a premium solution for e-mails, image uploading & digital portfolios. showcase your online presence with customizable profiles, secure image hosting, and professional email management.",
    images: ["https://r.emogir.ls/og-release-emogirls.png"],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    images: ["https://r.emogir.ls/og-release-emogirls.png"],
  },
};

export const viewport = {
  themeColor: "#f2108a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <Script
          defer
          data-domain="emogir.ls"
          src="https://plausible.emogir.ls/js/script.js"
          strategy="afterInteractive"
        />
      </head>
      <body
        className={`${satoshi.variable} ${inter.variable} ${outfit.variable} ${spaceGrotesk.variable} ${plusJakartaSans.variable} ${sora.variable} antialiased bg-[#030303]`}
      >
        <SessionProvider>
          <ToastProvider>
            <NextTopLoader
              color="#ff3379"
              height={0.5}
              showSpinner={false}
              shadow="0 0 10px #ff3379,0 0 5px #ff3379"
            />
            <SiteLayout variant="default">{children}</SiteLayout>
          </ToastProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
