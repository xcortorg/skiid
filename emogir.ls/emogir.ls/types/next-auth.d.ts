import "next-auth";

declare module "next-auth" {
  interface User {
    username?: string;
    image?: string | null;
    onboarding?: boolean;
  }

  interface Session {
    user: User & {
      id?: string;
      username?: string;
      image?: string | null;
      onboarding?: boolean;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    username?: string;
    image?: string | null;
    onboarding?: boolean;
  }
}
